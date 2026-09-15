"""
Day 18 API tests.
"""

import sqlite3

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Bluestock Financial Analytics API"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_companies():
    response = client.get("/companies?limit=5")
    assert response.status_code == 200

    body = response.json()
    assert body["limit"] == 5
    assert body["total"] >= 1
    assert len(body["data"]) <= 5


def test_company_case_insensitive():
    response = client.get("/companies/RELIANCE")
    assert response.status_code == 200
    assert response.json()["company_id"].upper() == "RELIANCE"


def test_missing_company():
    response = client.get("/companies/DOES_NOT_EXIST")
    assert response.status_code == 404


def test_financials():
    response = client.get("/financials/RELIANCE?limit=5")
    assert response.status_code == 200

    body = response.json()
    assert "profit_and_loss" in body
    assert "balance_sheet" in body


def test_ratios():
    response = client.get("/ratios/RELIANCE?limit=5")
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_screener():
    response = client.get("/screener?limit=5")
    assert response.status_code == 200
    assert len(response.json()["data"]) <= 5


def test_peers_service_or_data():
    response = client.get("/peers/MARUTI")
    assert response.status_code in (200, 404, 503)


def test_stock_service_or_data():
    response = client.get("/stock/RELIANCE")
    assert response.status_code in (200, 404, 503)


def test_invalid_limit():
    response = client.get("/companies?limit=0")
    assert response.status_code == 422


def test_sqlite_database_is_readable():
    # Confirms the API is pointing at a real SQLite database through the
    # application's configured path.
    from src.api.main import DB_PATH

    connection = sqlite3.connect(DB_PATH)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()
    finally:
        connection.close()

    assert row[0] >= 1
