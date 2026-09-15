"""
Day 13 Bank / Financials Carve-out tests.
"""

import pandas as pd
import pytest

from src.analytics.financials_carveout_day13 import (
    apply_carve_out,
    classify_financial_company,
    classify_sector_table,
)


def test_bank_is_financial():
    assert classify_financial_company("Financial Services", "Banks") is True


def test_insurance_is_financial():
    assert classify_financial_company("Financials", "Insurance") is True


def test_nbfc_is_financial():
    assert classify_financial_company("Financial Services", "NBFC") is True


def test_lending_is_financial():
    assert classify_financial_company("Financial Services", "Lending") is True


def test_manufacturing_is_not_financial():
    assert classify_financial_company("Industrials", "Capital Goods") is False


def test_sector_classification_columns():
    sectors = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "broad_sector": "Financial Services",
                "sub_sector": "Banks",
            },
            {
                "company_id": "XYZ",
                "broad_sector": "Industrials",
                "sub_sector": "Capital Goods",
            },
        ]
    )

    result = classify_sector_table(sectors)

    assert result["is_financial_company"].tolist() == [True, False]
    assert result["carve_out_category"].tolist() == [
        "FINANCIALS",
        "NON_FINANCIALS",
    ]


def test_carve_out_keeps_financial_rows():
    ratios = pd.DataFrame(
        [
            {
                "company_id": "BANK1",
                "year": "2024-03",
                "debt_to_equity": 5.0,
                "interest_coverage": 2.0,
                "asset_turnover": 0.4,
                "operating_profit_margin_pct": 20.0,
                "free_cash_flow_cr": 100.0,
            }
        ]
    )

    sectors = pd.DataFrame(
        [
            {
                "company_id": "BANK1",
                "broad_sector": "Financial Services",
                "sub_sector": "Banks",
                "is_financial_company": True,
                "carve_out_category": "FINANCIALS",
            }
        ]
    )

    result = apply_carve_out(ratios, sectors)

    assert len(result) == 1
    assert bool(result.loc[0, "is_financial_company"]) is True


def test_carve_out_excludes_industrial_metrics_for_financials():
    ratios = pd.DataFrame(
        [
            {
                "company_id": "BANK1",
                "year": "2024-03",
                "debt_to_equity": 5.0,
                "interest_coverage": 2.0,
                "asset_turnover": 0.4,
                "operating_profit_margin_pct": 20.0,
                "free_cash_flow_cr": 100.0,
            }
        ]
    )

    sectors = pd.DataFrame(
        [
            {
                "company_id": "BANK1",
                "broad_sector": "Financial Services",
                "sub_sector": "Banks",
                "is_financial_company": True,
                "carve_out_category": "FINANCIALS",
            }
        ]
    )

    result = apply_carve_out(ratios, sectors)

    for column in [
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "operating_profit_margin_pct",
        "free_cash_flow_cr",
    ]:
        assert pd.isna(result.loc[0, column])

    assert bool(result.loc[0, "industrial_screener_eligible"]) is False


def test_non_financial_metrics_are_preserved():
    ratios = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": "2024-03",
                "debt_to_equity": 0.5,
                "interest_coverage": 8.0,
                "asset_turnover": 1.5,
                "operating_profit_margin_pct": 18.0,
                "free_cash_flow_cr": 200.0,
            }
        ]
    )

    sectors = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "broad_sector": "Industrials",
                "sub_sector": "Capital Goods",
                "is_financial_company": False,
                "carve_out_category": "NON_FINANCIALS",
            }
        ]
    )

    result = apply_carve_out(ratios, sectors)

    assert result.loc[0, "debt_to_equity"] == pytest.approx(0.5)
    assert result.loc[0, "interest_coverage"] == pytest.approx(8.0)
    assert result.loc[0, "asset_turnover"] == pytest.approx(1.5)
    assert result.loc[0, "operating_profit_margin_pct"] == pytest.approx(18.0)
    assert result.loc[0, "free_cash_flow_cr"] == pytest.approx(200.0)
    assert bool(result.loc[0, "industrial_screener_eligible"]) is True


def test_unknown_company_is_unclassified():
    ratios = pd.DataFrame(
        [
            {
                "company_id": "UNKNOWN",
                "year": "2024-03",
                "debt_to_equity": 1.0,
            }
        ]
    )

    sectors = pd.DataFrame(
        columns=[
            "company_id",
            "broad_sector",
            "sub_sector",
            "is_financial_company",
            "carve_out_category",
        ]
    )

    result = apply_carve_out(ratios, sectors)

    assert result.loc[0, "carve_out_category"] == "UNCLASSIFIED"
    assert bool(result.loc[0, "industrial_screener_eligible"]) is True
