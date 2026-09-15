"""
Bluestock Financial Analytics
Sprint 2 - Day 11
Cash Flow Analytics

Calculates:
- CFO (Operating Cash Flow)
- CFI (Investing Cash Flow)
- CFF (Financing Cash Flow)
- Net Cash Flow
- FCF (Free Cash Flow = CFO + CFI)
- CFO / PAT
- CFO / Sales
- Cash-flow consistency and edge-case flags

The raw source columns are:
    operating_activity
    investing_activity
    financing_activity
    net_cash_flow

No raw source values are overwritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import math

import pandas as pd

from src.etl.loader import load_all_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "cashflow_analytics.csv"
EDGE_LOG = OUTPUT_DIR / "cashflow_edge_cases.log"


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


def calculate_fcf(cfo, cfi) -> Optional[float]:
    """Free Cash Flow = CFO + CFI."""
    cfo_value = _number(cfo)
    cfi_value = _number(cfi)

    if cfo_value is None or cfi_value is None:
        return None

    return cfo_value + cfi_value


def calculate_cashflow_reconciliation(cfo, cfi, cff, reported_ncf):
    """
    Check:
        Net Cash Flow ~= CFO + CFI + CFF

    Returns:
        (difference, status)
    """
    values = [_number(cfo), _number(cfi), _number(cff), _number(reported_ncf)]

    if any(value is None for value in values):
        return None, "INSUFFICIENT"

    cfo_value, cfi_value, cff_value, ncf_value = values
    calculated = cfo_value + cfi_value + cff_value
    difference = ncf_value - calculated

    status = "OK" if abs(difference) <= 10 else "MISMATCH"
    return difference, status


def calculate_cfo_pat(cfo, pat) -> Optional[float]:
    """CFO / PAT ratio. Returns None when PAT is zero/missing."""
    cfo_value = _number(cfo)
    pat_value = _number(pat)

    if cfo_value is None or pat_value is None or pat_value == 0:
        return None

    return cfo_value / pat_value


def calculate_cfo_sales(cfo, sales) -> Optional[float]:
    """CFO / Sales ratio."""
    cfo_value = _number(cfo)
    sales_value = _number(sales)

    if cfo_value is None or sales_value is None or sales_value == 0:
        return None

    return cfo_value / sales_value * 100


def prepare_cashflow_data(
    cashflow: pd.DataFrame,
    profitandloss: pd.DataFrame,
) -> pd.DataFrame:
    """Join cash flow data with PAT and sales."""
    required_cf = [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    missing_cf = [
        column for column in required_cf
        if column not in cashflow.columns
    ]
    if missing_cf:
        raise ValueError(f"cashflow missing columns: {missing_cf}")

    required_pl = [
        "company_id",
        "year",
        "sales",
        "net_profit",
    ]

    missing_pl = [
        column for column in required_pl
        if column not in profitandloss.columns
    ]
    if missing_pl:
        raise ValueError(f"profitandloss missing columns: {missing_pl}")

    cf = cashflow[required_cf].copy()
    pl = profitandloss[required_pl].copy()

    for df in (cf, pl):
        df["company_id"] = (
            df["company_id"].astype(str).str.strip().str.upper()
        )

    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]:
        cf[column] = pd.to_numeric(cf[column], errors="coerce")

    for column in ["sales", "net_profit"]:
        pl[column] = pd.to_numeric(pl[column], errors="coerce")

    # P&L and cash flow are annual datasets, so join on company/year.
    df = cf.merge(
        pl,
        on=["company_id", "year"],
        how="left",
        suffixes=("", "_pl"),
    )

    return df


def calculate_cashflow_table(
    cashflow: pd.DataFrame,
    profitandloss: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate Day-11 cash-flow analytics."""
    df = prepare_cashflow_data(cashflow, profitandloss)

    rows = []

    for _, row in df.iterrows():
        cfo = _number(row["operating_activity"])
        cfi = _number(row["investing_activity"])
        cff = _number(row["financing_activity"])
        reported_ncf = _number(row["net_cash_flow"])
        pat = _number(row["net_profit"])
        sales = _number(row["sales"])

        fcf = calculate_fcf(cfo, cfi)
        difference, reconciliation = calculate_cashflow_reconciliation(
            cfo, cfi, cff, reported_ncf
        )

        cfo_pat = calculate_cfo_pat(cfo, pat)
        cfo_sales = calculate_cfo_sales(cfo, sales)

        if cfo is None:
            cash_quality = "MISSING_CFO"
        elif cfo > 0 and fcf is not None and fcf > 0:
            cash_quality = "STRONG_POSITIVE_FCF"
        elif cfo > 0:
            cash_quality = "POSITIVE_CFO"
        elif cfo < 0:
            cash_quality = "NEGATIVE_CFO"
        else:
            cash_quality = "ZERO_CFO"

        rows.append(
            {
                "company_id": row["company_id"],
                "year": row["year"],
                "cfo_cr": cfo,
                "cfi_cr": cfi,
                "cff_cr": cff,
                "reported_net_cash_flow_cr": reported_ncf,
                "calculated_net_cash_flow_cr": (
                    None
                    if any(v is None for v in [cfo, cfi, cff])
                    else cfo + cfi + cff
                ),
                "net_cash_flow_difference_cr": difference,
                "reconciliation_status": reconciliation,
                "free_cash_flow_cr": fcf,
                "pat_cr": pat,
                "sales_cr": sales,
                "cfo_to_pat": cfo_pat,
                "cfo_to_sales_pct": cfo_sales,
                "cash_quality": cash_quality,
            }
        )

    return pd.DataFrame(rows)


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK CASH FLOW ANALYTICS - DAY 11 EDGE CASE LOG",
        "=" * 70,
        f"Rows generated: {len(result)}",
        "",
        "Reconciliation status:",
    ]

    reconciliation_counts = (
        result["reconciliation_status"]
        .value_counts(dropna=False)
        .sort_index()
    )

    for status, count in reconciliation_counts.items():
        lines.append(f"{status}: {count}")

    lines.extend(
        [
            "",
            "Cash quality:",
        ]
    )

    quality_counts = (
        result["cash_quality"]
        .value_counts(dropna=False)
        .sort_index()
    )

    for status, count in quality_counts.items():
        lines.append(f"{status}: {count}")

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 11 CASH FLOW ANALYTICS")
    print("=" * 70)

    data = load_all_data()

    result = calculate_cashflow_table(
        data["cashflow"],
        data["profitandloss"],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows calculated : {len(result)}")
    print(f"Output          : {OUTPUT_CSV}")
    print(f"Edge log        : {EDGE_LOG}")
    print()

    print(
        result[
            [
                "company_id",
                "year",
                "cfo_cr",
                "cfi_cr",
                "cff_cr",
                "free_cash_flow_cr",
                "cfo_to_pat",
                "cfo_to_sales_pct",
                "reconciliation_status",
                "cash_quality",
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()
