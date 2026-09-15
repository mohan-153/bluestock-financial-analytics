"""
Day 08 profitability ratio tests.
"""

import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    ebit_margin,
    return_on_equity,
    return_on_capital,
    return_on_assets,
)


def test_npm_normal():
    assert net_profit_margin(100, 1000) == pytest.approx(10.0)


def test_npm_zero_sales():
    assert net_profit_margin(100, 0) is None


def test_opm_normal():
    assert operating_profit_margin(250, 1000) == pytest.approx(25.0)


def test_opm_zero_sales():
    assert operating_profit_margin(250, 0) is None


def test_ebit_margin():
    assert ebit_margin(300, 50, 1000) == pytest.approx(25.0)


def test_roe_normal():
    assert return_on_equity(150, 500, 500) == pytest.approx(15.0)


def test_roe_non_positive_equity():
    assert return_on_equity(150, 500, -500) is None


def test_roce_normal():
    assert return_on_capital(300, 50, 500, 300, 200) == pytest.approx(25.0)

def test_roa_zero_assets():
    assert return_on_assets(100, 0) is None
