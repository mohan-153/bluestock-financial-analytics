from pathlib import Path
import sqlite3
import csv
import pandas as pd

from src.etl.loader import load_all_data


DB_PATH = Path("data/nifty100.db")
SCHEMA_PATH = Path("schema.sql")
AUDIT_PATH = Path("output/load_audit.csv")


# ============================================================
# COLUMN MAPPINGS
# ============================================================

TABLE_COLUMNS = {
    "companies": [
        "company_id",
        "company_logo",
        "company_name",
        "chart_link",
        "about_company",
        "website",
        "nse_profile",
        "bse_profile",
        "face_value",
        "book_value",
        "roce_percentage",
        "roe_percentage",
    ],

    "profitandloss": [
        "id",
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ],

    "balancesheet": [
        "id",
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
    ],

    "cashflow": [
        "id",
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ],

    "analysis": [
    "id",
    "company_id",
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
],

    "documents": [
    "id",
    "company_id",
    "year",
    "annual_report",
],

    "prosandcons": [
        "id",
        "company_id",
        "pros",
        "cons",
    ],

    "sectors": [
        "id",
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ],

    "market_cap": [
        "id",
        "company_id",
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ],

    "stock_prices": [
        "id",
        "company_id",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "adjusted_close",
    ],

    "financial_ratios": [
        "id",
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
    ],

    "peer_groups": [
        "id",
        "peer_group_name",
        "company_id",
        "is_benchmark",
    ],
}


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_dataset(
    table_name,
    df,
):
    """
    Prepare a DataFrame for SQLite insertion.
    """

    df = df.copy()

    # --------------------------------------------------------
    # companies.id -> companies.company_id
    # --------------------------------------------------------

    if table_name == "companies":

        if "id" not in df.columns:
            raise ValueError(
                "companies.xlsx must contain 'id'"
            )

        df = df.rename(
            columns={
                "id": "company_id"
            }
        )

    # --------------------------------------------------------
    # Normalize company IDs
    # --------------------------------------------------------

    if "company_id" in df.columns:

        df["company_id"] = (
            df["company_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    # --------------------------------------------------------
    # Convert NaN to None
    # --------------------------------------------------------

    df = df.where(
        df.notna(),
        None
    )

    # --------------------------------------------------------
    # Keep only schema columns
    # --------------------------------------------------------

    required_columns = TABLE_COLUMNS[
        table_name
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{table_name}: missing columns: {missing}"
        )

    df = df[
        required_columns
    ]

    return df


# ============================================================
# DATABASE CREATION
# ============================================================

def create_database():

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema not found: {SCHEMA_PATH}"
        )

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    AUDIT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove old database so every load is reproducible.
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(
        DB_PATH
    )

    try:

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        schema_sql = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        connection.executescript(
            schema_sql
        )

        return connection

    except Exception:
        connection.close()

        if DB_PATH.exists():
            DB_PATH.unlink()

        raise


# ============================================================
# INSERT DATA
# ============================================================

def insert_dataset(
    connection,
    table_name,
    df,
):

    prepared = prepare_dataset(
        table_name,
        df,
    )

    columns = TABLE_COLUMNS[
        table_name
    ]

    placeholders = ",".join(
        ["?"] * len(columns)
    )

    column_sql = ",".join(
        f'"{column}"'
        for column in columns
    )

    sql = f"""
        INSERT INTO "{table_name}"
        ({column_sql})
        VALUES ({placeholders})
    """

    records = [
        tuple(row)
        for row in prepared.itertuples(
            index=False,
            name=None,
        )
    ]

    if records:
        connection.executemany(
            sql,
            records,
        )

    return len(records)

def filter_orphan_company_rows(
    datasets: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """
    Remove child-table rows whose company_id is not present in
    the master companies dataset.

    Source files are never modified. Rejected rows are returned
    as DQ-03 foreign-key failures.
    """

    master_ids = set(
        datasets["companies"]["id"]
        .dropna()
        .astype("string")
        .str.strip()
        .str.upper()
    )

    filtered = {}
    dq_failures = []

    for dataset_name, df in datasets.items():

        if dataset_name == "companies" or "company_id" not in df.columns:
            filtered[dataset_name] = df.copy()
            continue

        current = df.copy()

        normalized_ids = (
            current["company_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        orphan_mask = (
            current["company_id"].isna()
            | normalized_ids.isna()
            | ~normalized_ids.isin(master_ids)
        )

        if orphan_mask.any():

            orphan_rows = current.loc[orphan_mask]

            for _, row in orphan_rows.iterrows():

                company_id = row.get("company_id")
                year = row.get("year", "")

                dq_failures.append({
                    "company_id": (
                        ""
                        if pd.isna(company_id)
                        else str(company_id).strip().upper()
                    ),
                    "year": (
                        ""
                        if pd.isna(year)
                        else str(year)
                    ),
                    "field": "company_id",
                    "issue": (
                        f"Company ID does not exist in master companies; "
                        f"rejected from {dataset_name}"
                    ),
                    "severity": "CRITICAL",
                })

            current = current.loc[~orphan_mask].copy()

        filtered[dataset_name] = current

    return filtered, dq_failures


def write_validation_failures(failures):
    """Write foreign-key DQ-03 failures discovered during loading."""

    validation_path = Path("output/validation_failures.csv")
    validation_path.parent.mkdir(parents=True, exist_ok=True)

    with validation_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "company_id",
                "year",
                "field",
                "issue",
                "severity",
            ],
        )

        writer.writeheader()
        writer.writerows(failures)

# ============================================================
# LOAD ALL DATA
# ============================================================

def load_database():

    # Load and normalize all source datasets.
    data = load_all_data()

    # Resolve DQ-03 foreign-key issues before SQLite insertion.
    data, fk_failures = filter_orphan_company_rows(data)

    # Create a fresh database.
    connection = create_database()

    audit_rows = []

    table_order = [
        "companies",
        "sectors",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "market_cap",
        "stock_prices",
        "financial_ratios",
        "peer_groups",
    ]

    try:

        for table_name in table_order:

            df = data[table_name]
            source_rows = len(df)

            try:

                inserted_rows = insert_dataset(
                    connection,
                    table_name,
                    df,
                )

                audit_rows.append({
                    "table_name": table_name,
                    "source_rows": source_rows,
                    "inserted_rows": inserted_rows,
                    "status": "LOADED",
                    "error": "",
                })

            except Exception as exc:

                audit_rows.append({
                    "table_name": table_name,
                    "source_rows": source_rows,
                    "inserted_rows": 0,
                    "status": "FAILED",
                    "error": str(exc),
                })

                connection.rollback()
                raise

        # Final SQLite foreign-key verification.
        fk_check = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

        if fk_check:
            raise sqlite3.IntegrityError(
                f"Foreign-key verification failed: {len(fk_check)} violation(s)"
            )

        connection.commit()

    finally:
        connection.close()

    # Write load audit.
    with AUDIT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "table_name",
                "source_rows",
                "inserted_rows",
                "status",
                "error",
            ],
        )

        writer.writeheader()
        writer.writerows(audit_rows)

    # Write DQ-03 FK failures discovered during loading.
    write_validation_failures(fk_failures)

    return audit_rows, fk_failures

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("BLUESTOCK FINANCIAL ANALYTICS")
    print("SQLite Database Loader")
    print("=" * 80)

    results, fk_failures = load_database()

    print()

    for row in results:

        print(
            f"{row['table_name']:20} "
            f"source={row['source_rows']:5} "
            f"inserted={row['inserted_rows']:5} "
            f"{row['status']}"
        )

    print()
    print(f"Database: {DB_PATH}")
    print(f"Audit:    {AUDIT_PATH}")
    print(f"DQ-03 FK failures: {len(fk_failures)}")
    print()
    print("DATABASE LOAD COMPLETE")
