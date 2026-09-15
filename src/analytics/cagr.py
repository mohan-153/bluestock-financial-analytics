"""
Bluestock Financial Analytics
Sprint 2 - Day 10
CAGR Engine

Calculates 3Y / 5Y / 10Y CAGR for:
    - Revenue (Sales)
    - PAT (Net Profit)
    - EPS

Edge classifications:
    Positive -> Positive : CAGR
    Positive -> Negative : DECLINE_TO_LOSS
    Negative -> Positive : TURNAROUND
    Negative -> Negative : BOTH_NEGATIVE
    Zero base            : ZERO_BASE
    Missing history      : INSUFFICIENT

Important:
    CAGR is calculated using the financial year sequence and the requested
    number of years. A 3Y CAGR requires a starting observation 3 years before
    the ending observation, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
from typing import Optional

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
EDGE_LOG = OUTPUT_DIR / "cagr_edge_cases.log"
OUTPUT_CSV = OUTPUT_DIR / "cagr_results.csv"

HORIZONS = (3, 5, 10)


@dataclass(frozen=True)
class CAGRResult:
    value: Optional[float]
    status: str


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


def calculate_cagr(start_value, end_value, years: int) -> CAGRResult:
    """
    Calculate CAGR with explicit sign/zero edge-case handling.

    For Positive -> Positive:
        ((end / start) ** (1 / years) - 1) * 100

    For all other sign combinations, return None with a classification.
    """
    start = _number(start_value)
    end = _number(end_value)

    if years <= 0:
        raise ValueError("years must be positive")

    if start is None or end is None:
        return CAGRResult(None, "INSUFFICIENT")

    if start == 0:
        return CAGRResult(None, "ZERO_BASE")

    if start > 0 and end > 0:
        value = ((end / start) ** (1.0 / years) - 1.0) * 100.0
        return CAGRResult(value, "CAGR")

    if start > 0 and end < 0:
        return CAGRResult(None, "DECLINE_TO_LOSS")

    if start < 0 and end > 0:
        return CAGRResult(None, "TURNAROUND")

    if start < 0 and end < 0:
        return CAGRResult(None, "BOTH_NEGATIVE")

    return CAGRResult(None, "INSUFFICIENT")


def _year_number(year_value) -> Optional[int]:
    """Extract fiscal year from values such as 2024-03 or 2024."""
    if pd.isna(year_value):
        return None

    match = pd.Series([str(year_value)]).str.extract(
        r"^(\d{4})",
        expand=False,
    ).iloc[0]

    if pd.isna(match):
        return None

    return int(match)


def prepare_annual_data(profitandloss: pd.DataFrame) -> pd.DataFrame:
    """Prepare annual P&L data for CAGR calculations."""
    required = [
        "company_id",
        "year",
        "sales",
        "net_profit",
        "eps",
    ]

    missing = [column for column in required if column not in profitandloss.columns]
    if missing:
        raise ValueError(f"profitandloss missing columns: {missing}")

    df = profitandloss[required].copy()

    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )

    df["fiscal_year"] = df["year"].apply(_year_number)

    for column in ["sales", "net_profit", "eps"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["company_id", "fiscal_year"])
    df["fiscal_year"] = df["fiscal_year"].astype(int)

    # One observation per company/fiscal year.
    df = df.sort_values(["company_id", "fiscal_year"])
    df = df.drop_duplicates(
        subset=["company_id", "fiscal_year"],
        keep="last",
    )

    return df


def _find_start_row(group: pd.DataFrame, end_year: int, horizon: int):
    """
    Find the observation exactly horizon fiscal years before end_year.

    This avoids treating a missing year as if it were a valid CAGR period.
    """
    start_year = end_year - horizon

    matches = group[group["fiscal_year"] == start_year]

    if matches.empty:
        return None

    return matches.iloc[0]


def calculate_cagr_table(profitandloss: pd.DataFrame) -> pd.DataFrame:
    """Return one row per company/end-year/horizon/metric."""
    annual = prepare_annual_data(profitandloss)

    rows = []

    for company_id, group in annual.groupby("company_id", sort=True):

        group = group.sort_values("fiscal_year")

        for _, end_row in group.iterrows():

            end_year = int(end_row["fiscal_year"])

            for horizon in HORIZONS:

                start_row = _find_start_row(
                    group,
                    end_year,
                    horizon,
                )

                for metric, column in (
                    ("revenue", "sales"),
                    ("pat", "net_profit"),
                    ("eps", "eps"),
                ):

                    if start_row is None:
                        result = CAGRResult(None, "INSUFFICIENT")
                        start_year = end_year - horizon
                    else:
                        start_year = int(start_row["fiscal_year"])
                        result = calculate_cagr(
                            start_row[column],
                            end_row[column],
                            horizon,
                        )

                    rows.append(
                        {
                            "company_id": company_id,
                            "end_year": end_year,
                            "start_year": start_year,
                            "horizon_years": horizon,
                            "metric": metric,
                            "start_value": (
                                None
                                if start_row is None
                                else start_row[column]
                            ),
                            "end_value": end_row[column],
                            "cagr_pct": result.value,
                            "status": result.status,
                        }
                    )

    return pd.DataFrame(rows)


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    counts = (
        result.groupby(["metric", "horizon_years", "status"])
        .size()
        .reset_index(name="rows")
    )

    lines = [
        "BLUESTOCK CAGR ENGINE - DAY 10 EDGE CASE LOG",
        "=" * 65,
        f"Rows generated: {len(result)}",
        "",
        "Status counts:",
    ]

    for _, row in counts.iterrows():
        lines.append(
            f"{row['metric']} | "
            f"{int(row['horizon_years'])}Y | "
            f"{row['status']} | "
            f"{int(row['rows'])}"
        )

    EDGE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 10 CAGR ENGINE")
    print("=" * 70)

    data = load_all_data()

    result = calculate_cagr_table(data["profitandloss"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows generated : {len(result)}")
    print(f"Output         : {OUTPUT_CSV}")
    print(f"Edge log       : {EDGE_LOG}")
    print()
    print(
        result[
            [
                "company_id",
                "end_year",
                "start_year",
                "horizon_years",
                "metric",
                "cagr_pct",
                "status",
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()
