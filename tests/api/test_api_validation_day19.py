"""
Bluestock Financial Analytics
Sprint 3 - Day 19
API Validation & Tests

Focused validation tests for the Day 18 FastAPI service.
These tests verify status codes, query validation, response shape,
case-insensitive company lookup, pagination, and service availability.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_response_contract():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_root_response_contract():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()

    assert body["name"] == "Bluestock Financial Analytics API"
    assert body["version"] == "1.0.0"
    assert body["docs"] == "/docs"


def test_companies_default_pagination():
    response = client.get("/companies")

    assert response.status_code == 200
    body = response.json()

    assert set(["total", "limit", "offset", "data"]) <= body.keys()
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 20


def test_companies_offset():
    response = client.get("/companies?limit=5&offset=5")

    assert response.status_code == 200
    body = response.json()

    assert body["limit"] == 5
    assert body["offset"] == 5
    assert len(body["data"]) <= 5


def test_companies_limit_upper_bound():
    response = client.get("/companies?limit=101")

    assert response.status_code == 422


def test_companies_negative_offset():
    response = client.get("/companies?offset=-1")

    assert response.status_code == 422


def test_company_lookup_is_case_insensitive():
    response = client.get("/companies/reliance")

    assert response.status_code == 200
    assert response.json()["company_id"] == "RELIANCE"


def test_company_not_found_contract():
    response = client.get("/companies/NOT_A_REAL_COMPANY")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_financials_limit_validation():
    response = client.get("/financials/RELIANCE?limit=0")

    assert response.status_code == 422


def test_ratios_not_found_contract():
    response = client.get("/ratios/NOT_A_REAL_COMPANY")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ratio data not found"


def test_screener_limit_validation():
    response = client.get("/screener?limit=501")

    assert response.status_code == 422


def test_screener_passed_only_contract():
    response = client.get("/screener?passed_only=true&limit=10")

    assert response.status_code == 200
    body = response.json()

    assert body["passed_only"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 10

    for row in body["data"]:
        assert row["screener_pass"] in (0, 1, True, False)


def test_screener_company_filter():
    response = client.get("/screener?company_id=RELIANCE&limit=10")

    assert response.status_code == 200

    for row in response.json()["data"]:
        assert str(row["company_id"]).upper() == "RELIANCE"


def test_peers_unknown_company():
    response = client.get("/peers/NOT_A_REAL_COMPANY")

    assert response.status_code in (404, 503)


def test_stock_unknown_company():
    response = client.get("/stock/NOT_A_REAL_COMPANY")

    assert response.status_code in (404, 503)


def test_cagr_limit_validation():
    response = client.get("/cagr/RELIANCE?limit=0")

    assert response.status_code == 422


def test_openapi_document_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()

    assert body["info"]["title"] == "Bluestock Financial Analytics API"

    paths = body["paths"]
    expected = {
        "/",
        "/health",
        "/companies",
        "/companies/{company_id}",
        "/financials/{company_id}",
        "/ratios/{company_id}",
        "/screener",
        "/peers/{company_id}",
        "/stock/{company_id}",
        "/cagr/{company_id}",
    }

    assert expected <= set(paths)
