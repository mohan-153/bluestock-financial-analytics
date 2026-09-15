"""
Day 10 CAGR tests.
"""

import pytest

from src.analytics.cagr import calculate_cagr


def test_positive_to_positive():
    # 100 -> 121 over 2 years = 10% CAGR
    result = calculate_cagr(100, 121, 2)
    assert result.status == "CAGR"
    assert result.value == pytest.approx(10.0)


def test_positive_to_negative():
    result = calculate_cagr(100, -20, 3)
    assert result.value is None
    assert result.status == "DECLINE_TO_LOSS"


def test_negative_to_positive():
    result = calculate_cagr(-100, 20, 3)
    assert result.value is None
    assert result.status == "TURNAROUND"


def test_negative_to_negative():
    result = calculate_cagr(-100, -20, 3)
    assert result.value is None
    assert result.status == "BOTH_NEGATIVE"


def test_zero_base():
    result = calculate_cagr(0, 100, 3)
    assert result.value is None
    assert result.status == "ZERO_BASE"


def test_missing_start():
    result = calculate_cagr(None, 100, 3)
    assert result.value is None
    assert result.status == "INSUFFICIENT"


def test_missing_end():
    result = calculate_cagr(100, None, 3)
    assert result.value is None
    assert result.status == "INSUFFICIENT"


def test_one_year_growth():
    result = calculate_cagr(100, 150, 1)
    assert result.value == pytest.approx(50.0)


def test_invalid_horizon():
    with pytest.raises(ValueError):
        calculate_cagr(100, 120, 0)


def test_negative_to_zero_is_decline_to_loss():
    result = calculate_cagr(100, 0, 3)
    assert result.value is None
    assert result.status == "INSUFFICIENT"
