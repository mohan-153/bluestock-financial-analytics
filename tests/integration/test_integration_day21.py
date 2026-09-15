"""
Bluestock Financial Analytics
Sprint 3 - Day 21
Integration Tests
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.analytics.integration_day21 import (
    DB_PATH,
    PEER_CSV,
    PEER_TABLE,
    STOCK_CSV,
    STOCK_TABLE,
    get_table_count,
    integrate,
    table_exists,
)


def test_stock_source_csv_exists():
    assert STOCK_CSV.exists()


def test_peer_source_csv_exists():
    assert PEER_CSV.exists()


def test_stock_table_exists():
    assert table_exists(STOCK_TABLE)


def test_peer_table_exists():
    assert table_exists(PEER_TABLE)


def test_stock_table_has_rows():
    assert get_table_count(STOCK_TABLE) > 0


def test_peer_table_has_rows():
    assert get_table_count(PEER_TABLE) > 0


def test_stock_csv_and_db_counts_match():
    csv_count = len(pd.read_csv(STOCK_CSV))
    db_count = get_table_count(STOCK_TABLE)

    assert csv_count == db_count


def test_peer_csv_and_db_counts_match():
    csv_count = len(pd.read_csv(PEER_CSV))
    db_count = get_table_count(PEER_TABLE)

    assert csv_count == db_count


def test_stock_has_unique_company_calendar_year():
    with sqlite3.connect(DB_PATH) as connection:
        df = pd.read_sql_query(
            f'SELECT company_id, calendar_year FROM "{STOCK_TABLE}"',
            connection,
        )

    assert not df.duplicated(
        ["company_id", "calendar_year"]
    ).any()


def test_peer_has_unique_company_group_year():
    with sqlite3.connect(DB_PATH) as connection:
        df = pd.read_sql_query(
            f'SELECT * FROM "{PEER_TABLE}"',
            connection,
        )

    keys = ["company_id", "peer_group_name"]

    if "year" in df.columns:
        keys.append("year")

    assert not df.duplicated(keys).any()


def test_stock_company_ids_exist_in_master():
    with sqlite3.connect(DB_PATH) as connection:
        stock_ids = {
            row[0]
            for row in connection.execute(
                f'SELECT DISTINCT company_id FROM "{STOCK_TABLE}"'
            ).fetchall()
        }

        company_ids = {
            row[0]
            for row in connection.execute(
                "SELECT company_id FROM companies"
            ).fetchall()
        }

    assert stock_ids <= company_ids


def test_peer_company_ids_exist_in_master():
    with sqlite3.connect(DB_PATH) as connection:
        peer_ids = {
            row[0]
            for row in connection.execute(
                f'SELECT DISTINCT company_id FROM "{PEER_TABLE}"'
            ).fetchall()
        }

        company_ids = {
            row[0]
            for row in connection.execute(
                "SELECT company_id FROM companies"
            ).fetchall()
        }

    assert peer_ids <= company_ids


def test_integration_is_repeatable():
    result = integrate()

    assert result["stock_csv_rows"] == result["stock_db_rows"]
    assert result["peer_csv_rows"] == result["peer_db_rows"]
