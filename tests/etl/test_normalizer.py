from src.etl.normalizer import normalize_year, normalize_ticker


def test_normalize_year():
    assert normalize_year(2024) == "2024-03"
    assert normalize_year("2024") == "2024-03"
    assert normalize_year("FY2024") == "2024-03"
    assert normalize_year("2024-25") == "2024-03"
    assert normalize_year("Mar 2024") == "2024-03"
    assert normalize_year("Mar-24") == "2024-03"
    assert normalize_year("Mar 24") == "2024-03"
    assert normalize_year("Dec 2012") == "2012-12"
    assert normalize_year("Mar-13") == "2013-03"


def test_normalize_year_invalid():
    assert normalize_year(None) is None
    assert normalize_year("invalid") is None
    assert normalize_year("TTM") is None


def test_normalize_ticker():
    assert normalize_ticker("tcs") == "TCS"
    assert normalize_ticker(" TCS ") == "TCS"
    assert normalize_ticker("tCs") == "TCS"


def test_normalize_ticker_empty():
    assert normalize_ticker("") is None
    assert normalize_ticker(None) is None