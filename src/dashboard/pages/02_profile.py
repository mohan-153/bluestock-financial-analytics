"""Day 23 Company Profile screen."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies, get_pl, get_pros_cons, get_ratios

st.title("Company Profile")
companies = get_companies()
term = st.text_input("Search company or ticker", placeholder="Type ticker or company name...").strip().lower()
m = companies if not term else companies[
    companies.company_id.astype(str).str.lower().str.contains(term, na=False) |
    companies.company_name.astype(str).str.lower().str.contains(term, na=False)
]
if m.empty:
    st.warning("Ticker not found — please try another")
    st.stop()
labels = {r.company_id: f"{r.company_id} — {r.company_name}" for r in m.itertuples()}
ticker = st.selectbox("Select company", list(labels), format_func=labels.get)
company = companies[companies.company_id.eq(ticker)].iloc[0]
st.header(str(company.company_name).replace("\n"," "))
st.caption(f"{ticker} · {company.get('broad_sector','N/A')} · {company.get('sub_sector','N/A')}")
st.write(company.get("about_company") or "About description not available.")

ratios, pl, pc = get_ratios(ticker), get_pl(ticker), get_pros_cons(ticker)
latest = ratios.iloc[-1] if not ratios.empty else pd.Series()
def fmt(x):
    """Format a dashboard KPI value."""
    return "N/A" if pd.isna(x) else f"{float(x):.2f}"

fields = [
    ("ROE","return_on_equity_pct"), ("ROCE","return_on_capital_employed_pct"),
    ("Net Profit Margin","net_profit_margin_pct"), ("D/E","debt_to_equity"),
    ("Revenue CAGR 5yr","revenue_cagr_5yr"), ("FCF","free_cash_flow_cr")
]
tiles = st.columns(6)
for tile, (label, field) in zip(tiles, fields):
    tile.metric(label, fmt(latest.get(field)))

if {"year","sales","net_profit"}.issubset(pl.columns):
    x = pl.copy()
    x["year_label"] = x.year.astype(str)
    x["sales"] = pd.to_numeric(x.sales, errors="coerce")
    x["net_profit"] = pd.to_numeric(x.net_profit, errors="coerce")
    x = x.dropna(subset=["sales","net_profit"]).tail(10)
    st.subheader("10-Year Revenue and Net Profit")
    fig = go.Figure()
    fig.add_bar(x=x.year_label, y=x.sales, name="Revenue")
    fig.add_bar(x=x.year_label, y=x.net_profit, name="Net Profit")
    fig.update_layout(barmode="group", height=430, yaxis_title="₹ Crore")
    st.plotly_chart(fig, width="stretch")

if not ratios.empty and "year" in ratios:
    st.subheader("ROE and ROCE Trend")
    fig = go.Figure()
    for field, label in [("return_on_equity_pct","ROE"),("return_on_capital_employed_pct","ROCE")]:
        if field in ratios:
            fig.add_scatter(x=ratios.year.astype(str), y=pd.to_numeric(ratios[field],errors="coerce"), mode="lines+markers", name=label)
    fig.update_layout(height=400, yaxis_title="%")
    st.plotly_chart(fig, width="stretch")

st.subheader("Pros and Cons")
if pc.empty:
    st.info("Stored pros/cons are not available yet. NLP-generated pros/cons are a Sprint 5 deliverable.")
else:
    for _, row in pc.iterrows():
        if str(row.get("pros") or "").strip(): st.success("✓ " + str(row["pros"]).strip())
        if str(row.get("cons") or "").strip(): st.error("✗ " + str(row["cons"]).strip())

