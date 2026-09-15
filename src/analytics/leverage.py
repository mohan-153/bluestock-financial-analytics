"""
Bluestock Financial Analytics
Sprint 2 - Day 09
Leverage & Efficiency Engine

Calculates:
    - Debt-to-Equity (D/E)
    - High Leverage flag
    - Interest Coverage Ratio (ICR)
    - Debt Free / No Interest label
    - Net Debt (when a true cash balance is available)
    - Asset Turnover

Important:
    The available core cash-flow source contains CFO/CFI/CFF and net cash flow,
    but does not contain a cash-and-equivalents balance. Therefore this module
    does NOT incorrectly treat CFO as cash. Net debt is left as None unless a
    true cash balance column is supplied.
"""

from __future__ import annotations

from pathlib import Path
import math
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
EDGE_LOG = OUTPUT_DIR / "leverage_edge_cases.log"


def _number(value) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def debt_to_equity(borrowings, equity_capital, reserves) -> Optional[float]:
    """D/E = borrowings / (equity capital + reserves)."""
    borrowings = _number(borrowings)
    equity_capital = _number(equity_capital)
    reserves = _number(reserves)

    if any(v is None for v in (borrowings, equity_capital, reserves)):
        return None

    equity = equity_capital + reserves
    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(de_ratio, is_financials=False) -> bool:
    """High leverage when D/E > 2.0; Financials are excluded from the flag."""
    if is_financials:
        return False

    de_ratio = _number(de_ratio)
    return de_ratio is not None and de_ratio > 2.0


def interest_coverage_ratio(
    operating_profit,
    depreciation,
    interest,
) -> Optional[float]:
    """ICR = EBIT / interest, where EBIT = operating profit - depreciation."""
    operating_profit = _number(operating_profit)
    depreciation = _number(depreciation)
    interest = _number(interest)

    if any(v is None for v in (operating_profit, depreciation, interest)):
        return None

    if interest <= 0:
        return None

    ebit = operating_profit - depreciation
    return ebit / interest


def interest_status(interest) -> str:
    """Classify zero-interest rows as Debt Free / No Interest."""
    interest = _number(interest)

    if interest == 0:
        return "Debt Free / No Interest"
    if interest is None:
        return "Unknown"
    if interest < 0:
        return "Invalid Negative Interest"
    return "Interest Bearing"


def net_debt(borrowings, cash_balance=None) -> Optional[float]:
    """
    Net Debt = borrowings - cash balance.

    A true cash balance is required. The core source does not provide one,
    so cash_balance=None correctly returns None instead of using CFO.
    """
    borrowings = _number(borrowings)
    cash_balance = _number(cash_balance)

    if borrowings is None or cash_balance is None:
        return None

    return borrowings - cash_balance


def asset_turnover(sales, total_assets) -> Optional[float]:
    """Asset Turnover = Sales / Total Assets."""
    sales = _number(sales)
    total_assets = _number(total_assets)

    if sales is None or total_assets is None or total_assets <= 0:
        return None

    return sales / total_assets


def _is_financial_company(company_id: str, sectors: pd.DataFrame) -> bool:
    """Identify Financials using sector/sub-sector text."""
    row = sectors[
        sectors["company_id"].astype(str).str.strip().str.upper() == company_id
    ]

    if row.empty:
        return False

    text = " ".join(
        row.iloc[0][
            [c for c in ["broad_sector", "sub_sector"] if c in row.columns]
        ].fillna("").astype(str).tolist()
    ).lower()

    keywords = (
        "financial",
        "bank",
        "insurance",
        "nbfc",
        "finance",
        "lending",
    )
    return any(keyword in text for keyword in keywords)


def calculate_leverage_metrics(
    profitandloss: pd.DataFrame,
    balancesheet: pd.DataFrame,
    sectors: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate Day-09 leverage and efficiency metrics."""
    required_pnl = [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "depreciation",
        "interest",
    ]
    required_bs = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_assets",
    ]

    missing_pnl = [c for c in required_pnl if c not in profitandloss.columns]
    missing_bs = [c for c in required_bs if c not in balancesheet.columns]

    if missing_pnl:
        raise ValueError(f"profitandloss missing columns: {missing_pnl}")
    if missing_bs:
        raise ValueError(f"balancesheet missing columns: {missing_bs}")

    pnl = profitandloss[required_pnl].copy()
    bs = balancesheet[required_bs].copy()

    for df in (pnl, bs):
        df["company_id"] = (
            df["company_id"].astype(str).str.strip().str.upper()
        )

    bs = bs.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = pnl.merge(
        bs,
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    )

    result["de_ratio"] = result.apply(
        lambda r: debt_to_equity(
            r["borrowings"],
            r["equity_capital"],
            r["reserves"],
        ),
        axis=1,
    )

    result["is_financials"] = result["company_id"].apply(
        lambda cid: _is_financial_company(cid, sectors)
    )

    result["high_leverage_flag"] = result.apply(
        lambda r: high_leverage_flag(
            r["de_ratio"],
            bool(r["is_financials"]),
        ),
        axis=1,
    )

    result["icr"] = result.apply(
        lambda r: interest_coverage_ratio(
            r["operating_profit"],
            r["depreciation"],
            r["interest"],
        ),
        axis=1,
    )

    result["interest_status"] = result["interest"].apply(interest_status)

    result["icr_warning"] = result.apply(
        lambda r: (
            False
            if r["interest_status"] != "Interest Bearing"
            else r["icr"] is not None and r["icr"] < 1.5
        ),
        axis=1,
    )

    # No true cash-balance field exists in the core BS/CF inputs.
    result["net_debt_cr"] = result.apply(
        lambda r: net_debt(r["borrowings"], None),
        axis=1,
    )

    result["asset_turnover"] = result.apply(
        lambda r: asset_turnover(
            r["sales"],
            r["total_assets"],
        ),
        axis=1,
    )

    return result


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK LEVERAGE & EFFICIENCY - DAY 09 EDGE CASE LOG",
        "=" * 65,
        f"Rows calculated: {len(result)}",
        f"D/E unavailable: {int(result['de_ratio'].isna().sum())}",
        f"High leverage flags: {int(result['high_leverage_flag'].sum())}",
        f"Debt Free / No Interest: {int((result['interest_status'] == 'Debt Free / No Interest').sum())}",
        f"ICR unavailable: {int(result['icr'].isna().sum())}",
        f"ICR warnings: {int(result['icr_warning'].sum())}",
        f"Net debt unavailable: {int(result['net_debt_cr'].isna().sum())}",
        f"Asset turnover unavailable: {int(result['asset_turnover'].isna().sum())}",
    ]

    EDGE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 09 LEVERAGE & EFFICIENCY ENGINE")
    print("=" * 70)

    data = load_all_data()

    result = calculate_leverage_metrics(
        data["profitandloss"],
        data["balancesheet"],
        data["sectors"],
    )

    write_edge_log(result)

    print(f"Rows calculated       : {len(result)}")
    print(f"High leverage flags   : {int(result['high_leverage_flag'].sum())}")
    print(
        "Debt Free / No Interest: "
        f"{int((result['interest_status'] == 'Debt Free / No Interest').sum())}"
    )
    print(f"ICR warnings          : {int(result['icr_warning'].sum())}")
    print(f"Net debt available    : {int(result['net_debt_cr'].notna().sum())}")
    print(f"Edge log              : {EDGE_LOG}")
    print()
    print(
        result[
            [
                "company_id",
                "year",
                "de_ratio",
                "high_leverage_flag",
                "icr",
                "interest_status",
                "net_debt_cr",
                "asset_turnover",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
