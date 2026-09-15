"""Day 23 Home screen."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_companies, get_ratios, get_screener_snapshot, get_valuation

st.title("Nifty 100 Analytics")
st.caption("Financial intelligence overview")
companies = get_companies()
snapshot = get_screener_snapshot()
selected_year = st.sidebar.selectbox("Analysis year", list(range(2019, 2025)), index=5)

def selected_rows(df):
    """Filter a dataframe to the selected year using its year field."""
    if df.empty or "year" not in df.columns:
        return df.iloc[0:0]
    return df[df["year"].astype(str).str[:4].eq(str(selected_year))]

ratio_rows = []
valuation_rows = []
for ticker in companies["company_id"].dropna().astype(str):
    try:
        r = selected_rows(get_ratios(ticker))
        if not r.empty: ratio_rows.append(r.iloc[-1])
        v = get_valuation(ticker)
        if not v.empty and "calendar_year" in v:
            v = v[pd.to_numeric(v["calendar_year"], errors="coerce").eq(selected_year)]
            if not v.empty: valuation_rows.append(v.iloc[-1])
    except Exception:
        pass
ratios = pd.DataFrame(ratio_rows)
valuation = pd.DataFrame(valuation_rows)

def num(df, col):
    """Return a numeric Series for a column."""
    return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(dtype=float)

roe = num(companies, "roe_percentage")
de = num(ratios, "debt_to_equity")
cagr = num(ratios, "revenue_cagr_5yr")
pe = num(valuation, "pe_ratio")

c = st.columns(6)
c[0].metric("Average ROE", f"{roe.mean():.2f}%" if roe.notna().any() else "N/A")
c[1].metric("Median P/E", f"{pe.median():.2f}" if pe.notna().any() else "N/A")
c[2].metric("Median D/E", f"{de.median():.2f}" if de.notna().any() else "N/A")
c[3].metric("Total Companies", int(companies.company_id.nunique()))
c[4].metric("Median Revenue CAGR 5yr", f"{cagr.median():.2f}%" if cagr.notna().any() else "N/A")
c[5].metric("Debt-Free Companies", int((de.fillna(-1) == 0).sum()))

st.subheader(f"Sector Breakdown — {selected_year}")
sector = companies.groupby("broad_sector", dropna=False)["company_id"].nunique().reset_index(name="company_count")
fig = px.pie(sector, names="broad_sector", values="company_count", hole=.45)
fig.update_layout(height=420, margin=dict(l=10,r=10,t=40,b=10))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Top 5 Companies by Quality")
if snapshot.empty:
    st.info("Screener snapshot is not available.")
else:
    s = selected_rows(snapshot)
    score = "composite_quality_score" if "composite_quality_score" in s else "kpi_pass_count"
    if score in s:
        s[score] = pd.to_numeric(s[score], errors="coerce")
        cols = [x for x in ["company_id","company_name","broad_sector",score] if x in s]
        st.dataframe(s.sort_values(score, ascending=False)[cols].head(5), use_container_width=True, hide_index=True)
        if score == "kpi_pass_count":
            st.caption("Composite quality score is not present in the current Day 15 snapshot; KPI pass count is used as the available quality ranking.")
