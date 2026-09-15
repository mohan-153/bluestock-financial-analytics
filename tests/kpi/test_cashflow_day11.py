"""
Day 11 Cash Flow Analytics tests.
"""

import pytest

from src.analytics.cashflow import (
    calculate_cfo_pat,
    calculate_cfo_sales,
    calculate_cashflow_reconciliation,
    calculate_fcf,
)


def test_fcf():
    assert calculate_fcf(100, -40) == pytest.approx(60)


def test_fcf_both_positive():
    assert calculate_fcf(100, 25) == pytest.approx(125)


def test_fcf_missing_value():
    assert calculate_fcf(None, 25) is None


def test_reconciliation_ok():
    difference, status = calculate_cashflow_reconciliation(
        100, -40, 20, 80
    )
    assert difference == pytest.approx(0)
    assert status == "OK"


def test_reconciliation_within_tolerance():
    difference, status = calculate_cashflow_reconciliation(
        100, -40, 20, 85
    )
    assert difference == pytest.approx(5)
    assert status == "OK"


def test_reconciliation_mismatch():
    difference, status = calculate_cashflow_reconciliation(
        100, -40, 20, 100
    )
    assert difference == pytest.approx(20)
    assert status == "MISMATCH"


def test_reconciliation_missing():
    difference, status = calculate_cashflow_reconciliation(
        None, -40, 20, 80
    )
    assert difference is None
    assert status == "INSUFFICIENT"


def test_cfo_pat():
    assert calculate_cfo_pat(120, 100) == pytest.approx(1.2)


def test_cfo_pat_zero_pat():
    assert calculate_cfo_pat(120, 0) is None


def test_cfo_pat_missing():
    assert calculate_cfo_pat(None, 100) is None


def test_cfo_sales():
    assert calculate_cfo_sales(250, 1000) == pytest.approx(25)


def test_cfo_sales_zero_sales():
    assert calculate_cfo_sales(250, 0) is None


def test_cfo_sales_missing():
    assert calculate_cfo_sales(None, 1000) is None
