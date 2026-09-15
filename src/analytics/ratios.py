"""
Bluestock Financial Analytics
Sprint 2 - Day 08
Profitability Ratio Engine

Computes:
    - Net Profit Margin (NPM)
    - Operating Profit Margin (OPM)
    - EBIT Margin
    - Return on Equity (ROE)
    - Return on Capital Employed (ROCE)
    - Return on Assets (ROA)

Rules:
    - Monetary values are INR Crore.
    - Zero sales -> NPM/OPM/EBIT Margin = None.
    - Equity + reserves <= 0 -> ROE = None.
    - Capital employed <= 0 -> ROCE = None.
    - Zero total assets -> ROA = None.
    - Source opm_percentage is cross-checked but never overwritten.
"""

from __future__ import annotations

from pathlib import Path
import math
import sqlite3
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
EDGE_LOG = OUTPUT_DIR / "ratio_edge_cases.log"
OPM_CHECK = OUTPUT_DIR / "opm_cross_check.csv"


def _number(value) -> Optional[float]:
    """Convert a value to float; return None for missing/non-numeric values."""
    if pd.isna(value):
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value):
        return None

    return value


def _safe_divide(numerator, denominator) -> Optional[float]:
    """Return numerator / denominator, or None for invalid/zero denominator."""
    numerator = _number(numerator)
    denominator = _number(denominator)

    if numerator is None or denominator is None or denominator == 0:
        return None

    return numerator / denominator


def net_profit_margin(net_profit, sales) -> Optional[float]:
    """NPM = net_profit / sales * 100."""
    ratio = _safe_divide(net_profit, sales)
    return None if ratio is None else ratio * 100.0


def operating_profit_margin(operating_profit, sales) -> Optional[float]:
    """OPM = operating_profit / sales * 100."""
    ratio = _safe_divide(operating_profit, sales)
    return None if ratio is None else ratio * 100.0


def ebit_margin(operating_profit, depreciation, sales) -> Optional[float]:
    """
    EBIT Margin = (operating_profit - depreciation) / sales * 100.

    The project KPI reference defines EBIT as operating profit less
    depreciation.
    """
    operating_profit = _number(operating_profit)
    depreciation = _number(depreciation)
    sales = _number(sales)

    if operating_profit is None or depreciation is None:
        return None
    if sales is None or sales == 0:
        return None

    return ((operating_profit - depreciation) / sales) * 100.0


def return_on_equity(net_profit, equity_capital, reserves) -> Optional[float]:
    """
    ROE = net_profit / (equity_capital + reserves) * 100.

    Return None when equity + reserves <= 0.
    """
    net_profit = _number(net_profit)
    equity_capital = _number(equity_capital)
    reserves = _number(reserves)

    if net_profit is None or equity_capital is None or reserves is None:
        return None

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100.0


def return_on_capital(
    operating_profit,
    depreciation,
    equity_capital,
    reserves,
    borrowings,
) -> Optional[float]:
    """
    ROCE = EBIT / (equity + reserves + borrowings) * 100.

    EBIT = operating_profit - depreciation.
    """
    operating_profit = _number(operating_profit)
    depreciation = _number(depreciation)
    equity_capital = _number(equity_capital)
    reserves = _number(reserves)
    borrowings = _number(borrowings)

    values = [
        operating_profit,
        depreciation,
        equity_capital,
        reserves,
        borrowings,
    ]

    if any(value is None for value in values):
        return None

    capital_employed = equity_capital + reserves + borrowings

    if capital_employed <= 0:
        return None

    ebit = operating_profit - depreciation
    return (ebit / capital_employed) * 100.0


def return_on_assets(net_profit, total_assets) -> Optional[float]:
    """ROA = net_profit / total_assets * 100."""
    ratio = _safe_divide(net_profit, total_assets)
    return None if ratio is None else ratio * 100.0


def calculate_profitability_ratios(
    profitandloss: pd.DataFrame,
    balancesheet: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate profitability ratios by company and financial year.

    P&L and balance-sheet rows are joined on (company_id, year).
    A left join is used so every P&L observation is retained.
    """
    pnl = profitandloss.copy()
    bs = balancesheet.copy()

    pnl["company_id"] = (
        pnl["company_id"].astype(str).str.strip().str.upper()
    )
    bs["company_id"] = (
        bs["company_id"].astype(str).str.strip().str.upper()
    )

    bs_cols = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_assets",
    ]

    missing_bs = [col for col in bs_cols if col not in bs.columns]
    if missing_bs:
        raise ValueError(
            f"balancesheet is missing required columns: {missing_bs}"
        )

    required_pnl = [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "depreciation",
        "net_profit",
        "opm_percentage",
    ]

    missing_pnl = [col for col in required_pnl if col not in pnl.columns]
    if missing_pnl:
        raise ValueError(
            f"profitandloss is missing required columns: {missing_pnl}"
        )

    bs = bs[bs_cols].drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = pnl[
        [
            "company_id",
            "year",
            "sales",
            "operating_profit",
            "depreciation",
            "net_profit",
            "opm_percentage",
        ]
    ].merge(
        bs,
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    )

    result["npm_pct"] = result.apply(
        lambda row: net_profit_margin(
            row["net_profit"],
            row["sales"],
        ),
        axis=1,
    )

    result["opm_pct"] = result.apply(
        lambda row: operating_profit_margin(
            row["operating_profit"],
            row["sales"],
        ),
        axis=1,
    )

    result["ebit_margin_pct"] = result.apply(
        lambda row: ebit_margin(
            row["operating_profit"],
            row["depreciation"],
            row["sales"],
        ),
        axis=1,
    )

    result["roe_pct"] = result.apply(
        lambda row: return_on_equity(
            row["net_profit"],
            row["equity_capital"],
            row["reserves"],
        ),
        axis=1,
    )

    result["roce_pct"] = result.apply(
        lambda row: return_on_capital(
            row["operating_profit"],
            row["depreciation"],
            row["equity_capital"],
            row["reserves"],
            row["borrowings"],
        ),
        axis=1,
    )

    result["roa_pct"] = result.apply(
        lambda row: return_on_assets(
            row["net_profit"],
            row["total_assets"],
        ),
        axis=1,
    )

    result["opm_source_pct"] = pd.to_numeric(
        result["opm_percentage"],
        errors="coerce",
    )

    result["opm_difference_pct_points"] = (
        result["opm_source_pct"] - result["opm_pct"]
    ).abs()

    result["opm_crosscheck_status"] = "PASS"
    result.loc[
        result["opm_source_pct"].isna()
        | result["opm_pct"].isna(),
        "opm_crosscheck_status",
    ] = "NOT_CHECKED"

    result.loc[
        result["opm_difference_pct_points"] > 1.0,
        "opm_crosscheck_status",
    ] = "MISMATCH"

    return result


def write_edge_log(ratios: pd.DataFrame) -> None:
    """Write division-by-zero and negative-equity edge-case observations."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK RATIO ENGINE - DAY 08 EDGE CASE LOG",
        "=" * 60,
    ]

    zero_sales = int(
        pd.to_numeric(ratios["sales"], errors="coerce").eq(0).sum()
    )

    negative_equity = int(
        (
            pd.to_numeric(ratios["equity_capital"], errors="coerce")
            + pd.to_numeric(ratios["reserves"], errors="coerce")
            <= 0
        ).sum()
    )

    zero_assets = int(
        pd.to_numeric(ratios["total_assets"], errors="coerce").eq(0).sum()
    )

    lines.append(f"Zero-sales rows: {zero_sales}")
    lines.append(f"Non-positive equity rows: {negative_equity}")
    lines.append(f"Zero-total-assets rows: {zero_assets}")
    lines.append("")

    for _, row in ratios.iterrows():
        messages = []

        sales = _number(row["sales"])
        equity = _number(row["equity_capital"])
        reserves = _number(row["reserves"])
        assets = _number(row["total_assets"])

        if sales == 0:
            messages.append("sales=0; profitability margins set to None")

        if (
            equity is not None
            and reserves is not None
            and equity + reserves <= 0
        ):
            messages.append("equity+reserves<=0; ROE set to None")

        if assets == 0:
            messages.append("total_assets=0; ROA set to None")

        if messages:
            lines.append(
                f"{row['company_id']} | {row['year']} | "
                + "; ".join(messages)
            )

    EDGE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_opm_crosscheck(ratios: pd.DataFrame) -> None:
    """Export source-vs-computed OPM checks for auditability."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "company_id",
        "year",
        "opm_source_pct",
        "opm_pct",
        "opm_difference_pct_points",
        "opm_crosscheck_status",
    ]

    ratios[columns].to_csv(OPM_CHECK, index=False)


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 08 PROFITABILITY RATIO ENGINE")
    print("=" * 70)

    data = load_all_data()

    ratios = calculate_profitability_ratios(
        data["profitandloss"],
        data["balancesheet"],
    )

    write_edge_log(ratios)
    write_opm_crosscheck(ratios)

    print(f"Rows calculated : {len(ratios)}")
    print(
        "Columns         : "
        "npm_pct, opm_pct, ebit_margin_pct, roe_pct, roce_pct, roa_pct"
    )
    print(f"OPM mismatches  : {(ratios['opm_crosscheck_status'] == 'MISMATCH').sum()}")
    print(f"Edge log        : {EDGE_LOG}")
    print(f"OPM cross-check : {OPM_CHECK}")

    print()
    print("Sample:")
    print(
        ratios[
            [
                "company_id",
                "year",
                "npm_pct",
                "opm_pct",
                "roe_pct",
                "roce_pct",
                "roa_pct",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
