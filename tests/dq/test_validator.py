import pandas as pd

from src.etl.validator import (
    check_primary_key_unique,
    check_required_columns,
    check_company_pk_unique,
    check_annual_pk_unique,
    check_foreign_key_integrity,
    check_balance_sheet,
    check_opm_crosscheck,
    check_positive_sales,
    check_year_format,
    check_ticker_format,
    check_net_cash,
    check_fixed_assets,
    check_tax_rate,
    check_dividend_payout,
    check_url_format,
    check_eps_sign_consistency,
    check_bse_ase_balance,
    check_coverage,
)


def test_dq04_balance_sheet():
    df = pd.DataFrame({
        "total_assets": [1000],
        "total_liabilities": [995],
    })

    assert check_balance_sheet(df)


def test_dq04_balance_sheet_failure():
    df = pd.DataFrame({
        "total_assets": [1000],
        "total_liabilities": [900],
    })

    assert not check_balance_sheet(df)


def test_dq05_opm_crosscheck():
    df = pd.DataFrame({
        "opm_percentage": [20.0],
        "op_profit": [200],
        "sales": [1000],
    })

    assert check_opm_crosscheck(df)


def test_dq05_opm_crosscheck_failure():
    df = pd.DataFrame({
        "opm_percentage": [25.0],
        "op_profit": [200],
        "sales": [1000],
    })

    assert not check_opm_crosscheck(df)


def test_dq06_positive_sales():
    df = pd.DataFrame({
        "sales": [100, 200],
        "broad_sector": ["IT", "Industrials"],
    })

    assert check_positive_sales(df)


def test_dq06_zero_sales():
    df = pd.DataFrame({
        "sales": [0],
        "broad_sector": ["IT"],
    })

    assert not check_positive_sales(df)


def test_dq07_year_format():
    values = pd.Series(["2024-25", "2023-24"])

    assert check_year_format(values)


def test_dq07_invalid_year():
    values = pd.Series(["2024", "invalid"])

    assert not check_year_format(values)


def test_dq08_ticker_format():
    values = pd.Series(["TCS", "INFY", "RELIANCE"])

    assert check_ticker_format(values)


def test_dq08_invalid_ticker():
    values = pd.Series(["A"])

    assert not check_ticker_format(values)


def test_dq09_net_cash():
    df = pd.DataFrame({
        "net_cash_flow": [100],
        "CFO": [200],
        "CFI": [-50],
        "CFF": [-50],
    })

    assert check_net_cash(df)


def test_dq09_net_cash_failure():
    df = pd.DataFrame({
        "net_cash_flow": [100],
        "CFO": [200],
        "CFI": [-20],
        "CFF": [-50],
    })

    assert not check_net_cash(df)


def test_dq10_fixed_assets():
    df = pd.DataFrame({
        "fixed_assets": [100, 200],
    })

    assert check_fixed_assets(df)


def test_dq10_negative_fixed_assets():
    df = pd.DataFrame({
        "fixed_assets": [100, -20],
    })

    assert not check_fixed_assets(df)


def test_dq11_tax_rate():
    df = pd.DataFrame({
        "tax_percentage": [10, 30, 60],
    })

    assert check_tax_rate(df)


def test_dq11_tax_rate_failure():
    df = pd.DataFrame({
        "tax_percentage": [70],
    })

    assert not check_tax_rate(df)


def test_dq12_dividend_payout():
    df = pd.DataFrame({
        "dividend_payout": [50, 100, 200],
    })

    assert check_dividend_payout(df)


def test_dq12_dividend_payout_failure():
    df = pd.DataFrame({
        "dividend_payout": [250],
    })

    assert not check_dividend_payout(df)


def test_dq13_url_format():
    values = pd.Series([
        "https://example.com/report.pdf",
    ])

    assert check_url_format(values)


def test_dq13_invalid_url():
    values = pd.Series([
        "not-a-url",
    ])

    assert not check_url_format(values)


def test_dq14_eps_consistency():
    df = pd.DataFrame({
        "eps": [10],
        "net_profit": [100],
    })

    assert check_eps_sign_consistency(df)


def test_dq14_eps_mismatch():
    df = pd.DataFrame({
        "eps": [-10],
        "net_profit": [100],
    })

    assert not check_eps_sign_consistency(df)


def test_dq15_balance():
    df = pd.DataFrame({
        "total_assets": [1000],
        "total_liabilities": [1000],
    })

    assert check_bse_ase_balance(df)


def test_dq15_balance_failure():
    df = pd.DataFrame({
        "total_assets": [1000],
        "total_liabilities": [900],
    })

    assert not check_bse_ase_balance(df)


def test_dq16_coverage():
    df = pd.DataFrame({
        "company_id": [1, 1, 1, 1, 1],
        "year": [
            "2020-21",
            "2021-22",
            "2022-23",
            "2023-24",
            "2024-25",
        ],
    })

    assert check_coverage(df)


def test_dq16_insufficient_coverage():
    df = pd.DataFrame({
        "company_id": [1, 1, 1],
        "year": [
            "2022-23",
            "2023-24",
            "2024-25",
        ],
    })

    assert not check_coverage(df)