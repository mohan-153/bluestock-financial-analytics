"""
Bluestock Financial Analytics
Sprint 3 - Day 16
Stock & Market Analytics

Calculates annual market/price analytics from the existing stock_prices and
market_cap datasets.

Metrics:
- annual return
- annual high / low
- average close
- annualized volatility from daily returns
- maximum drawdown
- latest close
- market-cap / valuation fields from market_cap

Prices are treated as SIMULATED where the project source is simulated.
No raw source values are modified.
"""

from __future__ import annotations

from pathlib import Path
import math
from typing import Optional

import numpy as np
import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "stock_market_analytics_day16.csv"
EDGE_LOG = OUTPUT_DIR / "stock_market_analytics_day16.log"


def _number(value) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def calculate_annual_return(first_close, last_close) -> Optional[float]:
    first = _number(first_close)
    last = _number(last_close)

    if first is None or last is None or first <= 0:
        return None

    return (last / first - 1.0) * 100.0


def calculate_daily_returns(close_prices: pd.Series) -> pd.Series:
    prices = pd.to_numeric(close_prices, errors="coerce")
    prices = prices.replace([np.inf, -np.inf], np.nan)
    return prices.pct_change().dropna()


def calculate_annualized_volatility(close_prices: pd.Series) -> Optional[float]:
    returns = calculate_daily_returns(close_prices)

    if len(returns) < 2:
        return None

    return float(returns.std(ddof=1) * math.sqrt(252) * 100.0)


def calculate_max_drawdown(close_prices: pd.Series) -> Optional[float]:
    prices = pd.to_numeric(close_prices, errors="coerce")
    prices = prices.replace([np.inf, -np.inf], np.nan).dropna()

    if prices.empty:
        return None

    running_max = prices.cummax()
    drawdown = prices / running_max - 1.0

    return float(drawdown.min() * 100.0)


def prepare_prices(stock_prices: pd.DataFrame) -> pd.DataFrame:
    required = [
        "company_id",
        "date",
        "close_price",
    ]

    missing = [c for c in required if c not in stock_prices.columns]
    if missing:
        raise ValueError(f"stock_prices missing columns: {missing}")

    df = stock_prices[required].copy()

    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close_price"] = pd.to_numeric(
        df["close_price"], errors="coerce"
    )

    df = df.dropna(subset=["company_id", "date", "close_price"])
    df = df[df["close_price"] > 0]

    return df.sort_values(["company_id", "date"])


def prepare_market_cap(market_cap: pd.DataFrame) -> pd.DataFrame:
    if market_cap is None or market_cap.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "year",
                "market_cap_crore",
                "enterprise_value_crore",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
            ]
        )

    df = market_cap.copy()
    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )

    return df


def calculate_stock_market_analytics(
    stock_prices: pd.DataFrame,
    market_cap: pd.DataFrame,
) -> pd.DataFrame:
    prices = prepare_prices(stock_prices)
    mc = prepare_market_cap(market_cap)

    rows = []

    for (company_id, year), group in prices.assign(
        calendar_year=prices["date"].dt.year
    ).groupby(["company_id", prices["date"].dt.year], sort=True):

        group = group.sort_values("date")
        closes = group["close_price"]

        first_close = float(closes.iloc[0])
        last_close = float(closes.iloc[-1])

        rows.append(
            {
                "company_id": company_id,
                "calendar_year": int(year),
                "price_start_date": group["date"].iloc[0].date().isoformat(),
                "price_end_date": group["date"].iloc[-1].date().isoformat(),
                "trading_days": int(len(group)),
                "first_close": first_close,
                "last_close": last_close,
                "annual_return_pct": calculate_annual_return(
                    first_close, last_close
                ),
                "annual_high": float(closes.max()),
                "annual_low": float(closes.min()),
                "average_close": float(closes.mean()),
                "annualized_volatility_pct": calculate_annualized_volatility(
                    closes
                ),
                "max_drawdown_pct": calculate_max_drawdown(closes),
                "price_data_status": "SIMULATED"
                if len(group) > 0
                else "MISSING",
            }
        )

    result = pd.DataFrame(rows)

    if not mc.empty and not result.empty:
        mc = mc.copy()

        if "year" in mc.columns:
            mc["year_num"] = pd.to_numeric(
                mc["year"], errors="coerce"
            )

            result["market_year"] = result["calendar_year"]

            result = result.merge(
                mc[
                    [
                        "company_id",
                        "year_num",
                        "market_cap_crore",
                        "enterprise_value_crore",
                        "pe_ratio",
                        "pb_ratio",
                        "ev_ebitda",
                        "dividend_yield_pct",
                    ]
                ],
                left_on=["company_id", "market_year"],
                right_on=["company_id", "year_num"],
                how="left",
            )

            result = result.drop(columns=["year_num", "market_year"])

    return result


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK STOCK & MARKET ANALYTICS - DAY 16",
        "=" * 70,
        f"Rows generated: {len(result)}",
        f"Companies: {result['company_id'].nunique() if not result.empty else 0}",
    ]

    if not result.empty:
        lines.extend(
            [
                "",
                "Price data status:",
            ]
        )

        for status, count in result["price_data_status"].value_counts().items():
            lines.append(f"{status}: {int(count)}")

        lines.extend(
            [
                "",
                "Rows with annualized volatility:",
                str(int(result["annualized_volatility_pct"].notna().sum())),
                "",
                "Rows with maximum drawdown:",
                str(int(result["max_drawdown_pct"].notna().sum())),
            ]
        )

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 16 STOCK + MARKET ANALYTICS")
    print("=" * 70)

    data = load_all_data()

    result = calculate_stock_market_analytics(
        data["stock_prices"],
        data["market_cap"],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows generated : {len(result)}")
    print(
        f"Companies      : "
        f"{result['company_id'].nunique() if not result.empty else 0}"
    )
    print(f"Output         : {OUTPUT_CSV}")
    print(f"Edge log       : {EDGE_LOG}")
    print()

    if not result.empty:
        print(
            result.head(15).to_string(index=False)
        )


if __name__ == "__main__":
    main()
