import pandas as pd
import streamlit as st
import plotly.express as px

from src.dashboard.day25_common import sql_df, clean_year

st.title("Capital Allocation Map")
st.caption("Latest CFO / CFI / CFF sign patterns across the Nifty 100.")

cf = sql_df("""
    SELECT company_id, year,
           operating_activity,
           investing_activity,
           financing_activity
    FROM cashflow
""")

co = sql_df("""
    SELECT company_id, company_name
    FROM companies
""")

if cf.empty:
    st.warning("Cash flow data is not available.")
    st.stop()

cf["_year"] = clean_year(cf["year"])
cf = cf.dropna(subset=["_year"])
cf = (
    cf.sort_values(["company_id", "_year"])
      .drop_duplicates("company_id", keep="last")
)

for col in [
    "operating_activity",
    "investing_activity",
    "financing_activity",
]:
    cf[col] = pd.to_numeric(cf[col], errors="coerce")

def sign(x):
    if pd.isna(x) or x == 0:
        return "0"
    return "+" if x > 0 else "-"

def classify(row):
    pattern = (
        sign(row.operating_activity),
        sign(row.investing_activity),
        sign(row.financing_activity),
    )

    labels = {
        ("+", "-", "-"): "Reinvestor",
        ("+", "-", "+"): "Shareholder Returns",
        ("+", "+", "-"): "Cash Generator",
        ("+", "+", "+"): "Capital Raiser",
        ("-", "-", "+"): "Distress Signal",
        ("-", "+", "+"): "Rescue / Funding",
        ("-", "-", "-"): "Cash Burn",
        ("-", "+", "-"): "Restructuring",
    }

    return labels.get(pattern, "Unclassified")

cf["pattern"] = cf.apply(classify, axis=1)

view = cf.merge(co, on="company_id", how="left")

summary = (
    view.groupby("pattern", as_index=False)
        .agg(companies=("company_id", "nunique"))
        .sort_values("companies", ascending=False)
)

st.subheader("Capital Allocation Distribution")

fig = px.treemap(
    summary,
    path=["pattern"],
    values="companies",
    title="Nifty 100 Capital Allocation Patterns"
)

fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

patterns = summary["pattern"].tolist()

selected_pattern = st.selectbox(
    "Select a pattern to view companies",
    patterns
)

companies_view = view[
    view["pattern"].eq(selected_pattern)
].copy()

st.subheader(
    f"{selected_pattern} — {len(companies_view)} companies"
)

display_cols = [
    "company_id",
    "company_name",
    "year",
    "operating_activity",
    "investing_activity",
    "financing_activity",
    "pattern",
]

st.dataframe(
    companies_view[display_cols]
    .sort_values("company_id")
    .round(2),
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download Pattern Companies CSV",
    companies_view[display_cols].to_csv(index=False).encode("utf-8"),
    "capital_allocation_pattern.csv",
    "text/csv"
)

st.caption(
    "Classification is based on the latest available CFO/CFI/CFF sign pattern. "
    "Zero or missing values are treated as neutral."
)
