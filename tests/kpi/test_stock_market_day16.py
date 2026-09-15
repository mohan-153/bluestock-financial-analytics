"""
Day 16 Stock & Market Analytics tests.
"""

import pandas as pd
import pytest

from src.analytics.stock_market_day16 import (
    calculate_annual_return,
    calculate_annualized_volatility,
    calculate_daily_returns,
    calculate_max_drawdown,
)


def test_annual_return():
    assert calculate_annual_return(100, 120) == pytest.approx(20)


def test_annual_return_loss():
    assert calculate_annual_return(200, 150) == pytest.approx(-25)


def test_annual_return_invalid_base():
    assert calculate_annual_return(0, 100) is None


def test_annual_return_missing():
    assert calculate_annual_return(None, 100) is None


def test_daily_returns():
    prices = pd.Series([100, 110, 99])
    result = calculate_daily_returns(prices)

    assert len(result) == 2
    assert result.iloc[0] == pytest.approx(0.10)


def test_volatility_needs_two_returns():
    prices = pd.Series([100, 110])
    assert calculate_annualized_volatility(prices) is None


def test_volatility_constant_prices():
    prices = pd.Series([100, 100, 100, 100])
    assert calculate_annualized_volatility(prices) == pytest.approx(0)


def test_max_drawdown():
    prices = pd.Series([100, 120, 90, 110])
    # Peak 120 -> trough 90 = -25%
    assert calculate_max_drawdown(prices) == pytest.approx(-25)


def test_max_drawdown_no_decline():
    prices = pd.Series([100, 110, 120])
    assert calculate_max_drawdown(prices) == pytest.approx(0)


def test_max_drawdown_empty():
    prices = pd.Series([], dtype=float)
    assert calculate_max_drawdown(prices) is None
