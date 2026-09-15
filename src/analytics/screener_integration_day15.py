"""
Bluestock Financial Analytics
Sprint 3 - Day 15
Screener Data Integration

Creates a database-ready screener snapshot by combining:
- companies
- sectors
- Day-12 financial ratios
- Day-13 financial carve-out
- Day-14 screener flags

The output is intentionally a separate snapshot CSV. Raw/source tables are
never overwritten.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data
from src.analytics.screener_day14 import build_screener_preview


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "screener_snapshot_day15.csv"
EDGE_LOG = OUTPUT_DIR / "screener_integration_day15.log"


def build_screener_snapshot(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a clean company-year screener snapshot."""
    preview = build_screener_preview(data).copy()

    companies = data["companies"].copy()
    companies["company_id"] = (
        companies["id"].astype(str).str.strip().str.upper()
    )

    company_columns = ["company_id", "company_name", "website"]
    available = [
        column for column in company_columns
        if column in companies.columns or column == "company_id"
    ]

    company_info = companies[available].drop_duplicates("company_id")

    result = preview.merge(
        company_info,
        on="company_id",
        how="left",
    )

    # Keep one stable ordering.
    result = result.sort_values(
        ["year", "screener_pass", "company_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return result


def write_snapshot_to_sqlite(
    result: pd.DataFrame,
    db_path: Path = DB_PATH,
    table_name: str = "screener_snapshot",
) -> int:
    """
    Replace the generated snapshot table in SQLite.

    This is an analytics snapshot, not a replacement for source tables.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        result.to_sql(
            table_name,
            connection,
            if_exists="replace",
            index=False,
        )

        count = connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

    return int(count)


def validate_snapshot(
    result: pd.DataFrame,
    db_path: Path = DB_PATH,
) -> dict:
    """Return integration validation metrics."""
    required = [
        "company_id",
        "year",
        "screener_pass",
        "is_financial_company",
        "industrial_screener_eligible",
        "kpi_pass_count",
    ]

    missing = [column for column in required if column not in result.columns]

    if missing:
        return {
            "status": "FAIL",
            "rows": len(result),
            "companies": result["company_id"].nunique()
            if "company_id" in result.columns
            else 0,
            "missing_columns": missing,
            "db_rows": 0,
        }

    with sqlite3.connect(db_path) as connection:
        db_rows = connection.execute(
            "SELECT COUNT(*) FROM screener_snapshot"
        ).fetchone()[0]

    duplicate_rows = int(
        result.duplicated(["company_id", "year"]).sum()
    )

    invalid_pass_values = int(
        (~result["screener_pass"].isin([True, False])).sum()
    )

    status = (
        "PASS"
        if len(result) == db_rows
        and not missing
        and duplicate_rows == 0
        and invalid_pass_values == 0
        else "FAIL"
    )

    return {
        "status": status,
        "rows": len(result),
        "companies": result["company_id"].nunique(),
        "duplicate_company_year_rows": duplicate_rows,
        "invalid_screener_values": invalid_pass_values,
        "db_rows": int(db_rows),
        "financial_rows": int(result["is_financial_company"].sum()),
        "passing_rows": int(result["screener_pass"].sum()),
    }


def write_edge_log(validation: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK SCREENER INTEGRATION - DAY 15",
        "=" * 70,
    ]

    for key, value in validation.items():
        lines.append(f"{key}: {value}")

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 15 SCREENER DATA INTEGRATION")
    print("=" * 70)

    data = load_all_data()
    result = build_screener_snapshot(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)

    db_rows = write_snapshot_to_sqlite(result)
    validation = validate_snapshot(result)

    write_edge_log(validation)

    print(f"Rows generated : {len(result)}")
    print(f"Companies      : {result['company_id'].nunique()}")
    print(f"DB rows        : {db_rows}")
    print(f"Passing rows   : {int(result['screener_pass'].sum())}")
    print(f"Status         : {validation['status']}")
    print(f"CSV output     : {OUTPUT_CSV}")
    print(f"SQLite table   : screener_snapshot")
    print(f"Edge log       : {EDGE_LOG}")
    print()

    print(
        result[
            [
                "company_id",
                "company_name",
                "year",
                "broad_sector",
                "is_financial_company",
                "kpi_pass_count",
                "screener_pass",
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()
