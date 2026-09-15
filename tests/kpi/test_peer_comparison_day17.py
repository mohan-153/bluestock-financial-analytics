"""
Day 17 Peer Comparison tests.
"""

import pandas as pd
import pytest

from src.analytics.peer_comparison_day17 import (
    calculate_peer_percentile,
    calculate_peer_rank,
    prepare_peer_groups,
)


def test_rank_higher_is_better():
    values = pd.Series([30, 20, 10])
    result = calculate_peer_rank(values, higher_is_better=True)

    assert result.tolist() == [1.0, 2.0, 3.0]


def test_rank_lower_is_better():
    values = pd.Series([1, 2, 3])
    result = calculate_peer_rank(values, higher_is_better=False)

    assert result.tolist() == [1.0, 2.0, 3.0]


def test_rank_handles_missing():
    values = pd.Series([30, None, 10])
    result = calculate_peer_rank(values, higher_is_better=True)

    assert result.iloc[0] == 1
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == 2


def test_rank_ties():
    values = pd.Series([30, 30, 10])
    result = calculate_peer_rank(values, higher_is_better=True)

    assert result.tolist() == [1.0, 1.0, 3.0]


def test_percentile_higher_is_better():
    values = pd.Series([30, 20, 10])
    result = calculate_peer_percentile(values, higher_is_better=True)

    assert result.iloc[0] > result.iloc[1]
    assert result.iloc[1] > result.iloc[2]


def test_percentile_lower_is_better():
    values = pd.Series([1, 2, 3])
    result = calculate_peer_percentile(values, higher_is_better=False)

    assert result.iloc[0] > result.iloc[1]
    assert result.iloc[1] > result.iloc[2]


def test_percentile_single_value():
    values = pd.Series([10])
    result = calculate_peer_percentile(values, higher_is_better=True)

    assert result.iloc[0] == pytest.approx(100)


def test_peer_group_preparation():
    peers = pd.DataFrame(
        [
            {
                "peer_group_name": "Large Banks",
                "company_id": " abc ",
                "is_benchmark": "1",
            },
            {
                "peer_group_name": "Large Banks",
                "company_id": "XYZ",
                "is_benchmark": "false",
            },
        ]
    )

    result = prepare_peer_groups(peers)

    assert result.loc[0, "company_id"] == "ABC"
    assert bool(result.loc[0, "is_benchmark"]) is True
    assert bool(result.loc[1, "is_benchmark"]) is False


def test_peer_group_missing_column():
    peers = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "peer_group_name": "Group",
            }
        ]
    )

    with pytest.raises(ValueError):
        prepare_peer_groups(peers)
