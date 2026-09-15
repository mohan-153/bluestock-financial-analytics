"""
Day 15 Screener Data Integration tests.
"""

import sqlite3

import pandas as pd
import pytest

from src.analytics.screener_integration_day15 import (
    build_screener_snapshot,
    validate_snapshot,
    write_snapshot_to_sqlite,
)


def sample_data():
    return {
        "companies": pd.DataFrame(
            [
                {
                    "id": "ABC",
                    "company_name": "ABC Industries",
                    "website": "https://example.com",
                },
            ]
        ),
    }


def test_snapshot_adds_company_information(monkeypatch):
    import src.analytics.screener_integration_day15 as module

    preview = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
                "screener_pass": True,
            }
        ]
    )

    monkeypatch.setattr(module, "build_screener_preview", lambda data: preview)

    result = build_screener_snapshot(sample_data())

    assert result.loc[0, "company_name"] == "ABC Industries"
    assert result.loc[0, "website"] == "https://example.com"


def test_snapshot_keeps_company_year_rows(monkeypatch):
    import src.analytics.screener_integration_day15 as module

    preview = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
                "screener_pass": True,
            },
            {
                "company_id": "ABC",
                "year": "2023-03",
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 5,
                "screener_pass": False,
            },
        ]
    )

    monkeypatch.setattr(module, "build_screener_preview", lambda data: preview)

    result = build_screener_snapshot(sample_data())

    assert len(result) == 2
    assert result["company_id"].nunique() == 1


def test_snapshot_sorting(monkeypatch):
    import src.analytics.screener_integration_day15 as module

    preview = pd.DataFrame(
        [
            {
                "company_id": "ZZZ",
                "year": "2023-03",
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
                "screener_pass": True,
            },
            {
                "company_id": "AAA",
                "year": "2024-03",
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
                "screener_pass": True,
            },
        ]
    )

    monkeypatch.setattr(module, "build_screener_preview", lambda data: preview)

    result = build_screener_snapshot(sample_data())

    assert result.iloc[0]["year"] == "2024-03"


def test_write_snapshot_to_sqlite(tmp_path):
    db = tmp_path / "test.db"

    result = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "screener_pass": True,
            },
            {
                "company_id": "XYZ",
                "year": "2024-03",
                "screener_pass": False,
            },
        ]
    )

    count = write_snapshot_to_sqlite(
        result,
        db_path=db,
        table_name="screener_snapshot_test",
    )

    assert count == 2

    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM screener_snapshot_test"
        ).fetchone()[0]

    assert rows == 2


def test_validate_snapshot_pass(tmp_path):
    db = tmp_path / "test.db"

    result = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "screener_pass": True,
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
            }
        ]
    )

    write_snapshot_to_sqlite(
        result,
        db_path=db,
        table_name="screener_snapshot",
    )

    validation = validate_snapshot(result, db_path=db)

    assert validation["status"] == "PASS"
    assert validation["rows"] == 1
    assert validation["db_rows"] == 1


def test_validate_snapshot_detects_duplicates(tmp_path):
    db = tmp_path / "test.db"

    result = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "screener_pass": True,
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 6,
            },
            {
                "company_id": "ABC",
                "year": "2024-03",
                "screener_pass": False,
                "is_financial_company": False,
                "industrial_screener_eligible": True,
                "kpi_pass_count": 2,
            },
        ]
    )

    write_snapshot_to_sqlite(
        result,
        db_path=db,
        table_name="screener_snapshot",
    )

    validation = validate_snapshot(result, db_path=db)

    assert validation["status"] == "FAIL"
    assert validation["duplicate_company_year_rows"] == 1


def test_validate_snapshot_missing_column(tmp_path):
    db = tmp_path / "test.db"

    result = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "screener_pass": True,
            }
        ]
    )

    validation = validate_snapshot(result, db_path=db)

    assert validation["status"] == "FAIL"
    assert "is_financial_company" in validation["missing_columns"]
