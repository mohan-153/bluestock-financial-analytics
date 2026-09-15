"""
Day 12 Financial Ratios tests.
"""

import pytest

from src.analytics.financial_ratios_day12 import (
    asset_turnover,
    debt_to_equity,
    free_cash_flow,
    interest_coverage,
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    safe_divide,
)


def test_safe_divide():
    assert safe_divide(20, 5) == pytest.approx(4)


def test_safe_divide_zero():
    assert safe_divide(20, 0) is None


def test_net_profit_margin():
    assert net_profit_margin(150, 1000) == pytest.approx(15)


def test_operating_profit_margin():
    assert operating_profit_margin(200, 1000) == pytest.approx(20)


def test_return_on_equity():
    assert return_on_equity(100, 200, 300) == pytest.approx(20)


def test_debt_to_equity():
    assert debt_to_equity(250, 200, 300) == pytest.approx(0.5)


def test_interest_coverage():
    assert interest_coverage(300, 50, 25) == pytest.approx(10)


def test_interest_coverage_zero_interest():
    assert interest_coverage(300, 50, 0) is None


def test_asset_turnover():
    assert asset_turnover(1000, 500) == pytest.approx(2)


def test_free_cash_flow():
    assert free_cash_flow(500, -200) == pytest.approx(300)


def test_free_cash_flow_missing():
    assert free_cash_flow(None, -200) is None


def test_financial_ratios_module_import():
    from src.analytics.financial_ratios_day12 import calculate_financial_ratios
    assert callable(calculate_financial_ratios)
