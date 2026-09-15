"""
Bluestock Financial Analytics
Sprint 3 - Day 21
Analytics/API Integration Layer

Integrates generated Day 16 and Day 17 CSV analytics
into SQLite tables consumed by the FastAPI application.

No source/ETL data is modified.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

STOCK_CSV = OUTPUT_DIR / "stock_market_analytics_day16.csv"
PEER_CSV = OUTPUT_DIR / "peer_comparison_day17.csv"

STOCK_TABLE = "stock_market_analytics"
PEER_TABLE = "peer_comparison"

# Day 16 uses calendar_year, not year.
STOCK_REQUIRED_COLUMNS = {
    "company_id",
    "calendar_year",
}

PEER_REQUIRED_COLUMNS = {
    "company_id",
    "peer_group_name",
}


def get_connection() -> sqlite3.Connection:
    """Return a connection to the project SQLite database."""
    return sqlite3.connect(DB_PATH)


def load_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    """Load and validate a generated analytics CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Required analytics file not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"Analytics file is empty: {path}")

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns in {path.name}: {sorted(missing)}"
        )

    return df


def normalize_company_id(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize company IDs without modifying the source CSV."""
    result = df.copy()

    result["company_id"] = (
        result["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return result


def get_master_company_ids() -> set[str]:
    """Return valid company IDs from the master companies table."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT company_id FROM companies"
        ).fetchall()

    return {
        str(row[0]).strip().upper()
        for row in rows
        if row[0] is not None
    }


def validate_company_ids(
    df: pd.DataFrame,
    valid_company_ids: set[str],
    source_name: str,
) -> None:
    """Ensure analytics records reference master companies."""
    ids = (
        df["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    orphan_ids = sorted(set(ids) - valid_company_ids)

    if orphan_ids:
        raise ValueError(
            f"{source_name} contains company IDs not found in companies: "
            f"{orphan_ids}"
        )


def validate_stock_data(df: pd.DataFrame) -> None:
    """Validate Day 16 annual stock/market analytics."""
    if df["company_id"].isna().any():
        raise ValueError("Stock analytics contains NULL company_id")

    if df["calendar_year"].isna().any():
        raise ValueError("Stock analytics contains NULL calendar_year")

    duplicate_count = df.duplicated(
        subset=["company_id", "calendar_year"]
    ).sum()

    if duplicate_count:
        raise ValueError(
            "Stock analytics contains "
            f"{duplicate_count} duplicate (company_id, calendar_year) rows"
        )


def validate_peer_data(df: pd.DataFrame) -> None:
    """Validate Day 17 peer comparison analytics."""
    if df["company_id"].isna().any():
        raise ValueError("Peer comparison contains NULL company_id")

    if df["peer_group_name"].isna().any():
        raise ValueError(
            "Peer comparison contains NULL peer_group_name"
        )

    keys = ["company_id", "peer_group_name"]

    if "year" in df.columns:
        keys.append("year")

    duplicate_count = df.duplicated(subset=keys).sum()

    if duplicate_count:
        raise ValueError(
            f"Peer comparison contains {duplicate_count} duplicate rows"
        )


def write_table(df: pd.DataFrame, table_name: str) -> int:
    """Replace an analytics SQLite table with generated CSV data."""
    with get_connection() as connection:
        df.to_sql(
            table_name,
            connection,
            if_exists="replace",
            index=False,
        )

        count = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

    return int(count)


def table_exists(table_name: str) -> bool:
    """Check whether a SQLite table exists."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()

    return row is not None


def get_table_count(table_name: str) -> int:
    """Return row count for a SQLite table."""
    if not table_exists(table_name):
        return 0

    with get_connection() as connection:
        return int(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
        )


def integrate() -> dict[str, int]:
    """Run the complete Day 21 integration."""
    stock = normalize_company_id(
        load_csv(STOCK_CSV, STOCK_REQUIRED_COLUMNS)
    )
    peer = normalize_company_id(
        load_csv(PEER_CSV, PEER_REQUIRED_COLUMNS)
    )

    valid_company_ids = get_master_company_ids()

    validate_company_ids(
        stock,
        valid_company_ids,
        STOCK_TABLE,
    )
    validate_company_ids(
        peer,
        valid_company_ids,
        PEER_TABLE,
    )

    validate_stock_data(stock)
    validate_peer_data(peer)

    stock_db_rows = write_table(stock, STOCK_TABLE)
    peer_db_rows = write_table(peer, PEER_TABLE)

    if stock_db_rows != len(stock):
        raise RuntimeError(
            "Stock SQLite row count does not match CSV row count"
        )

    if peer_db_rows != len(peer):
        raise RuntimeError(
            "Peer SQLite row count does not match CSV row count"
        )

    return {
        "stock_csv_rows": len(stock),
        "stock_db_rows": stock_db_rows,
        "peer_csv_rows": len(peer),
        "peer_db_rows": peer_db_rows,
        "companies": len(valid_company_ids),
    }


def main() -> None:
    print("=" * 72)
    print("BLUESTOCK — DAY 21 INTEGRATION")
    print("=" * 72)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = integrate()

    print(f"Master companies       : {result['companies']}")
    print(f"Stock CSV rows         : {result['stock_csv_rows']}")
    print(f"Stock SQLite rows      : {result['stock_db_rows']}")
    print(f"Peer CSV rows          : {result['peer_csv_rows']}")
    print(f"Peer SQLite rows       : {result['peer_db_rows']}")
    print()
    print("Tables created:")
    print(f"  - {STOCK_TABLE}")
    print(f"  - {PEER_TABLE}")
    print()
    print("DAY 21 INTEGRATION: PASS")


if __name__ == "__main__":
    main()
