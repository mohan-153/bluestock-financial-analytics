"""
Bluestock Financial Analytics
Sprint 3 - Day 18
FastAPI endpoints.

Read-only API over data/nifty100.db.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"

app = FastAPI(
    title="Bluestock Financial Analytics API",
    version="1.0.0",
    description="Read-only API for Bluestock Nifty 100 analytics.",
)


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return dict(row) if row else None


def table_exists(table_name: str) -> bool:
    result = fetch_one(
        """
        SELECT 1 AS found
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    )
    return result is not None


@app.get("/health")
def health() -> dict[str, Any]:
    """API and database health check."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as exc:
        return {
            "status": "error",
            "database": "unavailable",
            "detail": str(exc),
        }


@app.get("/companies")
def companies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Return paginated company master data."""
    total = fetch_one("SELECT COUNT(*) AS count FROM companies")["count"]

    rows = fetch_all(
        """
        SELECT
            company_id,
            company_name,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        ORDER BY company_id
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": rows,
    }


@app.get("/companies/{company_id}")
def company(company_id: str) -> dict[str, Any]:
    """Return one company."""
    row = fetch_one(
        """
        SELECT
            company_id,
            company_name,
            company_logo,
            chart_link,
            about_company,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        WHERE UPPER(company_id) = UPPER(?)
        """,
        (company_id.strip(),),
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return row


@app.get("/financials/{company_id}")
def financials(
    company_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Return P&L and balance-sheet rows for a company."""
    pnl = fetch_all(
        """
        SELECT *
        FROM profitandloss
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year DESC
        LIMIT ?
        """,
        (company_id.strip(), limit),
    )

    balance = fetch_all(
        """
        SELECT *
        FROM balancesheet
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year DESC
        LIMIT ?
        """,
        (company_id.strip(), limit),
    )

    if not pnl and not balance:
        raise HTTPException(status_code=404, detail="Financial data not found")

    return {
        "company_id": company_id.strip().upper(),
        "profit_and_loss": pnl,
        "balance_sheet": balance,
    }


@app.get("/ratios/{company_id}")
def ratios(
    company_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Return calculated financial ratios."""
    rows = fetch_all(
        """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year DESC
        LIMIT ?
        """,
        (company_id.strip(), limit),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Ratio data not found")

    return {
        "company_id": company_id.strip().upper(),
        "count": len(rows),
        "data": rows,
    }


@app.get("/screener")
def screener(
    passed_only: bool = False,
    company_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    """Return screener snapshot rows."""
    if not table_exists("screener_snapshot"):
        raise HTTPException(
            status_code=503,
            detail="screener_snapshot table is not available",
        )

    conditions = []
    params: list[Any] = []

    if passed_only:
        conditions.append("screener_pass = 1")

    if company_id:
        conditions.append("UPPER(company_id) = UPPER(?)")
        params.append(company_id.strip())

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = fetch_all(
        f"""
        SELECT *
        FROM screener_snapshot
        {where}
        ORDER BY year DESC, company_id
        LIMIT ?
        """,
        (*params, limit),
    )

    return {
        "count": len(rows),
        "passed_only": passed_only,
        "data": rows,
    }


@app.get("/peers/{company_id}")
def peers(company_id: str) -> dict[str, Any]:
    """Return peer comparison rows for a company."""
    if not table_exists("peer_comparison"):
        raise HTTPException(
            status_code=503,
            detail="peer_comparison table is not available",
        )

    rows = fetch_all(
        """
        SELECT *
        FROM peer_comparison
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year DESC, peer_group_name
        """,
        (company_id.strip(),),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Peer data not found")

    return {
        "company_id": company_id.strip().upper(),
        "count": len(rows),
        "data": rows,
    }


@app.get("/stock/{company_id}")
def stock(
    company_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Return stock-market analytics."""
    if not table_exists("stock_market_analytics"):
        raise HTTPException(
            status_code=503,
            detail="stock_market_analytics table is not available",
        )

    rows = fetch_all(
        """
        SELECT *
        FROM stock_market_analytics
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY calendar_year DESC
        LIMIT ?
        """,
        (company_id.strip(), limit),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Stock data not found")

    return {
        "company_id": company_id.strip().upper(),
        "count": len(rows),
        "data": rows,
    }


@app.get("/cagr/{company_id}")
def cagr(
    company_id: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Return CAGR analytics from the generated CSV."""
    cagr_path = PROJECT_ROOT / "output" / "cagr_results.csv"

    if not cagr_path.exists():
        raise HTTPException(
            status_code=503,
            detail="CAGR output is not available",
        )

    # Keep the API dependency-light: pandas is already a project dependency.
    import pandas as pd

    df = pd.read_csv(cagr_path)
    if "company_id" not in df.columns:
        raise HTTPException(status_code=500, detail="Invalid CAGR output")

    rows = (
        df[df["company_id"].astype(str).str.upper() == company_id.strip().upper()]
        .head(limit)
        .where(pd.notna(df), None)
        .to_dict(orient="records")
    )

    if not rows:
        raise HTTPException(status_code=404, detail="CAGR data not found")

    return {
        "company_id": company_id.strip().upper(),
        "count": len(rows),
        "data": rows,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Bluestock Financial Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
