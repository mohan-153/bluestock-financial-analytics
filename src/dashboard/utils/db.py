from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
DB_PATH=Path(__file__).resolve().parents[3]/"data"/"nifty100.db"
def q(sql,params=()):
    with sqlite3.connect(DB_PATH) as c:return pd.read_sql_query(sql,c,params=params)
@st.cache_data(ttl=600)
def get_companies(): return q("SELECT c.*,s.broad_sector,s.sub_sector FROM companies c LEFT JOIN sectors s ON s.company_id=c.company_id")
@st.cache_data(ttl=600)
def get_financial_ratios_all(): return q("SELECT * FROM financial_ratios")
@st.cache_data(ttl=600)
def get_profit_loss_all(): return q("SELECT company_id,year,sales,net_profit,eps FROM profitandloss")
@st.cache_data(ttl=600)
def get_market_all(): return q("SELECT * FROM stock_market_analytics")
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "nifty100.db"


def q(sql, params=()):
    """Execute a SELECT query."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=600)
def get_companies():
    return q("""
        SELECT
            c.*,
            s.broad_sector,
            s.sub_sector
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.company_id
        ORDER BY c.company_id
    """)


@st.cache_data(ttl=600)
def get_financial_ratios_all():
    """Load all financial ratio records."""
    return q("""
        SELECT *
        FROM financial_ratios
        ORDER BY company_id, year
    """)


@st.cache_data(ttl=600)
def get_profit_loss_all():
    """Load P&L records required for CAGR calculations."""
    return q("""
        SELECT
            company_id,
            year,
            sales,
            net_profit,
            eps
        FROM profitandloss
        ORDER BY company_id, year
    """)


@st.cache_data(ttl=600)
def get_market_all():
    """Load integrated stock-market analytics."""
    return q("""
        SELECT *
        FROM stock_market_analytics
        ORDER BY company_id, calendar_year
    """)


@st.cache_data(ttl=600)
def get_ratios(ticker):
    return q("""
        SELECT *
        FROM financial_ratios
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_pl(ticker):
    return q("""
        SELECT *
        FROM profitandloss
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_bs(ticker):
    return q("""
        SELECT *
        FROM balancesheet
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_cf(ticker):
    return q("""
        SELECT *
        FROM cashflow
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_valuation(ticker):
    return q("""
        SELECT *
        FROM stock_market_analytics
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY calendar_year DESC
    """, (ticker,))

@st.cache_data(ttl=600)
def get_screener_snapshot():
    """Load the existing Day 15 screener snapshot for Home/legacy dashboard pages."""
    return q("""
        SELECT *
        FROM screener_snapshot
        ORDER BY company_id, year
    """)


@st.cache_data(ttl=600)
def get_peer_groups():
    """Load available peer groups."""
    return q("""
        SELECT DISTINCT peer_group_name
        FROM peer_comparison
        ORDER BY peer_group_name
    """)


@st.cache_data(ttl=600)
def get_peers(group_name):
    """Load peer comparison rows for a peer group."""
    return q("""
        SELECT *
        FROM peer_comparison
        WHERE peer_group_name = ?
        ORDER BY year DESC, company_id
    """, (group_name,))


@st.cache_data(ttl=600)
def get_pros_cons(ticker):
    """Load company pros and cons."""
    return q("""
        SELECT *
        FROM prosandcons
        WHERE UPPER(company_id) = UPPER(?)
    """, (ticker,))
