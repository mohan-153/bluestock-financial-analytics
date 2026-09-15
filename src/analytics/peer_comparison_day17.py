"""
Bluestock Financial Analytics
Sprint 3 - Day 17
Peer Comparison

Builds peer-level KPI comparisons using the existing peer_groups and
financial analytics.

Outputs:
- peer group
- company KPI values
- peer rank
- peer percentile
- peer group size

Ranking is descending for "higher is better" metrics and ascending for
Debt-to-Equity. Financial carve-out eligibility is respected.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.etl.loader import load_all_data
from src.analytics.screener_day14 import build_screener_preview


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_CSV = OUTPUT_DIR / "peer_comparison_day17.csv"
EDGE_LOG = OUTPUT_DIR / "peer_comparison_day17.log"


HIGHER_IS_BETTER = {
    "return_on_equity_pct": True,
    "roce_pct": True,
    "operating_profit_margin_pct": True,
    "interest_coverage": True,
    "asset_turnover": True,
    "free_cash_flow_cr": True,
    "cfo_to_sales_pct": True,
}

LOWER_IS_BETTER = {
    "debt_to_equity": False,
}


def prepare_peer_groups(peer_groups: pd.DataFrame) -> pd.DataFrame:
    required = [
        "peer_group_name",
        "company_id",
        "is_benchmark",
    ]

    missing = [c for c in required if c not in peer_groups.columns]
    if missing:
        raise ValueError(f"peer_groups missing columns: {missing}")

    df = peer_groups[required].copy()

    df["company_id"] = (
        df["company_id"].astype(str).str.strip().str.upper()
    )
    df["peer_group_name"] = (
        df["peer_group_name"].astype(str).str.strip()
    )

    df["is_benchmark"] = (
        df["is_benchmark"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["1", "true", "yes", "y"])
    )

    return df


def calculate_peer_rank(
    values: pd.Series,
    higher_is_better: bool = True,
) -> pd.Series:
    """
    Dense ranking among non-null values.
    """
    numeric = pd.to_numeric(values, errors="coerce")

    if higher_is_better:
        return numeric.rank(
            ascending=False,
            method="min",
            na_option="keep",
        )
    return numeric.rank(
        ascending=True,
        method="min",
        na_option="keep",
    )


def calculate_peer_percentile(
    values: pd.Series,
    higher_is_better: bool = True,
) -> pd.Series:
    """
    Percentile score from 0-100.

    Higher-is-better:
        best value approaches 100.
    Lower-is-better:
        lowest value approaches 100.
    """
    numeric = pd.to_numeric(values, errors="coerce")

    if numeric.notna().sum() <= 1:
        return numeric.where(numeric.notna(), None).apply(
            lambda x: 100.0 if pd.notna(x) else None
        )

    if higher_is_better:
        return numeric.rank(
            pct=True,
            method="average",
            na_option="keep",
        ) * 100.0

    return (
        1.0
        - numeric.rank(
            pct=True,
            method="average",
            na_option="keep",
        )
        + (1.0 / numeric.notna().sum())
    ) * 100.0


def add_peer_metric_ranking(
    df: pd.DataFrame,
    metric: str,
    higher_is_better: bool,
) -> pd.DataFrame:
    rank_column = f"{metric}_peer_rank"
    percentile_column = f"{metric}_peer_percentile"

    df[rank_column] = (
        df.groupby(["peer_group_name", "year"], dropna=False)[metric]
        .transform(
            lambda values: calculate_peer_rank(
                values,
                higher_is_better,
            )
        )
    )

    df[percentile_column] = (
        df.groupby(["peer_group_name", "year"], dropna=False)[metric]
        .transform(
            lambda values: calculate_peer_percentile(
                values,
                higher_is_better,
            )
        )
    )

    return df


def build_peer_comparison(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    preview = build_screener_preview(data).copy()
    peers = prepare_peer_groups(data["peer_groups"])

    # One company can occur in multiple peer groups.
    df = preview.merge(
        peers,
        on="company_id",
        how="inner",
    )

    if df.empty:
        return df

    # Peer group size for each group/year.
    df["peer_group_size"] = (
        df.groupby(["peer_group_name", "year"])["company_id"]
        .transform("nunique")
    )

    for metric, higher_is_better in HIGHER_IS_BETTER.items():
        if metric in df.columns:
            df = add_peer_metric_ranking(
                df,
                metric,
                higher_is_better,
            )

    for metric, higher_is_better in LOWER_IS_BETTER.items():
        if metric in df.columns:
            df = add_peer_metric_ranking(
                df,
                metric,
                higher_is_better,
            )

    rank_columns = [
        f"{metric}_peer_rank"
        for metric in list(HIGHER_IS_BETTER) + list(LOWER_IS_BETTER)
        if metric in df.columns
    ]

    if rank_columns:
        df["average_peer_rank"] = df[rank_columns].mean(axis=1)
    else:
        df["average_peer_rank"] = None

    df = df.sort_values(
        [
            "year",
            "peer_group_name",
            "average_peer_rank",
            "company_id",
        ],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)

    return df


def write_edge_log(result: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "BLUESTOCK PEER COMPARISON - DAY 17",
        "=" * 70,
        f"Rows generated: {len(result)}",
        f"Companies: {result['company_id'].nunique() if not result.empty else 0}",
        f"Peer groups: {result['peer_group_name'].nunique() if not result.empty else 0}",
    ]

    if not result.empty:
        lines.extend(
            [
                "",
                "Peer group sizes:",
            ]
        )

        sizes = (
            result[
                ["peer_group_name", "peer_group_size"]
            ]
            .drop_duplicates()
            .sort_values("peer_group_name")
        )

        for _, row in sizes.iterrows():
            lines.append(
                f"{row['peer_group_name']}: {int(row['peer_group_size'])}"
            )

        lines.extend(
            [
                "",
                f"Benchmark rows: {int(result['is_benchmark'].sum())}",
                (
                    "Financial rows: "
                    f"{int(result['is_financial_company'].sum())}"
                ),
            ]
        )

    EDGE_LOG.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BLUESTOCK — DAY 17 PEER COMPARISON")
    print("=" * 70)

    data = load_all_data()
    result = build_peer_comparison(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    write_edge_log(result)

    print(f"Rows generated : {len(result)}")
    print(
        f"Companies      : "
        f"{result['company_id'].nunique() if not result.empty else 0}"
    )
    print(
        f"Peer groups    : "
        f"{result['peer_group_name'].nunique() if not result.empty else 0}"
    )
    print(f"Output         : {OUTPUT_CSV}")
    print(f"Edge log       : {EDGE_LOG}")
    print()

    if not result.empty:
        print(
            result[
                [
                    "company_id",
                    "peer_group_name",
                    "year",
                    "is_benchmark",
                    "peer_group_size",
                    "return_on_equity_pct",
                    "return_on_equity_pct_peer_rank",
                    "debt_to_equity",
                    "debt_to_equity_peer_rank",
                    "average_peer_rank",
                ]
            ].head(20).to_string(index=False)
        )


if __name__ == "__main__":
    main()
