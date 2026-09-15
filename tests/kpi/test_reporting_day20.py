"""
Day 20 Reporting Layer tests.
"""

import pandas as pd

from src.analytics.reporting_day20 import (
    build_cagr_report,
    build_company_summary,
    build_market_report,
    build_peer_report,
    build_screener_report,
)


def test_screener_report_not_empty():
    result = build_screener_report()

    assert not result.empty
    assert "company_id" in result.columns


def test_screener_report_has_core_kpis():
    result = build_screener_report()

    expected = {
        "company_id",
        "year",
        "kpi_pass_count",
        "screener_pass",
    }

    assert expected <= set(result.columns)


def test_screener_latest_has_unique_companies():
    result = build_screener_report()

    assert result["company_id"].is_unique


def test_peer_report_not_empty():
    result = build_peer_report()

    assert not result.empty
    assert "peer_group_name" in result.columns


def test_peer_report_unique_company_group():
    result = build_peer_report()

    assert not result.duplicated(
        ["company_id", "peer_group_name"]
    ).any()


def test_market_report_available():
    result = build_market_report()

    # Day 16 generated the SQLite table in the project.
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "company_id" in result.columns


def test_market_latest_has_unique_companies():
    result = build_market_report()

    assert result["company_id"].is_unique


def test_cagr_report_available():
    result = build_cagr_report()

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "company_id" in result.columns


def test_company_summary_has_master_companies():
    result = build_company_summary()

    assert len(result) >= 90
    assert result["company_id"].is_unique


def test_company_summary_contains_company_name():
    result = build_company_summary()

    assert "company_name" in result.columns


def test_company_summary_preserves_master_count():
    result = build_company_summary()

    assert result["company_id"].nunique() == len(result)


def test_report_values_are_not_all_missing():
    result = build_company_summary()

    useful_columns = [
        column
        for column in [
            "roe_pct",
            "roce_pct",
            "opm_pct",
            "kpi_pass_count",
        ]
        if column in result.columns
    ]

    assert useful_columns

    for column in useful_columns:
        assert result[column].notna().any()


def test_screener_pass_values_are_boolean_like():
    result = build_screener_report()

    values = set(result["screener_pass"].dropna().unique())

    assert values <= {0, 1, True, False}
