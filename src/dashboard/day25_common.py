from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st


def _find_project_root():
    """Find the Bluestock project root without depending on Streamlit's runpy cwd."""
    here = Path(__file__).resolve()

    # For src/dashboard/day25_common.py:
    # parents[0] = dashboard
    # parents[1] = src
    # parents[2] = project root
    candidates = [
        here.parents[2],
        Path.cwd(),
        Path(__file__).resolve().parent.parent.parent,
    ]

    for root in candidates:
        db = root / "data" / "nifty100.db"
        if db.is_file():
            return root

    # Keep a deterministic fallback so the error is meaningful.
    return here.parents[2]


PROJECT_ROOT = _find_project_root()
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


def _check_db():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Bluestock database not found at: {DB_PATH}. "
            f"Expected: <project_root>\\data\\nifty100.db"
        )


@st.cache_data(ttl=600)
def sql_df(query, params=()):
    _check_db()
    with sqlite3.connect(str(DB_PATH)) as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def companies():
    return sql_df("""
        SELECT
            c.company_id,
            c.company_name,
            c.about_company,
            s.broad_sector,
            s.sub_sector
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.company_id
        ORDER BY c.company_id
    """)


def clean_year(series):
    return pd.to_numeric(
        series.astype(str).str.extract(r"(\d{4})", expand=False),
        errors="coerce",
    )


def latest_by_company(df, year_col):
    x = df.copy()
    x["_year_num"] = clean_year(x[year_col])
    x = x.dropna(subset=["_year_num"])

    return (
        x.sort_values(["company_id", "_year_num"])
        .drop_duplicates("company_id", keep="last")
        .drop(columns="_year_num")
    )
