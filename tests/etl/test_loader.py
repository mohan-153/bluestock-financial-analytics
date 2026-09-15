from src.etl.loader import (
    load_dataset,
    load_all_core_data,
    load_companies,
)

def test_load_companies():
    df = load_companies()

    assert not df.empty
    assert len(df) == 92


def test_load_all_core_data():
    data = load_all_core_data()

    expected_datasets = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
    }

    assert set(data.keys()) == expected_datasets

    for name, df in data.items():
        assert not df.empty, f"{name} is empty"

def test_loader_applies_normalization():
    df = load_companies()

    assert not df.empty

    for column in df.columns:
        column_lower = str(column).strip().lower()

        if column_lower in {"ticker", "symbol", "stock_ticker"}:
            values = df[column].dropna()

            assert all(
                value == str(value).upper()
                for value in values
            )