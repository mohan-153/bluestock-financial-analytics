"""
Bluestock Financial Analytics
Sprint 2 - Day 12
Financial Ratios Table Population

Builds the final financial_ratios analytics dataset from the core financial
tables and writes it to output/financial_ratios_day12.csv.

Required analytical fields:
- Net Profit Margin
- Operating Profit Margin
- Return on Equity
- Debt to Equity
- Interest Coverage
- Asset Turnover
- Free Cash Flow
- Capex
- Earnings Per Share
- Book Value Per Share
- Dividend Payout Ratio
- Total Debt
- Cash From Operations

The raw source data is not overwritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import math

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "financial_ratios_day12.csv"
EDGE_LOG = OUTPUT_DIR / "financial_ratios_edge_cases.log"


def _num(value) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def safe_divide(numerator, denominator) -> Optional[float]:
    n = _num(numerator)
    d = _num(denominator)
    if n is None or d is None or d == 0:
        return None
    return n / d


def net_profit_margin(net_profit, sales) -> Optional[float]:
    value = safe_divide(net_profit, sales)
    return None if value is None else value * 100


def operating_profit_margin(operating_profit, sales) -> Optional[float]:
    value = safe_divide(operating_profit, sales)
    return None if value is None else value * 100


def return_on_equity(net_profit, equity_capital, reserves) -> Optional[float]:
    equity = None
    ec = _num(equity_capital)
    reserves_value = _num(reserves)
    if ec is not None and reserves_value is not None:
        equity = ec + reserves_value
    value = safe_divide(net_profit, equity)
    return None if value is None else value * 100


def debt_to_equity(borrowings, equity_capital, reserves) -> Optional[float]:
    equity = None
    ec = _num(equity_capital)
    reserves_value = _num(reserves)
    if ec is not None and reserves_value is not None:
        equity = ec + reserves_value
    return safe_divide(borrowings, equity)


def interest_coverage(operating_profit, depreciation, interest) -> Optional[float]:
    op = _num(operating_profit)
    dep = _num(depreciation)
    interest_value = _num(interest)

    if op is None or dep is None or interest_value is None:
        return None

    if interest_value <= 0:
        return None

    return (op - dep) / interest_value


def asset_turnover(sales, total_assets) -> Optional[float]:
    return safe_divide(sales, total_assets)


def free_cash_flow(cfo, cfi) -> Optional[float]:
    cfo_value = _num(cfo)
    cfi_value = _num(cfi)
    if cfo_value is None or cfi_value is None:
        return None
    return cfo_value + cfi_value


def book_value_per_share(equity_capital, reserves) -> Optional[float]:
    """
    The source does not provide share count, so this function does not invent
    one. It returns book value only when a valid share-count field is supplied.
    """
    return None


def prepare_data(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pl = data["profitandloss"].copy()
    bs = data["balancesheet"].copy()
    cf = data["cashflow"].copy()

    pl["company_id"] = pl["company_id"].astype(str).str.strip().str.upper()
    bs["company_id"] = bs["company_id"].astype(str).str.strip().str.upper()
    cf["company_id"] = cf["company_id"].astype(str).str.strip().str.upper()

    pl = pl[
        [
            "company_id", "year", "sales", "operating_profit", "depreciation",
            "interest", "net_profit", "eps", "dividend_payout"
        ]
    ].copy()

    bs = bs[
        [
            "company_id", "year", "equity_capital", "reserves", "borrowings",
            "total_assets"
        ]
    ].copy()

    cf = cf[
        [
            "company_id", "year", "operating_activity",
            "investing_activity"
        ]
    ].copy()

    pl = pl.merge(
        bs,
        on=["company_id", "year"],
        how="left",
    )

    pl = pl.merge(
        cf,
        on=["company_id", "year"],
        how="left",
    )

    return pl


def calculate_financial_ratios(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = prepare_data(data)
    rows = []

    for _, row in df.iterrows():
        cfo = _num(row["operating_activity"])
        cfi = _num(row["investing_activity"])

        rows.append(
            {
                "company_id": row["company_id"],
                "year": row["year"],
                "net_profit_margin_pct": net_profit_margin(
                    row["net_profit"], row["sales"]
                ),
                "operating_profit_margin_pct": operating_profit_margin(
                    row["operating_profit"], row["sales"]
                ),
                "return_on_equity_pct": return_on_equity(
                    row["net_profit"],
                    row["equity_capital"],
                    row["reserves"],
                ),
                "debt_to_equity": debt_to_equity(
                    row["borrowings"],
                    row["equity_capital"],
                    row["reserves"],
                ),
                "interest_coverage": interest_coverage(
                    row["operating_profit"],
                    row["depreciation"],
                    row["interest"],
                ),
                "asset_turnover": asset_turnover(
                    row["sales"],
                    row["total_assets"],
                ),
                "free_cash_flow_cr": free_cash_flow(cfo, cfi),
                "capex_cr": (
                    None if cfi is None else abs(cfi)
                ),
                "earnings_per_share": _num(row["eps"]),
                "book_value_per_share": book_value_per_share(
                    row["equity_capital"],
                    row["reserves"],
                ),
                "dividend_payout_ratio_pct": _num(row["dividend_payout"]),
                "total_debt_cr": _num(row["borrowings"]),
                "cash_from_operations_cr": cfo,
            }
        )

    return pd.DataFrame(rows)


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK FINANCIAL RATIOS - DAY 12 EDGE CASE LOG",
        "=" * 70,
        f"Rows generated: {len(result)}",
        "",
        "Missing values by field:",
    ]

    for column in result.columns:
        missing = int(result[column].isna().sum())
        if missing:
            lines.append(f"{column}: {missing}")

    EDGE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 12 FINANCIAL RATIOS")
    print("=" * 70)

    data = load_all_data()
    result = calculate_financial_ratios(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows generated : {len(result)}")
    print(f"Output         : {OUTPUT_CSV}")
    print(f"Edge log       : {EDGE_LOG}")
    print()
    print(result.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
