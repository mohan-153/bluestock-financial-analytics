import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.dashboard.day25_common import sql_df, companies, clean_year

st.title("Trend Analysis")
st.caption("10-year financial trend analysis with year-over-year change.")

co = companies()

search = st.text_input(
    "Search company or ticker",
    placeholder="e.g. TCS, Reliance, HDFCBANK"
)

if search.strip():
    term = search.strip().lower()
    matches = co[
        co["company_id"].astype(str).str.lower().str.contains(term, na=False)
        | co["company_name"].astype(str).str.lower().str.contains(term, na=False)
    ].copy()
else:
    matches = co.copy()

if matches.empty:
    st.warning("Company not found — please try another ticker or company name.")
    st.stop()

labels = {
    row.company_id: f"{row.company_id} — {row.company_name}"
    for row in matches.itertuples()
}

ticker = st.selectbox(
    "Select company",
    list(labels.keys()),
    format_func=lambda x: labels[x]
)

ratio = sql_df("""
    SELECT company_id, year,
           net_profit_margin_pct,
           operating_profit_margin_pct,
           return_on_equity_pct,
           interest_coverage,
           asset_turnover,
           free_cash_flow_cr
    FROM financial_ratios
    WHERE UPPER(company_id) = UPPER(?)
    ORDER BY year
""", (ticker,))

if ratio.empty:
    st.warning("No financial ratio history is available for this company.")
    st.stop()

ratio["_year"] = clean_year(ratio["year"])
ratio = ratio.dropna(subset=["_year"]).sort_values("_year").drop_duplicates("_year", keep="last")
ratio = ratio.tail(10).copy()

metric_map = {
    "ROE (%)": "return_on_equity_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Profit Margin (%)": "operating_profit_margin_pct",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
    "Free Cash Flow (₹ Cr)": "free_cash_flow_cr",
}

available = [
    label for label, col in metric_map.items()
    if ratio[col].notna().any()
]

selected = st.multiselect(
    "Select metrics (up to 3)",
    available,
    default=available[:2],
    max_selections=3
)

if not selected:
    st.info("Select at least one metric.")
    st.stop()

fig = go.Figure()

for label in selected:
    col = metric_map[label]
    y = pd.to_numeric(ratio[col], errors="coerce")

    yoy = y.pct_change() * 100
    text = [
        "" if pd.isna(v) else f"YoY {v:+.1f}%"
        for v in yoy
    ]

    fig.add_trace(
        go.Scatter(
            x=ratio["_year"].astype(int),
            y=y,
            mode="lines+markers",
            name=label,
            text=text,
            hovertemplate=(
                "<b>%{x}</b><br>"
                + label
                + ": %{y:.2f}<br>"
                + "%{text}<extra></extra>"
            )
        )
    )

fig.update_layout(
    height=520,
    hovermode="x unified",
    xaxis_title="Fiscal Year",
    yaxis_title="Metric value",
    legend_title="Metrics",
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Year-over-Year Change")

table = ratio[["_year"]].copy()
table["year"] = table["_year"].astype(int)

for label in selected:
    col = metric_map[label]
    values = pd.to_numeric(ratio[col], errors="coerce")
    table[label] = values
    table[f"{label} YoY %"] = values.pct_change() * 100

table = table.drop(columns="_year")
st.dataframe(
    table.round(2),
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download CSV",
    table.to_csv(index=False).encode("utf-8"),
    f"{ticker}_trend_analysis.csv",
    "text/csv"
)
