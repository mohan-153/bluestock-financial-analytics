"""
Bluestock Financial Analytics
Sprint 3 - Day 20
Reporting Layer

Builds a consolidated business-facing reporting workbook/CSV outputs
from the existing analytics tables and generated CSV files.

No source/ETL data is modified.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

REPORT_CSV = OUTPUT_DIR / "blu_stock_report_day20.csv"
SCREENER_CSV = OUTPUT_DIR / "report_screener_day20.csv"
PEER_CSV = OUTPUT_DIR / "report_peer_summary_day20.csv"
MARKET_CSV = OUTPUT_DIR / "report_market_summary_day20.csv"
CAGR_CSV = OUTPUT_DIR / "report_cagr_summary_day20.csv"
REPORT_LOG = OUTPUT_DIR / "report_day20.log"


def read_sql(table: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)


def latest_per_company(df: pd.DataFrame, company_col: str = "company_id") -> pd.DataFrame:
    if df.empty:
        return df.copy()

    result = df.copy()

    if "year" in result.columns:
        result["_year_sort"] = pd.to_datetime(
            result["year"].astype(str),
            errors="coerce",
        )
        result = result.sort_values(
            [company_col, "_year_sort"],
            ascending=[True, False],
        )
        result = result.drop_duplicates(company_col, keep="first")
        result = result.drop(columns="_year_sort")

    return result


def build_screener_report() -> pd.DataFrame:
    df = latest_per_company(read_sql("screener_snapshot"))

    wanted = [
        "company_id",
        "year",
        "roe_pct",
        "roce_pct",
        "opm_pct",
        "cfo_to_sales_pct",
        "debt_to_equity",
        "interest_coverage",
        "kpi_pass_count",
        "screener_pass",
        "revenue_cagr_3y",
        "pat_cagr_3y",
    ]

    available = [column for column in wanted if column in df.columns]
    return df[available].copy()


def build_peer_report() -> pd.DataFrame:
    path = OUTPUT_DIR / "peer_comparison_day17.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    if df.empty:
        return df

    # One current/latest observation per company and peer group.
    if "year" in df.columns:
        df["_year_sort"] = pd.to_datetime(
            df["year"].astype(str),
            errors="coerce",
        )
        df = (
            df.sort_values("_year_sort", ascending=False)
            .drop_duplicates(["company_id", "peer_group_name"], keep="first")
            .drop(columns="_year_sort")
        )

    wanted = [
        "company_id",
        "peer_group_name",
        "year",
        "is_benchmark",
        "peer_group_size",
        "return_on_equity_pct_peer_rank",
        "roce_pct_peer_rank",
        "operating_profit_margin_pct_peer_rank",
        "debt_to_equity_peer_rank",
        "interest_coverage_peer_rank",
        "average_peer_rank",
    ]

    available = [column for column in wanted if column in df.columns]
    return df[available].copy()


def build_market_report() -> pd.DataFrame:
    path = OUTPUT_DIR / "stock_market_analytics_day16.csv"

    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    if df.empty:
        return df

    # Ensure year is available for selecting the latest annual record.
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

        df = (
            df.sort_values(["company_id", "year"])
            .drop_duplicates(subset=["company_id"], keep="last")
            .reset_index(drop=True)
        )
    else:
        # Fallback: one record per company if year is unavailable.
        df = (
            df.drop_duplicates(subset=["company_id"], keep="last")
            .reset_index(drop=True)
        )

    return df


def build_cagr_report() -> pd.DataFrame:
    path = OUTPUT_DIR / "cagr_results.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    if df.empty:
        return df

    # Keep the latest available observation for each company/period.
    if "company_id" in df.columns and "year" in df.columns:
        df["_year_sort"] = pd.to_datetime(
            df["year"].astype(str),
            errors="coerce",
        )
        df = (
            df.sort_values("_year_sort", ascending=False)
            .drop_duplicates(["company_id"], keep="first")
            .drop(columns="_year_sort")
        )

    return df


def build_company_summary() -> pd.DataFrame:
    companies = read_sql("companies")

    screener = build_screener_report()
    peer = build_peer_report()

    summary = companies.copy()

    if not screener.empty:
        screener_columns = [
            column
            for column in [
                "company_id",
                "year",
                "roe_pct",
                "roce_pct",
                "opm_pct",
                "cfo_to_sales_pct",
                "debt_to_equity",
                "interest_coverage",
                "kpi_pass_count",
                "screener_pass",
                "revenue_cagr_3y",
                "pat_cagr_3y",
            ]
            if column in screener.columns
        ]
        summary = summary.merge(
            screener[screener_columns],
            on="company_id",
            how="left",
        )

    if not peer.empty:
        peer_count = (
            peer.groupby("company_id", as_index=False)
            .agg(
                peer_group_count=("peer_group_name", "nunique"),
                benchmark_group_count=("is_benchmark", "sum"),
            )
        )

        summary = summary.merge(
            peer_count,
            on="company_id",
            how="left",
        )

    return summary


def write_report_log(
    summary: pd.DataFrame,
    screener: pd.DataFrame,
    peer: pd.DataFrame,
    market: pd.DataFrame,
    cagr: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK FINANCIAL ANALYTICS - DAY 20 REPORTING",
        "=" * 72,
        f"Companies in report: {len(summary)}",
        f"Screener rows: {len(screener)}",
        f"Peer summary rows: {len(peer)}",
        f"Market summary rows: {len(market)}",
        f"CAGR summary rows: {len(cagr)}",
        "",
        "Report files:",
        f"- {REPORT_CSV.name}",
        f"- {SCREENER_CSV.name}",
        f"- {PEER_CSV.name}",
        f"- {MARKET_CSV.name}",
        f"- {CAGR_CSV.name}",
    ]

    REPORT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("=" * 72)
    print("BLUESTOCK — DAY 20 REPORTING LAYER")
    print("=" * 72)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = build_company_summary()
    screener = build_screener_report()
    peer = build_peer_report()
    market = build_market_report()
    cagr = build_cagr_report()

    summary.to_csv(REPORT_CSV, index=False)
    screener.to_csv(SCREENER_CSV, index=False)
    peer.to_csv(PEER_CSV, index=False)
    market.to_csv(MARKET_CSV, index=False)
    cagr.to_csv(CAGR_CSV, index=False)

    write_report_log(summary, screener, peer, market, cagr)

    print(f"Companies        : {len(summary)}")
    print(f"Screener rows    : {len(screener)}")
    print(f"Peer rows        : {len(peer)}")
    print(f"Market rows      : {len(market)}")
    print(f"CAGR rows        : {len(cagr)}")
    print()
    print(f"Main report      : {REPORT_CSV}")
    print(f"Report log       : {REPORT_LOG}")


if __name__ == "__main__":
    main()
