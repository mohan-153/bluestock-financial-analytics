"""
Bluestock Financial Analytics
Sprint 2 - Day 13
Bank / Financials Carve-out

Classifies companies using the sectors table and applies the Financials
carve-out required by the analytics/screener.

Financial companies are retained in the master dataset, but industrial-only
metrics are marked as excluded for Financials:
- Debt to Equity
- Interest Coverage
- Asset Turnover
- Operating Profit Margin
- Free Cash Flow

The carve-out is classification-based; raw data is never modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "financials_carveout_day13.csv"
EDGE_LOG = OUTPUT_DIR / "financials_carveout_edge_cases.log"

FINANCIAL_KEYWORDS = (
    "financial",
    "finance",
    "bank",
    "insurance",
    "nbfc",
    "lending",
    "credit",
    "housing finance",
)


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def classify_financial_company(
    broad_sector,
    sub_sector,
) -> bool:
    """
    Return True for companies whose sector/sub-sector indicates Financials.

    Both broad_sector and sub_sector are checked because source classification
    can vary between the two fields.
    """
    text = f"{normalize_text(broad_sector)} {normalize_text(sub_sector)}"

    return any(keyword in text for keyword in FINANCIAL_KEYWORDS)


def classify_sector_table(sectors: pd.DataFrame) -> pd.DataFrame:
    required = [
        "company_id",
        "broad_sector",
        "sub_sector",
    ]

    missing = [column for column in required if column not in sectors.columns]
    if missing:
        raise ValueError(f"sectors missing columns: {missing}")

    df = sectors[required].copy()

    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )

    df["is_financial_company"] = df.apply(
        lambda row: classify_financial_company(
            row["broad_sector"],
            row["sub_sector"],
        ),
        axis=1,
    )

    df["carve_out_category"] = df["is_financial_company"].map(
        {
            True: "FINANCIALS",
            False: "NON_FINANCIALS",
        }
    )

    return df


def apply_carve_out(
    ratios: pd.DataFrame,
    sector_classification: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply the carve-out to an existing financial-ratios dataset.

    Financial companies remain present, but industrial-only metrics are
    excluded by setting them to None/NaN and adding explicit flags.
    """
    df = ratios.copy()

    if "company_id" not in df.columns:
        raise ValueError("ratios must contain company_id")

    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )

    classification = sector_classification[
        [
            "company_id",
            "broad_sector",
            "sub_sector",
            "is_financial_company",
            "carve_out_category",
        ]
    ].drop_duplicates("company_id")

    df = df.merge(
        classification,
        on="company_id",
        how="left",
    )

    df["is_financial_company"] = (
        df["is_financial_company"].fillna(False).astype(bool)
    )

    df["carve_out_category"] = df["carve_out_category"].fillna(
        "UNCLASSIFIED"
    )

    industrial_only_metrics = [
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "operating_profit_margin_pct",
        "free_cash_flow_cr",
    ]

    for column in industrial_only_metrics:
        if column in df.columns:
            df.loc[df["is_financial_company"], column] = None

    df["industrial_screener_eligible"] = ~df["is_financial_company"]

    return df


def build_day13_output(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sectors = classify_sector_table(data["sectors"])

    # Recalculate the Day-12 ratios from the same loaded source data so
    # Day-13 can be executed from the project without depending on an
    # already-generated CSV.
    from src.analytics.financial_ratios_day12 import (
        calculate_financial_ratios,
    )

    ratios = calculate_financial_ratios(data)

    return apply_carve_out(ratios, sectors)


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    financial_rows = result[result["is_financial_company"]]
    non_financial_rows = result[~result["is_financial_company"]]

    lines = [
        "BLUESTOCK FINANCIALS CARVE-OUT - DAY 13",
        "=" * 70,
        f"Total rows: {len(result)}",
        f"Financial rows: {len(financial_rows)}",
        f"Non-financial rows: {len(non_financial_rows)}",
        "",
        "Company classification:",
    ]

    company_summary = (
        result[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
                "is_financial_company",
            ]
        ]
        .drop_duplicates("company_id")
        .sort_values("company_id")
    )

    counts = company_summary["is_financial_company"].value_counts()

    lines.append(
        f"Financial companies: {int(counts.get(True, 0))}"
    )
    lines.append(
        f"Non-financial companies: {int(counts.get(False, 0))}"
    )

    lines.extend(
        [
            "",
            "Financial sector breakdown:",
        ]
    )

    breakdown = (
        company_summary[company_summary["is_financial_company"]]
        .groupby("broad_sector", dropna=False)
        .size()
        .sort_values(ascending=False)
    )

    if breakdown.empty:
        lines.append("No financial companies detected.")
    else:
        for sector, count in breakdown.items():
            lines.append(f"{sector}: {int(count)}")

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 13 FINANCIALS CARVE-OUT")
    print("=" * 70)

    data = load_all_data()
    result = build_day13_output(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    companies = result.drop_duplicates("company_id")

    print(f"Rows generated          : {len(result)}")
    print(
        "Financial companies     : "
        f"{int(companies['is_financial_company'].sum())}"
    )
    print(
        "Non-financial companies : "
        f"{int((~companies['is_financial_company']).sum())}"
    )
    print(f"Output                  : {OUTPUT_CSV}")
    print(f"Edge log                : {EDGE_LOG}")
    print()

    print(
        result[
            [
                "company_id",
                "year",
                "broad_sector",
                "sub_sector",
                "is_financial_company",
                "debt_to_equity",
                "interest_coverage",
                "asset_turnover",
                "industrial_screener_eligible",
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()
