import pandas as pd
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_financial_ratios_all,
    get_profit_loss_all,
    get_market_all,
)

from src.screener.engine import (
    PRESETS,
    build_screener_universe,
    apply_filters,
)


# =========================================================
# PAGE
# =========================================================

st.title("Screener")
st.caption(
    "Filter the Nifty 100 using financial, growth and valuation metrics."
)


# =========================================================
# LOAD DATA
# =========================================================

try:
    companies = get_companies()
    ratios = get_financial_ratios_all()
    profit_loss = get_profit_loss_all()
    market = get_market_all()

    universe = build_screener_universe(
        companies,
        ratios,
        profit_loss,
        market,
    )

except Exception as exc:
    st.error(f"Unable to build screener data: {exc}")
    st.stop()


if universe.empty:
    st.warning("No screener data is available.")
    st.stop()


# =========================================================
# PRESET SELECTOR
# =========================================================

st.sidebar.subheader("Preset Screeners")

preset = st.sidebar.selectbox(
    "Choose preset",
    ["Custom"] + list(PRESETS.keys()),
)


# =========================================================
# FILTER VALUES
# =========================================================
#
# IMPORTANT:
# For a preset, ONLY values explicitly defined in PRESETS
# are passed to apply_filters().
#
# This prevents inactive/default filters from accidentally
# changing the preset result.
# =========================================================

filters = {}


if preset == "Custom":

    st.sidebar.subheader("Filters")

    filters["min_roe"] = st.sidebar.slider(
        "ROE minimum (%)",
        min_value=0.0,
        max_value=50.0,
        value=0.0,
    )

    filters["max_de"] = st.sidebar.slider(
        "D/E maximum",
        min_value=0.0,
        max_value=10.0,
        value=10.0,
    )

    filters["min_fcf"] = st.sidebar.number_input(
        "FCF minimum (₹ Cr)",
        value=-1000000000.0,
    )

    filters["min_rev_cagr_5yr"] = st.sidebar.slider(
        "Revenue CAGR 5yr minimum (%)",
        min_value=-50.0,
        max_value=50.0,
        value=-50.0,
    )

    filters["min_pat_cagr_5yr"] = st.sidebar.slider(
        "PAT CAGR 5yr minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        value=-50.0,
    )

    filters["min_opm"] = st.sidebar.slider(
        "OPM minimum (%)",
        min_value=0.0,
        max_value=60.0,
        value=0.0,
    )

    filters["max_pe"] = st.sidebar.number_input(
        "P/E maximum",
        value=1000000.0,
    )

    filters["max_pb"] = st.sidebar.number_input(
        "P/B maximum",
        value=1000000.0,
    )

    filters["min_dividend_yield"] = st.sidebar.slider(
        "Dividend Yield minimum (%)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
    )

    filters["min_icr"] = st.sidebar.slider(
        "ICR minimum",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
    )


else:

    # -----------------------------------------------------
    # PRESET MODE
    # -----------------------------------------------------

    preset_values = PRESETS.get(preset, {})

    # Only explicitly defined preset rules are active.
    filters = {
        key: value
        for key, value in preset_values.items()
        if value is not None
    }

    st.sidebar.subheader("Active Preset Rules")

    # Human-readable labels for the preset summary.
    labels = {
        "min_roe": ("ROE", "≥", "%"),
        "max_de": ("D/E", "≤", ""),
        "min_fcf": ("FCF", "≥ ₹", " Cr"),
        "min_rev_cagr_5yr": ("Revenue CAGR 5yr", "≥", "%"),
        "min_pat_cagr_5yr": ("PAT CAGR 5yr", "≥", "%"),
        "min_opm": ("OPM", "≥", "%"),
        "max_pe": ("P/E", "≤", ""),
        "max_pb": ("P/B", "≤", ""),
        "min_dividend_yield": ("Dividend Yield", "≥", "%"),
        "min_icr": ("ICR", "≥", ""),
        "max_dividend_payout": ("Dividend Payout", "≤", "%"),
        "min_sales": ("Sales", "≥ ₹", " Cr"),
        "min_rev_cagr_3yr": ("Revenue CAGR 3yr", "≥", "%"),
    }

    # Show all supported conditions so the user can clearly
    # see which ones are active and which are not applied.
    supported_keys = [
        "min_roe",
        "max_de",
        "min_fcf",
        "min_rev_cagr_5yr",
        "min_pat_cagr_5yr",
        "min_opm",
        "max_pe",
        "max_pb",
        "min_dividend_yield",
        "min_icr",
        "max_dividend_payout",
        "min_sales",
        "min_rev_cagr_3yr",
    ]

    active_lines = []

    for key in supported_keys:

        label, operator, suffix = labels[key]

        if key in filters:

            value = filters[key]

            # Currency-style values
            if key in {
                "min_fcf",
                "min_sales",
            }:
                text = f"{label} {operator} ₹{float(value):,.2f}{suffix}"

            else:
                text = f"{label} {operator} {float(value):,.2f}{suffix}"

            active_lines.append(f"**{text}**")

        else:
            active_lines.append(
                f"**{label}:** Not applied"
            )

    st.sidebar.info(
        f"**{preset}**\n\n"
        + "\n\n".join(active_lines)
    )


# =========================================================
# APPLY FILTERS
# =========================================================

try:

    result = apply_filters(
        universe,
        **filters,
    )

except Exception as exc:

    st.error(
        f"Unable to apply screener filters: {exc}"
    )
    st.stop()


# =========================================================
# RESULT COUNT
# =========================================================

st.subheader(
    f"{len(result)} companies match your filters"
)


# =========================================================
# RESULT TABLE
# =========================================================

show_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]


show_columns = [
    column
    for column in show_columns
    if column in result.columns
]


display_df = result[show_columns].copy()


# ---------------------------------------------------------
# Format numeric columns
# ---------------------------------------------------------

text_columns = {
    "company_id",
    "company_name",
    "broad_sector",
}


for column in display_df.columns:

    if column not in text_columns:

        display_df[column] = pd.to_numeric(
            display_df[column],
            errors="coerce",
        ).round(2)


st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
)


# =========================================================
# DOWNLOAD
# =========================================================

csv_data = display_df.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name="screener_results.csv",
    mime="text/csv",
)


# =========================================================
# DATA NOTE
# =========================================================

st.caption(
    "Preset screeners apply only their defined conditions. "
    "Inactive conditions are not applied. CAGR values are "
    "derived from the available fiscal-year history."
)

