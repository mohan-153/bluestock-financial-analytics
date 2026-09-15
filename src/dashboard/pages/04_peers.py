"""Day 24 Peer Comparison screen."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_peer_groups, get_peers

st.title("Peer Comparison")
st.caption("Compare companies within the integrated peer groups.")

groups = get_peer_groups()
if groups.empty:
    st.info("No peer groups are available.")
    st.stop()

group = st.selectbox("Peer group", groups["peer_group_name"].tolist())
df = get_peers(group)

if df.empty:
    st.info("No companies are assigned to this peer group.")
    st.stop()

companies = df["company_id"].dropna().astype(str).unique().tolist()
ticker = st.selectbox("Company", companies)

row = df[df.company_id.eq(ticker)].iloc[0]

# Use available numeric peer metrics. Prefer the Day 17 fields.
metric_map = {
    "ROE": ["roe_pct","return_on_equity_pct","roe"],
    "ROCE": ["roce_pct","return_on_capital_employed_pct","roce"],
    "NPM": ["net_profit_margin_pct","npm_pct"],
    "D/E": ["debt_to_equity","de_pct"],
    "FCF": ["free_cash_flow_cr","fcf"],
    "PAT CAGR 5yr": ["pat_cagr_5yr"],
    "Revenue CAGR 5yr": ["revenue_cagr_5yr"],
    "Asset Turnover": ["asset_turnover"],
}

def first_col(name):
    """Find the first available column for a metric."""
    for col in metric_map[name]:
        if col in df.columns:
            return col
    return None

metrics = []
company_values = []
peer_values = []
for label in metric_map:
    col = first_col(label)
    if col:
        metrics.append(label)
        series = pd.to_numeric(df[col], errors="coerce")
        company_values.append(pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0])
        peer_values.append(series.mean())

if metrics:
    # Lower D/E is better, but the radar displays the raw value for readability.
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=company_values + [company_values[0]],
                                  theta=metrics + [metrics[0]],
                                  fill="toself", name=ticker))
    fig.add_trace(go.Scatterpolar(r=peer_values + [peer_values[0]],
                                  theta=metrics + [metrics[0]],
                                  mode="lines", name="Peer Average"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), height=550)
    st.plotly_chart(fig, width="stretch")

st.subheader("Peer Companies")
st.dataframe(df, width="stretch", hide_index=True)

