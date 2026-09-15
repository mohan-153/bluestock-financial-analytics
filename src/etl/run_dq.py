from pathlib import Path
import re
import csv
import sqlite3

import pandas as pd
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from src.etl.loader import load_all_data


OUTPUT_FILE = Path("output/validation_failures.csv")
INFO_FILE = Path("output/dq_info.csv")

FINANCIAL_DATASETS = ["profitandloss", "balancesheet", "cashflow"]
CHILD_DATASETS = [
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "market_cap",
    "stock_prices",
    "financial_ratios",
    "peer_groups",
]


def add_failure(
    failures,
    rule_id,
    severity,
    issue,
    company_id=None,
    year=None,
    field="",
):
    failures.append(
        {
            "rule_id": rule_id,
            "company_id": company_id,
            "year": year,
            "field": field,
            "issue": issue,
            "severity": severity,
        }
    )


def find_column(df, candidates):
    lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        if candidate.strip().lower() in lookup:
            return lookup[candidate.strip().lower()]

    return None


def normalize_ids(series):
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


def numeric(series):
    return pd.to_numeric(series, errors="coerce")


# ============================================================
# DQ-01 — COMPANY PK UNIQUENESS
# ============================================================

def validate_dq01(companies, failures):
    id_col = find_column(companies, ["id", "company_id"])

    if id_col is None:
        add_failure(
            failures,
            "DQ-01",
            "CRITICAL",
            "companies: company ID column not found",
            field="id",
        )
        return

    ids = normalize_ids(companies[id_col])

    if ids.isna().any():
        for idx in companies.index[ids.isna()]:
            add_failure(
                failures,
                "DQ-01",
                "CRITICAL",
                "companies: null company ID",
                field=id_col,
            )

    duplicate_mask = ids.duplicated(keep=False) & ids.notna()

    for value in sorted(ids[duplicate_mask].unique()):
        add_failure(
            failures,
            "DQ-01",
            "CRITICAL",
            f"Duplicate company ID: {value}",
            company_id=value,
            field=id_col,
        )


# ============================================================
# DQ-02 — ANNUAL PK UNIQUENESS
# ============================================================

def validate_dq02(df, dataset_name, failures):
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year", "financial_year", "fy"])

    if company_col is None or year_col is None:
        add_failure(
            failures,
            "DQ-02",
            "CRITICAL",
            f"{dataset_name}: required company_id/year columns missing",
            field="company_id,year",
        )
        return

    temp = pd.DataFrame(
        {
            "company_id": normalize_ids(df[company_col]),
            "year": df[year_col].astype("string").str.strip(),
        }
    )

    duplicate_mask = temp.duplicated(
        subset=["company_id", "year"],
        keep=False,
    )

    duplicates = (
        temp.loc[duplicate_mask]
        .drop_duplicates()
        .sort_values(["company_id", "year"])
    )

    for _, row in duplicates.iterrows():
        add_failure(
            failures,
            "DQ-02",
            "CRITICAL",
            "Duplicate company/year combination",
            company_id=row["company_id"],
            year=row["year"],
            field="company_id,year",
        )



# ============================================================
# DQ-03 — FK INTEGRITY
# ============================================================

def validate_dq03(data, failures, info_rows):
    """
    Validate FK integrity on the FINAL SQLite database.

    The loader already rejects orphan source rows. Those rejected source
    rows must not be counted again as unresolved database CRITICAL failures.
    """

    db_path = Path("data/nifty100.db")

    if not db_path.exists():
        add_failure(
            failures,
            "DQ-03",
            "CRITICAL",
            "Final SQLite database does not exist",
            field="foreign_keys",
        )
        return

    connection = sqlite3.connect(str(db_path))

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        for table, rowid, parent, fk_index in violations:
            add_failure(
                failures,
                "DQ-03",
                "CRITICAL",
                (
                    f"SQLite foreign-key violation: "
                    f"table={table}, rowid={rowid}, parent={parent}, "
                    f"fk_index={fk_index}"
                ),
                field="company_id",
            )

    finally:
        connection.close()

    # Preserve the source-orphan audit without counting it as a current
    # database failure.
    companies = data["companies"]
    parent_col = find_column(companies, ["id", "company_id"])

    if parent_col is None:
        return

    parent_ids = set(normalize_ids(companies[parent_col].dropna()))

    for dataset_name in CHILD_DATASETS:
        if dataset_name not in data:
            continue

        df = data[dataset_name]
        child_col = find_column(df, ["company_id"])

        if child_col is None:
            continue

        child_ids = normalize_ids(df[child_col])
        invalid_mask = child_ids.notna() & ~child_ids.isin(parent_ids)
        rejected_count = int(invalid_mask.sum())

        if rejected_count:
            info_rows.append(
                {
                    "rule_id": "DQ-03",
                    "company_id": "",
                    "year": "",
                    "issue": (
                        f"{dataset_name}: {rejected_count} orphan source "
                        f"row(s) were rejected before database insertion"
                    ),
                    "severity": "INFO",
                }
            )


# ============================================================
# DQ-04 — BALANCE SHEET BALANCE
# ============================================================

def validate_dq04(df, failures):
    assets_col = find_column(df, ["total_assets"])
    liabilities_col = find_column(df, ["total_liabilities"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not assets_col or not liabilities_col:
        add_failure(
            failures,
            "DQ-04",
            "WARNING",
            "balancesheet: total_assets or total_liabilities column missing",
            field="total_assets,total_liabilities",
        )
        return

    assets = numeric(df[assets_col])
    liabilities = numeric(df[liabilities_col])

    valid = assets.notna() & liabilities.notna() & (assets != 0)

    ratio = pd.Series(index=df.index, dtype="float64")
    ratio.loc[valid] = (
        (assets.loc[valid] - liabilities.loc[valid]).abs()
        / assets.loc[valid].abs()
    )

    for idx in df.index[valid & (ratio >= 0.01)]:
        add_failure(
            failures,
            "DQ-04",
            "WARNING",
            (
                f"|total_assets-total_liabilities|/"
                f"|total_assets| >= 1%; "
                f"assets={assets.loc[idx]}, "
                f"liabilities={liabilities.loc[idx]}"
            ),
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=f"{assets_col},{liabilities_col}",
        )



# ============================================================
# DQ-05 — OPM CROSS-CHECK
# ============================================================

def validate_dq05(df, sectors, failures):
    """
    Cross-check source OPM against operating_profit / sales.

    Financial companies are excluded because bank/insurance financial
    statements do not use operating-profit/sales in the same way as
    industrial companies.
    """

    sales_col = find_column(df, ["sales"])
    op_col = find_column(df, ["operating_profit", "op_profit"])
    source_opm_col = find_column(df, ["opm_percentage"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not sales_col or not op_col or not source_opm_col:
        add_failure(
            failures,
            "DQ-05",
            "WARNING",
            "profitandloss: OPM cross-check columns missing",
            field="sales,operating_profit,opm_percentage",
        )
        return

    financial_ids = set()

    if sectors is not None:
        sector_company_col = find_column(sectors, ["company_id"])
        sector_col = find_column(sectors, ["broad_sector", "sub_sector"])

        if sector_company_col and sector_col:
            sector_text = (
                sectors[sector_col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            financial_mask = (
                sector_text.str.contains("financial", na=False)
                | sector_text.str.contains("bank", na=False)
                | sector_text.str.contains("insurance", na=False)
                | sector_text.str.contains("nbfc", na=False)
                | sector_text.str.contains("finance", na=False)
            )

            financial_ids = set(
                normalize_ids(
                    sectors.loc[
                        financial_mask,
                        sector_company_col,
                    ].dropna()
                )
            )

    sales = numeric(df[sales_col])
    op_profit = numeric(df[op_col])
    source_opm = numeric(df[source_opm_col])

    company_ids = normalize_ids(df[company_col])

    valid = (
        sales.notna()
        & op_profit.notna()
        & source_opm.notna()
        & (sales != 0)
    )

    # Exclude Financials from the OPM cross-check.
    valid &= ~company_ids.isin(financial_ids)

    computed = pd.Series(index=df.index, dtype="float64")
    computed.loc[valid] = (
        op_profit.loc[valid] / sales.loc[valid] * 100
    )

    mismatch = valid & (
        (source_opm - computed).abs() >= 1.0
    )

    for idx in df.index[mismatch]:
        add_failure(
            failures,
            "DQ-05",
            "WARNING",
            (
                f"OPM mismatch: source={source_opm.loc[idx]:.4f}, "
                f"computed={computed.loc[idx]:.4f}"
            ),
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=source_opm_col,
        )


# ============================================================
# DQ-06 — POSITIVE SALES
# ============================================================

def validate_dq06(df, sectors, failures):
    sales_col = find_column(df, ["sales"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not sales_col or not company_col:
        return

    financial_ids = set()

    if sectors is not None:
        sector_company_col = find_column(sectors, ["company_id"])
        sector_col = find_column(sectors, ["broad_sector"])

        if sector_company_col and sector_col:
            sector_text = (
                sectors[sector_col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            mask = (
                sector_text.str.contains("financial", na=False)
                | sector_text.str.contains("bank", na=False)
                | sector_text.str.contains("insurance", na=False)
                | sector_text.str.contains("nbfc", na=False)
            )

            financial_ids = set(
                normalize_ids(
                    sectors.loc[mask, sector_company_col]
                )
            )

    sales = numeric(df[sales_col])
    company_ids = normalize_ids(df[company_col])

    for idx in df.index[sales.notna() & (sales <= 0)]:
        company_id = company_ids.loc[idx]

        # Financial companies are carved out.
        if company_id in financial_ids:
            continue

        add_failure(
            failures,
            "DQ-06",
            "WARNING",
            f"Sales must be positive; found {sales.loc[idx]}",
            company_id=company_id,
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=sales_col,
        )


# ============================================================
# DQ-07 — YEAR FORMAT
# ============================================================

def validate_dq07(df, dataset_name, failures):
    year_col = find_column(df, ["year", "financial_year", "fy"])

    if year_col is None:
        return

    pattern = re.compile(r"^\d{4}-\d{2}$")

    for idx in df.index:
        value = df.loc[idx, year_col]

        if pd.isna(value):
            add_failure(
                failures,
                "DQ-07",
                "CRITICAL",
                f"{dataset_name}: missing financial year",
                company_id=df.loc[idx].get("company_id"),
                field=year_col,
            )
            continue

        text = str(value).strip()

        if not pattern.fullmatch(text):
            add_failure(
                failures,
                "DQ-07",
                "CRITICAL",
                f"{dataset_name}: invalid financial year format: {value}",
                company_id=df.loc[idx].get("company_id"),
                year=value,
                field=year_col,
            )


# ============================================================
# DQ-08 — TICKER FORMAT
# ============================================================

def validate_dq08(companies, failures):
    ticker_col = find_column(companies, ["company_id", "id"])

    if ticker_col is None:
        add_failure(
            failures,
            "DQ-08",
            "CRITICAL",
            "Ticker/company_id column not found",
            field="company_id",
        )
        return

    tickers = normalize_ids(companies[ticker_col])

    for idx in companies.index:
        value = tickers.loc[idx]

        if pd.isna(value):
            add_failure(
                failures,
                "DQ-08",
                "CRITICAL",
                "Missing ticker/company_id",
                field=ticker_col,
            )
            continue

        if not 2 <= len(value) <= 12:
            add_failure(
                failures,
                "DQ-08",
                "CRITICAL",
                f"Ticker length must be 2–12 characters; found '{value}'",
                company_id=value,
                field=ticker_col,
            )


# ============================================================
# DQ-09 — NET CASH CHECK
# ============================================================

def validate_dq09(df, failures):
    cfo_col = find_column(df, ["operating_activity", "cfo"])
    cfi_col = find_column(df, ["investing_activity", "cfi"])
    cff_col = find_column(df, ["financing_activity", "cff"])
    net_col = find_column(df, ["net_cash_flow"])

    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not all([cfo_col, cfi_col, cff_col, net_col]):
        add_failure(
            failures,
            "DQ-09",
            "WARNING",
            "cashflow: required cash-flow columns missing",
            field="operating_activity,investing_activity,financing_activity,net_cash_flow",
        )
        return

    cfo = numeric(df[cfo_col])
    cfi = numeric(df[cfi_col])
    cff = numeric(df[cff_col])
    reported = numeric(df[net_col])

    valid = (
        cfo.notna()
        & cfi.notna()
        & cff.notna()
        & reported.notna()
    )

    computed = cfo + cfi + cff
    mismatch = valid & (reported - computed).abs().gt(10)

    for idx in df.index[mismatch]:
        add_failure(
            failures,
            "DQ-09",
            "WARNING",
            (
                f"Net cash mismatch: reported={reported.loc[idx]}, "
                f"computed={computed.loc[idx]}, "
                f"difference={(reported.loc[idx] - computed.loc[idx]):.4f}"
            ),
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=net_col,
        )


# ============================================================
# DQ-10 — NON-NEGATIVE FIXED ASSETS
# ============================================================

def validate_dq10(df, failures):
    fixed_col = find_column(df, ["fixed_assets"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not fixed_col:
        add_failure(
            failures,
            "DQ-10",
            "WARNING",
            "balancesheet: fixed_assets column missing",
            field="fixed_assets",
        )
        return

    fixed = numeric(df[fixed_col])

    for idx in df.index[fixed.notna() & (fixed < 0)]:
        add_failure(
            failures,
            "DQ-10",
            "WARNING",
            f"Negative fixed assets: {fixed.loc[idx]}",
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=fixed_col,
        )


# ============================================================
# DQ-11 — TAX RATE RANGE
# ============================================================

def validate_dq11(df, failures):
    tax_col = find_column(df, ["tax_percentage", "tax_rate"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not tax_col:
        add_failure(
            failures,
            "DQ-11",
            "WARNING",
            "profitandloss: tax_percentage column missing",
            field="tax_percentage",
        )
        return

    tax = numeric(df[tax_col])

    for idx in df.index[tax.notna() & ((tax < 0) | (tax > 60))]:
        add_failure(
            failures,
            "DQ-11",
            "WARNING",
            f"Tax rate outside 0–60%: {tax.loc[idx]}",
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=tax_col,
        )


# ============================================================
# DQ-12 — DIVIDEND PAYOUT CAP
# ============================================================

def validate_dq12(df, failures):
    payout_col = find_column(df, ["dividend_payout"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not payout_col:
        add_failure(
            failures,
            "DQ-12",
            "WARNING",
            "profitandloss: dividend_payout column missing",
            field="dividend_payout",
        )
        return

    payout = numeric(df[payout_col])

    for idx in df.index[payout.notna() & (payout > 200)]:
        add_failure(
            failures,
            "DQ-12",
            "WARNING",
            f"Dividend payout exceeds 200%: {payout.loc[idx]}",
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=payout_col,
        )


# ============================================================
# DQ-13 — DOCUMENT URL VALIDITY
# ============================================================

def validate_dq13(df, failures):
    url_col = find_column(df, ["annual_report", "Annual_Report"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not url_col:
        add_failure(
            failures,
            "DQ-13",
            "WARNING",
            "documents: Annual_Report column missing",
            field="annual_report",
        )
        return

    cache = {}

    for idx in df.index:
        value = df.loc[idx, url_col]

        if pd.isna(value) or not str(value).strip():
            add_failure(
                failures,
                "DQ-13",
                "WARNING",
                "Annual report URL is empty",
                company_id=(
                    df.loc[idx, company_col]
                    if company_col
                    else None
                ),
                year=(
                    df.loc[idx, year_col]
                    if year_col
                    else None
                ),
                field=url_col,
            )
            continue

        url = str(value).strip()

        if url in cache:
            status = cache[url]
        else:
            try:
                request = Request(
                    url,
                    method="HEAD",
                    headers={
                        "User-Agent": "Bluestock-DQ-Validator/1.0"
                    },
                )

                with urlopen(request, timeout=10) as response:
                    status = response.status

            except HTTPError as exc:
                status = exc.code

            except URLError as exc:
                status = f"ERROR: {type(exc.reason).__name__}"

            except Exception as exc:
                status = f"ERROR: {type(exc).__name__}"

            cache[url] = status

        if status != 200:
            add_failure(
                failures,
                "DQ-13",
                "WARNING",
                f"Annual report URL HEAD status: {status}",
                company_id=(
                    df.loc[idx, company_col]
                    if company_col
                    else None
                ),
                year=(
                    df.loc[idx, year_col]
                    if year_col
                    else None
                ),
                field=url_col,
            )


# ============================================================
# DQ-14 — EPS SIGN CONSISTENCY
# ============================================================

def validate_dq14(df, failures):
    eps_col = find_column(df, ["eps"])
    profit_col = find_column(df, ["net_profit"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    if not eps_col or not profit_col:
        add_failure(
            failures,
            "DQ-14",
            "WARNING",
            "profitandloss: eps or net_profit column missing",
            field="eps,net_profit",
        )
        return

    eps = numeric(df[eps_col])
    profit = numeric(df[profit_col])

    positive_mismatch = (
        profit.gt(0)
        & eps.notna()
        & eps.le(0)
    )

    negative_mismatch = (
        profit.lt(0)
        & eps.notna()
        & eps.ge(0)
    )

    mismatch = positive_mismatch | negative_mismatch

    for idx in df.index[mismatch]:
        add_failure(
            failures,
            "DQ-14",
            "WARNING",
            (
                f"EPS sign inconsistent with net profit: "
                f"net_profit={profit.loc[idx]}, eps={eps.loc[idx]}"
            ),
            company_id=(
                df.loc[idx, company_col]
                if company_col
                else None
            ),
            year=(
                df.loc[idx, year_col]
                if year_col
                else None
            ),
            field=eps_col,
        )



# ============================================================
# DQ-15 — BSE/ASE BALANCE INFORMATIONAL
# ============================================================

def validate_dq15(df, info_rows):
    """
    Informational balance-sheet reconciliation.

    The source schema does not contain separate BSE/ASE balance fields.
    Therefore use the accounting identity available in the dataset:

        total_assets ≈ equity_capital + reserves + total_liabilities

    DQ-15 is INFO only and never contributes to validation failures.
    """

    assets_col = find_column(df, ["total_assets"])
    equity_col = find_column(df, ["equity_capital"])
    reserves_col = find_column(df, ["reserves"])
    liabilities_col = find_column(df, ["total_liabilities"])
    company_col = find_column(df, ["company_id"])
    year_col = find_column(df, ["year"])

    required = [
        assets_col,
        equity_col,
        reserves_col,
        liabilities_col,
    ]

    if not all(required):
        info_rows.append(
            {
                "rule_id": "DQ-15",
                "company_id": "",
                "year": "",
                "issue": (
                    "Balance-sheet reconciliation columns are unavailable"
                ),
                "severity": "INFO",
            }
        )
        return

    assets = numeric(df[assets_col])
    equity = numeric(df[equity_col])
    reserves = numeric(df[reserves_col])
    liabilities = numeric(df[liabilities_col])

    calculated_total = equity + reserves + liabilities

    valid = (
        assets.notna()
        & calculated_total.notna()
        & (assets != 0)
    )

    difference_pct = pd.Series(index=df.index, dtype="float64")
    difference_pct.loc[valid] = (
        (assets.loc[valid] - calculated_total.loc[valid]).abs()
        / assets.loc[valid].abs()
        * 100
    )

    mismatch = valid & (difference_pct >= 1.0)

    for idx in df.index[mismatch]:
        info_rows.append(
            {
                "rule_id": "DQ-15",
                "company_id": (
                    str(df.loc[idx, company_col]).strip().upper()
                ),
                "year": (
                    str(df.loc[idx, year_col])
                    if year_col
                    else ""
                ),
                "issue": (
                    f"Balance reconciliation difference="
                    f"{difference_pct.loc[idx]:.4f}%"
                ),
                "severity": "INFO",
            }
        )


# ============================================================
# DQ-16 — COVERAGE
# ============================================================

def validate_dq16(data, failures):
    coverage_frames = []

    for name in FINANCIAL_DATASETS:
        df = data[name]
        company_col = find_column(df, ["company_id"])
        year_col = find_column(df, ["year", "financial_year", "fy"])

        if company_col and year_col:
            coverage_frames.append(
                pd.DataFrame(
                    {
                        "company_id": normalize_ids(df[company_col]),
                        "year": df[year_col].astype("string").str.strip(),
                    }
                )
            )

    if not coverage_frames:
        return

    coverage = pd.concat(
        coverage_frames,
        ignore_index=True,
    ).drop_duplicates()

    # Each company must have >=5 distinct financial years
    counts = (
        coverage.groupby("company_id")["year"]
        .nunique()
    )

    for company_id, years in counts.items():
        if years < 5:
            add_failure(
                failures,
                "DQ-16",
                "WARNING",
                f"Company has only {years} years of data; expected at least 5",
                company_id=company_id,
                field="year",
            )


# ============================================================
# OUTPUT
# ============================================================

def save_outputs(failures, info_rows):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = pd.DataFrame(
        failures,
        columns=[
            "rule_id",
            "company_id",
            "year",
            "field",
            "issue",
            "severity",
        ],
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    info_result = pd.DataFrame(
        info_rows,
        columns=[
            "rule_id",
            "company_id",
            "year",
            "issue",
            "severity",
        ],
    )

    info_result.to_csv(
        INFO_FILE,
        index=False,
    )

    return result, info_result


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("BLUESTOCK — DATA QUALITY VALIDATION")
    print("=" * 70)

    # load_all_data() gives the normalized 12-dataset foundation.
    data = load_all_data()

    failures = []
    info_rows = []

    print("\nRunning DQ-01 ...")
    validate_dq01(data["companies"], failures)

    print("Running DQ-02 ...")
    for name in FINANCIAL_DATASETS:
        validate_dq02(data[name], name, failures)

    print("Running DQ-03 ...")
    validate_dq03(data, failures, info_rows)

    print("Running DQ-04 ...")
    validate_dq04(data["balancesheet"], failures)

    print("Running DQ-05 ...")
    validate_dq05(
        data["profitandloss"],
        data.get("sectors"),
        failures,
    )

    print("Running DQ-06 ...")
    validate_dq06(
        data["profitandloss"],
        data.get("sectors"),
        failures,
    )

    print("Running DQ-07 ...")
    for name in FINANCIAL_DATASETS:
        validate_dq07(data[name], name, failures)

    print("Running DQ-08 ...")
    validate_dq08(data["companies"], failures)

    print("Running DQ-09 ...")
    validate_dq09(data["cashflow"], failures)

    print("Running DQ-10 ...")
    validate_dq10(data["balancesheet"], failures)

    print("Running DQ-11 ...")
    validate_dq11(data["profitandloss"], failures)

    print("Running DQ-12 ...")
    validate_dq12(data["profitandloss"], failures)

    print("Running DQ-13 ...")
    validate_dq13(data["documents"], failures)

    print("Running DQ-14 ...")
    validate_dq14(data["profitandloss"], failures)

    print("Running DQ-15 ...")
    validate_dq15(data["balancesheet"], info_rows)

    print("Running DQ-16 ...")
    validate_dq16(data, failures)

    result, info_result = save_outputs(
        failures,
        info_rows,
    )

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    print(f"Total failures : {len(result)}")
    print(f"INFO records   : {len(info_result)}")

    if not result.empty:
        print("\nFailures by severity:")
        print(
            result["severity"]
            .value_counts()
            .to_string()
        )

        print("\nFailures by rule:")
        print(
            result["rule_id"]
            .value_counts()
            .sort_index()
            .to_string()
        )
    else:
        print("No WARNING/CRITICAL validation failures found.")

    print(f"\nFailures: {OUTPUT_FILE}")
    print(f"INFO:     {INFO_FILE}")


if __name__ == "__main__":
    main()
