import pandas as pd
import streamlit as st
import plotly.express as px

from src.dashboard.day25_common import sql_df, latest_by_company, clean_year

st.title("Sector Analysis")
st.caption("Compare companies within a sector using revenue, ROE and market capitalisation.")

sector_df = sql_df("""
    SELECT
        c.company_id,
        c.company_name,
        s.broad_sector,
        s.sub_sector,
        p.year,
        p.sales,
        r.return_on_equity_pct
    FROM companies c
    LEFT JOIN sectors s ON s.company_id = c.company_id
    LEFT JOIN profitandloss p ON p.company_id = c.company_id
    LEFT JOIN financial_ratios r
        ON r.company_id = c.company_id
        AND r.year = p.year
    WHERE s.broad_sector IS NOT NULL
""")

if sector_df.empty:
    st.warning("Sector data is not available.")
    st.stop()

latest = latest_by_company(
    sector_df[
        [
            "company_id", "company_name", "broad_sector",
            "sub_sector", "year", "sales", "return_on_equity_pct"
        ]
    ],
    "year"
)

# Market-cap data is optional because Day 16 uses calendar-year stock data.
# Do not let missing/invalid market-cap values break Plotly.
try:
    market = sql_df("""
        SELECT company_id, calendar_year, market_cap_crore
        FROM stock_market_analytics
    """)
    market = market.dropna(subset=["market_cap_crore"]).copy()
    if not market.empty:
        market["market_cap_crore"] = pd.to_numeric(
            market["market_cap_crore"], errors="coerce"
        )
        market = market.dropna(subset=["market_cap_crore"])
        market = latest_by_company(market, "calendar_year")
        latest = latest.merge(
            market[["company_id", "market_cap_crore"]],
            on="company_id",
            how="left",
        )
    else:
        latest["market_cap_crore"] = pd.NA
except Exception:
    latest["market_cap_crore"] = pd.NA

sectors = sorted(
    latest["broad_sector"].dropna().astype(str).unique().tolist()
)

if not sectors:
    st.warning("No sectors are available.")
    st.stop()

selected_sector = st.selectbox("Select sector", sectors)

view = latest[
    latest["broad_sector"].astype(str).eq(selected_sector)
].copy()

view["sales"] = pd.to_numeric(view["sales"], errors="coerce")
view["return_on_equity_pct"] = pd.to_numeric(
    view["return_on_equity_pct"], errors="coerce"
)
view["market_cap_crore"] = pd.to_numeric(
    view["market_cap_crore"], errors="coerce"
)

view = view.replace([float("inf"), float("-inf")], pd.NA)

plot_df = view.dropna(
    subset=["sales", "return_on_equity_pct"]
).copy()

if plot_df.empty:
    st.info("No complete Revenue/ROE observations are available for this sector.")
    st.stop()

st.metric("Companies in sector", len(plot_df))

# Use a constant marker size when market cap is unavailable.
# This prevents Plotly's marker-size validator from receiving NaN/inf.
has_market_cap = (
    plot_df["market_cap_crore"].notna().any()
    and (plot_df["market_cap_crore"] > 0).any()
)

if has_market_cap:
    plot_df["plot_market_cap"] = plot_df["market_cap_crore"].fillna(
        plot_df["market_cap_crore"].median()
    ).clip(lower=1)
    size_arg = "plot_market_cap"
else:
    plot_df["plot_market_cap"] = 12
    size_arg = "plot_market_cap"

plot_df["sub_sector"] = (
    plot_df["sub_sector"]
    .fillna("Unknown")
    .astype(str)
    .replace({"": "Unknown"})
)

fig = px.scatter(
    plot_df,
    x="sales",
    y="return_on_equity_pct",
    size=size_arg,
    color="sub_sector",
    hover_name="company_name",
    hover_data={
        "company_id": True,
        "sales": ":,.2f",
        "return_on_equity_pct": ":.2f",
        "market_cap_crore": ":,.2f",
        "sub_sector": True,
        size_arg: False,
    },
    labels={
        "sales": "Revenue (₹ Cr)",
        "return_on_equity_pct": "ROE (%)",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "sub_sector": "Sub-sector",
    },
    title=f"{selected_sector} — Revenue vs ROE",
)

fig.update_layout(height=560)
st.plotly_chart(fig, width="stretch")

st.subheader("Sector Median KPI")

median_df = pd.DataFrame({
    "Metric": ["Revenue (₹ Cr)", "ROE (%)"],
    "Median": [
        plot_df["sales"].median(),
        plot_df["return_on_equity_pct"].median(),
    ],
})

bar = px.bar(
    median_df,
    x="Metric",
    y="Median",
    text="Median",
    title=f"{selected_sector} — Median KPIs",
)
bar.update_traces(texttemplate="%{text:.2f}", textposition="outside")
bar.update_layout(height=400)
st.plotly_chart(bar, width="stretch")

st.subheader("Companies in Sector")

display = plot_df[
    [
        "company_id",
        "company_name",
        "sub_sector",
        "sales",
        "return_on_equity_pct",
        "market_cap_crore",
    ]
].sort_values("return_on_equity_pct", ascending=False)

st.dataframe(
    display.round(2),
    width="stretch",
    hide_index=True,
)

