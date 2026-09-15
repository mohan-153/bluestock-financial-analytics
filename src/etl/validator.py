import re
from typing import Any

import pandas as pd

def check_primary_key_unique(
    df: pd.DataFrame,
    column: str,
) -> bool:
    """
    Check that a column contains unique, non-null values.
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    return df[column].notna().all() and df[column].is_unique


def check_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
) -> bool:
    """
    Check that all required columns exist.
    """
    return all(
        column in df.columns
        for column in required_columns
    )

# ---------------------------------------------------------
# DQ-01 — Company PK Uniqueness
# ---------------------------------------------------------

def check_company_pk_unique(
    df: pd.DataFrame,
    column: str = "id",
) -> bool:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    return df[column].notna().all() and df[column].is_unique


# ---------------------------------------------------------
# DQ-02 — Annual PK Uniqueness
# ---------------------------------------------------------

def check_annual_pk_unique(
    df: pd.DataFrame,
    company_column: str = "company_id",
    year_column: str = "year",
) -> bool:
    required = {company_column, year_column}

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    return not df.duplicated(
        subset=[company_column, year_column]
    ).any()


# ---------------------------------------------------------
# DQ-03 — FK Integrity
# ---------------------------------------------------------

def check_foreign_key_integrity(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_column: str = "company_id",
    parent_column: str = "id",
) -> bool:
    if child_column not in child_df.columns:
        raise ValueError(f"Column '{child_column}' not found")

    if parent_column not in parent_df.columns:
        raise ValueError(f"Column '{parent_column}' not found")

    parent_ids = set(parent_df[parent_column].dropna())
    child_ids = set(child_df[child_column].dropna())

    return child_ids.issubset(parent_ids)


# ---------------------------------------------------------
# DQ-04 — Balance Sheet Balance
# ---------------------------------------------------------

def check_balance_sheet(
    df: pd.DataFrame,
    assets_column: str = "total_assets",
    liabilities_column: str = "total_liabilities",
    tolerance: float = 0.01,
) -> bool:
    required = {
        assets_column,
        liabilities_column,
    }

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    for _, row in df.iterrows():
        assets = row[assets_column]
        liabilities = row[liabilities_column]

        if pd.isna(assets) or pd.isna(liabilities):
            continue

        if assets == 0:
            if liabilities != 0:
                return False
            continue

        difference = abs(assets - liabilities) / abs(assets)

        if difference >= tolerance:
            return False

    return True


# ---------------------------------------------------------
# DQ-05 — OPM Cross-Check
# ---------------------------------------------------------

def check_opm_crosscheck(
    df: pd.DataFrame,
    source_column: str = "opm_percentage",
    operating_profit_column: str = "op_profit",
    sales_column: str = "sales",
    tolerance: float = 1.0,
) -> bool:
    required = {
        source_column,
        operating_profit_column,
        sales_column,
    }

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    for _, row in df.iterrows():
        sales = row[sales_column]

        if pd.isna(sales) or sales == 0:
            continue

        computed = row[operating_profit_column] / sales * 100
        source = row[source_column]

        if pd.isna(source):
            continue

        if abs(source - computed) >= tolerance:
            return False

    return True


# ---------------------------------------------------------
# DQ-06 — Positive Sales
# ---------------------------------------------------------

def check_positive_sales(
    df: pd.DataFrame,
    sales_column: str = "sales",
    financials_column: str = "broad_sector",
) -> bool:
    if sales_column not in df.columns:
        raise ValueError(f"Column '{sales_column}' not found")

    for _, row in df.iterrows():
        if (
            financials_column in df.columns
            and str(row[financials_column]).strip().lower()
            == "financials"
        ):
            continue

        if pd.notna(row[sales_column]) and row[sales_column] <= 0:
            return False

    return True


# ---------------------------------------------------------
# DQ-07 — Year Format
# ---------------------------------------------------------

def check_year_format(
    values: pd.Series,
) -> bool:
    pattern = re.compile(r"^\d{4}-\d{2}$")

    for value in values.dropna():
        if not pattern.match(str(value).strip()):
            return False

    return True


# ---------------------------------------------------------
# DQ-08 — Ticker Format
# ---------------------------------------------------------

def check_ticker_format(
    values: pd.Series,
) -> bool:
    for value in values.dropna():
        ticker = str(value).strip().upper()

        if not 2 <= len(ticker) <= 12:
            return False

    return True


# ---------------------------------------------------------
# DQ-09 — Net Cash Check
# ---------------------------------------------------------

def check_net_cash(
    df: pd.DataFrame,
    net_cash_column: str = "net_cash_flow",
    cfo_column: str = "CFO",
    cfi_column: str = "CFI",
    cff_column: str = "CFF",
    tolerance: float = 10.0,
) -> bool:
    required = {
        net_cash_column,
        cfo_column,
        cfi_column,
        cff_column,
    }

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    for _, row in df.iterrows():
        values = [
            row[net_cash_column],
            row[cfo_column],
            row[cfi_column],
            row[cff_column],
        ]

        if any(pd.isna(value) for value in values):
            continue

        computed = row[cfo_column] + row[cfi_column] + row[cff_column]

        if abs(row[net_cash_column] - computed) > tolerance:
            return False

    return True


# ---------------------------------------------------------
# DQ-10 — Non-Negative Fixed Assets
# ---------------------------------------------------------

def check_fixed_assets(
    df: pd.DataFrame,
    column: str = "fixed_assets",
) -> bool:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    values = df[column].dropna()

    return (values >= 0).all()


# ---------------------------------------------------------
# DQ-11 — Tax Rate Range
# ---------------------------------------------------------

def check_tax_rate(
    df: pd.DataFrame,
    column: str = "tax_percentage",
) -> bool:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    values = df[column].dropna()

    return ((values >= 0) & (values <= 60)).all()


# ---------------------------------------------------------
# DQ-12 — Dividend Payout Cap
# ---------------------------------------------------------

def check_dividend_payout(
    df: pd.DataFrame,
    column: str = "dividend_payout",
) -> bool:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    values = df[column].dropna()

    return (values <= 200).all()


# ---------------------------------------------------------
# DQ-13 — URL Validity
# ---------------------------------------------------------

def check_url_format(
    values: pd.Series,
) -> bool:
    """
    Structural URL check.

    Actual HTTP HEAD validation will be performed during
    the ETL validation run because URLs can decay over time.
    """
    url_pattern = re.compile(
        r"^https?://.+",
        re.IGNORECASE,
    )

    for value in values.dropna():
        if not url_pattern.match(str(value).strip()):
            return False

    return True


# ---------------------------------------------------------
# DQ-14 — EPS Sign Consistency
# ---------------------------------------------------------

def check_eps_sign_consistency(
    df: pd.DataFrame,
    eps_column: str = "eps",
    profit_column: str = "net_profit",
) -> bool:
    required = {eps_column, profit_column}

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    for _, row in df.iterrows():
        profit = row[profit_column]
        eps = row[eps_column]

        if pd.isna(profit) or pd.isna(eps):
            continue

        if profit > 0 and eps <= 0:
            return False

    return True


# ---------------------------------------------------------
# DQ-15 — BSE/ASE Balance
# ---------------------------------------------------------

def check_bse_ase_balance(
    df: pd.DataFrame,
    assets_column: str = "total_assets",
    liabilities_column: str = "total_liabilities",
) -> bool:
    required = {
        assets_column,
        liabilities_column,
    }

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    valid = df[[assets_column, liabilities_column]].dropna()

    return (valid[assets_column] == valid[liabilities_column]).all()


# ---------------------------------------------------------
# DQ-16 — Coverage Check
# ---------------------------------------------------------

def check_coverage(
    df: pd.DataFrame,
    company_column: str = "company_id",
    year_column: str = "year",
    minimum_years: int = 5,
) -> bool:
    required = {company_column, year_column}

    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    coverage = df.groupby(company_column)[year_column].nunique()

    return (coverage >= minimum_years).all()


# ---------------------------------------------------------
# Generic DQ Result
# ---------------------------------------------------------

def make_dq_result(
    rule_id: str,
    passed: bool,
    severity: str,
    message: str,
    company_id: Any = None,
    field: str = "",
) -> dict:
    return {
        "rule_id": rule_id,
        "company_id": company_id,
        "field": field,
        "issue": message if not passed else "",
        "severity": severity,
        "status": "PASS" if passed else "FAIL",
    }