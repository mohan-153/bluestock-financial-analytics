"""
Bluestock Financial Analytics
Sprint 2 - Day 14
KPI Validation + Screener Preview

Builds a first screening layer from the Day 8-13 analytics.

Rules:
- Financial companies are excluded from industrial-only screening.
- Missing KPI values do not pass a threshold.
- Thresholds are explicit and easy to change.
- This is a PREVIEW screener, not investment advice.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data
from src.analytics.cagr import calculate_cagr
from src.analytics.financial_ratios_day12 import calculate_financial_ratios
from src.analytics.financials_carveout_day13 import classify_sector_table, apply_carve_out


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "screener_preview_day14.csv"
EDGE_LOG = OUTPUT_DIR / "screener_day14_edge_cases.log"

# Conservative preview thresholds. These are project screening parameters,
# not claims about investment quality.
DEFAULT_THRESHOLDS = {
    "roe_min_pct": 15.0,
    "roce_min_pct": 15.0,
    "debt_to_equity_max": 1.0,
    "interest_coverage_min": 3.0,
    "opm_min_pct": 10.0,
    "cfo_to_sales_min_pct": 5.0,
}


def _number(value) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def passes_min(value, threshold: float) -> bool:
    value = _number(value)
    return value is not None and value >= threshold


def passes_max(value, threshold: float) -> bool:
    value = _number(value)
    return value is not None and value <= threshold


def build_screener_flags(
    row: pd.Series,
    thresholds: dict = DEFAULT_THRESHOLDS,
) -> dict:
    """
    Return individual KPI flags and an overall preview decision.

    Financial companies are not required to satisfy industrial-only metrics.
    """
    is_financial = bool(row.get("is_financial_company", False))

    roe_pass = passes_min(row.get("return_on_equity_pct"), thresholds["roe_min_pct"])
    roce_pass = passes_min(row.get("roce_pct"), thresholds["roce_min_pct"])
    opm_pass = passes_min(
        row.get("operating_profit_margin_pct"),
        thresholds["opm_min_pct"],
    )
    cfo_sales_pass = passes_min(
        row.get("cfo_to_sales_pct"),
        thresholds["cfo_to_sales_min_pct"],
    )

    if is_financial:
        de_pass = True
        icr_pass = True
    else:
        de_pass = passes_max(
            row.get("debt_to_equity"),
            thresholds["debt_to_equity_max"],
        )
        icr_pass = passes_min(
            row.get("interest_coverage"),
            thresholds["interest_coverage_min"],
        )

    checks = [roe_pass, roce_pass, opm_pass, cfo_sales_pass, de_pass, icr_pass]

    return {
        "roe_pass": roe_pass,
        "roce_pass": roce_pass,
        "opm_pass": opm_pass,
        "cfo_sales_pass": cfo_sales_pass,
        "de_pass": de_pass,
        "icr_pass": icr_pass,
        "kpi_pass_count": sum(checks),
        "screener_pass": all(checks),
    }


def _extract_roce(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate ROCE using the Day-8 definition:
        EBIT / (Equity + Borrowings) * 100
    """
    pl = data["profitandloss"][
        [
            "company_id", "year", "operating_profit", "depreciation"
        ]
    ].copy()

    bs = data["balancesheet"][
        [
            "company_id", "year", "equity_capital", "reserves", "borrowings"
        ]
    ].copy()

    for df in (pl, bs):
        df["company_id"] = (
            df["company_id"].astype(str).str.strip().str.upper()
        )

    df = pl.merge(bs, on=["company_id", "year"], how="left")

    ebit = (
        pd.to_numeric(df["operating_profit"], errors="coerce")
        - pd.to_numeric(df["depreciation"], errors="coerce")
    )
    capital = (
        pd.to_numeric(df["equity_capital"], errors="coerce")
        + pd.to_numeric(df["reserves"], errors="coerce")
        + pd.to_numeric(df["borrowings"], errors="coerce")
    )

    df["roce_pct"] = (ebit / capital.where(capital > 0)) * 100

    return df[["company_id", "year", "roce_pct"]]


def _extract_cfo_sales(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cf = data["cashflow"][
        ["company_id", "year", "operating_activity"]
    ].copy()

    pl = data["profitandloss"][
        ["company_id", "year", "sales"]
    ].copy()

    for df in (cf, pl):
        df["company_id"] = (
            df["company_id"].astype(str).str.strip().str.upper()
        )

    df = cf.merge(pl, on=["company_id", "year"], how="left")

    cfo = pd.to_numeric(df["operating_activity"], errors="coerce")
    sales = pd.to_numeric(df["sales"], errors="coerce")

    df["cfo_to_sales_pct"] = (cfo / sales.where(sales != 0)) * 100

    return df[["company_id", "year", "cfo_to_sales_pct"]]


def _extract_latest_cagr(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Add latest available 3Y revenue and PAT CAGR where the exact start year
    exists. Edge cases remain represented by their status.
    """
    pl = data["profitandloss"][
        ["company_id", "year", "sales", "net_profit"]
    ].copy()

    pl["company_id"] = (
        pl["company_id"].astype(str).str.strip().str.upper()
    )

    def year_num(value):
        try:
            return int(str(value)[:4])
        except (TypeError, ValueError):
            return None

    pl["fiscal_year"] = pl["year"].map(year_num)
    pl["sales"] = pd.to_numeric(pl["sales"], errors="coerce")
    pl["net_profit"] = pd.to_numeric(pl["net_profit"], errors="coerce")
    pl = pl.dropna(subset=["fiscal_year"])

    rows = []

    for company_id, group in pl.groupby("company_id"):
        group = group.sort_values("fiscal_year")
        end = group.iloc[-1]
        end_year = int(end["fiscal_year"])
        start = group[group["fiscal_year"] == end_year - 3]

        if start.empty:
            revenue = (None, "INSUFFICIENT")
            pat = (None, "INSUFFICIENT")
        else:
            start = start.iloc[0]
            revenue_result = calculate_cagr(
                start["sales"], end["sales"], 3
            )
            pat_result = calculate_cagr(
                start["net_profit"], end["net_profit"], 3
            )
            revenue = (revenue_result.value, revenue_result.status)
            pat = (pat_result.value, pat_result.status)

        rows.append(
            {
                "company_id": company_id,
                "cagr_end_year": end_year,
                "revenue_cagr_3y_pct": revenue[0],
                "revenue_cagr_3y_status": revenue[1],
                "pat_cagr_3y_pct": pat[0],
                "pat_cagr_3y_status": pat[1],
            }
        )

    return pd.DataFrame(rows)


def build_screener_preview(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    ratios = calculate_financial_ratios(data)
    sectors = classify_sector_table(data["sectors"])

    # Add Day-13 financial carve-out.
    ratios = apply_carve_out(ratios, sectors)

    roce = _extract_roce(data)
    cfo_sales = _extract_cfo_sales(data)
    cagr = _extract_latest_cagr(data)

    df = ratios.merge(
        roce,
        on=["company_id", "year"],
        how="left",
    )

    df = df.merge(
        cfo_sales,
        on=["company_id", "year"],
        how="left",
    )

    df = df.merge(
        cagr,
        on="company_id",
        how="left",
    )

    flags = df.apply(
        lambda row: pd.Series(build_screener_flags(row)),
        axis=1,
    )

    return pd.concat([df, flags], axis=1)


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    companies = result.drop_duplicates("company_id")

    lines = [
        "BLUESTOCK SCREENER PREVIEW - DAY 14",
        "=" * 70,
        f"Rows generated: {len(result)}",
        f"Companies: {len(companies)}",
        f"Rows passing screener: {int(result['screener_pass'].sum())}",
        "",
        "Company-level classification:",
        f"Financial companies: {int(companies['is_financial_company'].sum())}",
        f"Non-financial companies: {int((~companies['is_financial_company']).sum())}",
        "",
        "Pass counts by KPI:",
    ]

    for column in [
        "roe_pass",
        "roce_pass",
        "opm_pass",
        "cfo_sales_pass",
        "de_pass",
        "icr_pass",
    ]:
        lines.append(f"{column}: {int(result[column].sum())}")

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 14 KPI + SCREENER PREVIEW")
    print("=" * 70)

    data = load_all_data()
    result = build_screener_preview(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows generated : {len(result)}")
    print(
        "Companies      : "
        f"{result['company_id'].nunique()}"
    )
    print(
        "Screener pass  : "
        f"{int(result['screener_pass'].sum())}"
    )
    print(f"Output         : {OUTPUT_CSV}")
    print(f"Edge log       : {EDGE_LOG}")
    print()
    print(
        result[
            [
                "company_id",
                "year",
                "broad_sector",
                "is_financial_company",
                "roe_pass",
                "roce_pass",
                "opm_pass",
                "cfo_sales_pass",
                "de_pass",
                "icr_pass",
                "kpi_pass_count",
                "screener_pass",
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()
