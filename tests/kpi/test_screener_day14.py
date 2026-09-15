"""
Day 14 KPI + Screener tests.
"""

import pandas as pd
import pytest

from src.analytics.screener_day14 import (
    build_screener_flags,
    passes_max,
    passes_min,
)


def test_minimum_passes():
    assert passes_min(15, 15) is True


def test_minimum_fails():
    assert passes_min(14.99, 15) is False


def test_minimum_missing_fails():
    assert passes_min(None, 15) is False


def test_maximum_passes():
    assert passes_max(1, 1) is True


def test_maximum_fails():
    assert passes_max(1.01, 1) is False


def test_maximum_missing_fails():
    assert passes_max(None, 1) is False


def test_non_financial_all_kpis_pass():
    row = pd.Series(
        {
            "is_financial_company": False,
            "return_on_equity_pct": 20,
            "roce_pct": 20,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": 0.5,
            "interest_coverage": 5,
        }
    )

    result = build_screener_flags(row)

    assert result["kpi_pass_count"] == 6
    assert result["screener_pass"] is True


def test_non_financial_debt_failure():
    row = pd.Series(
        {
            "is_financial_company": False,
            "return_on_equity_pct": 20,
            "roce_pct": 20,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": 2,
            "interest_coverage": 5,
        }
    )

    result = build_screener_flags(row)

    assert result["de_pass"] is False
    assert result["screener_pass"] is False


def test_non_financial_interest_failure():
    row = pd.Series(
        {
            "is_financial_company": False,
            "return_on_equity_pct": 20,
            "roce_pct": 20,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": 0.5,
            "interest_coverage": 2,
        }
    )

    result = build_screener_flags(row)

    assert result["icr_pass"] is False
    assert result["screener_pass"] is False


def test_financial_carveout_ignores_industrial_debt_and_icr():
    row = pd.Series(
        {
            "is_financial_company": True,
            "return_on_equity_pct": 20,
            "roce_pct": 20,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": None,
            "interest_coverage": None,
        }
    )

    result = build_screener_flags(row)

    assert result["de_pass"] is True
    assert result["icr_pass"] is True
    assert result["kpi_pass_count"] == 6
    assert result["screener_pass"] is True


def test_financial_company_still_needs_general_kpis():
    row = pd.Series(
        {
            "is_financial_company": True,
            "return_on_equity_pct": 10,
            "roce_pct": 20,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": None,
            "interest_coverage": None,
        }
    )

    result = build_screener_flags(row)

    assert result["roe_pass"] is False
    assert result["screener_pass"] is False


def test_kpi_pass_count():
    row = pd.Series(
        {
            "is_financial_company": False,
            "return_on_equity_pct": 20,
            "roce_pct": 10,
            "operating_profit_margin_pct": 15,
            "cfo_to_sales_pct": 10,
            "debt_to_equity": 0.5,
            "interest_coverage": 2,
        }
    )

    result = build_screener_flags(row)

    assert result["kpi_pass_count"] == 4


def test_missing_kpi_does_not_pass():
    row = pd.Series(
        {
            "is_financial_company": False,
            "return_on_equity_pct": None,
            "roce_pct": None,
            "operating_profit_margin_pct": None,
            "cfo_to_sales_pct": None,
            "debt_to_equity": None,
            "interest_coverage": None,
        }
    )

    result = build_screener_flags(row)

    assert result["kpi_pass_count"] == 0
    assert result["screener_pass"] is False
