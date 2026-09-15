"""
Day 09 leverage and efficiency tests.
"""

import pytest

from src.analytics.leverage import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    interest_status,
    net_debt,
    asset_turnover,
)


def test_de_ratio_normal():
    assert debt_to_equity(200, 500, 500) == pytest.approx(0.2)


def test_de_zero_equity():
    assert debt_to_equity(200, 500, -500) is None


def test_high_leverage_above_two():
    assert high_leverage_flag(2.01) is True


def test_high_leverage_threshold_not_above_two():
    assert high_leverage_flag(2.0) is False


def test_financials_excluded_from_high_leverage():
    assert high_leverage_flag(5.0, is_financials=True) is False


def test_icr_normal():
    # EBIT = 300 - 50 = 250; ICR = 250 / 50 = 5
    assert interest_coverage_ratio(300, 50, 50) == pytest.approx(5.0)


def test_zero_interest():
    assert interest_coverage_ratio(300, 50, 0) is None
    assert interest_status(0) == "Debt Free / No Interest"


def test_negative_interest():
    assert interest_coverage_ratio(300, 50, -10) is None
    assert interest_status(-10) == "Invalid Negative Interest"


def test_net_debt_requires_cash_balance():
    assert net_debt(500, 100) == pytest.approx(400)
    assert net_debt(500, None) is None


def test_asset_turnover_normal():
    assert asset_turnover(1000, 500) == pytest.approx(2.0)


def test_asset_turnover_zero_assets():
    assert asset_turnover(1000, 0) is None
