import urllib.request
import pandas as pd
import streamlit as st

from src.dashboard.day25_common import sql_df, companies

st.title("Annual Reports")
st.caption("Browse available annual-report records for a selected company.")

co = companies()

search = st.text_input(
    "Search company or ticker",
    placeholder="e.g. TCS, RELIANCE, INFY",
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
    format_func=lambda x: labels[x],
)

# Read the documents schema first. This makes the page tolerant of
# Annual_Report / annual_report / report_url naming differences.
schema = sql_df("PRAGMA table_info(documents)")

if schema.empty:
    st.warning("The documents table is not available.")
    st.stop()

columns = schema["name"].astype(str).tolist()

year_col = next(
    (c for c in columns if c.lower() == "year"),
    next((c for c in columns if "year" in c.lower()), None),
)

report_col = next(
    (
        c for c in columns
        if c.lower() in {
            "annual_report",
            "annual report",
            "report_url",
            "url",
            "pdf_url",
            "annual_report_url",
        }
    ),
    next(
        (
            c for c in columns
            if "report" in c.lower() or c.lower().endswith("_url")
        ),
        None,
    ),
)

if year_col is None:
    st.error(
        "Could not identify the report-year column in the documents table."
    )
    st.stop()

if report_col is None:
    st.error(
        "Could not identify the annual-report URL column in the documents table. "
        f"Available columns: {', '.join(columns)}"
    )
    st.stop()

# Quote identifiers safely because the source column may contain spaces.
def q(identifier):
    return '"' + identifier.replace('"', '""') + '"'

query = f"""
    SELECT
        company_id,
        {q(year_col)} AS report_year,
        {q(report_col)} AS report_url
    FROM documents
    WHERE UPPER(company_id) = UPPER(?)
    ORDER BY {q(year_col)} DESC
"""

docs = sql_df(query, (ticker,))

if docs.empty:
    st.info("No annual-report records are available for this company.")
    st.stop()

def normalize_url(value):
    if pd.isna(value):
        return ""
    url = str(value).strip()
    if not url or url.lower() in {"nan", "none", "null"}:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def check_url(url):
    if not url:
        return "No link"

    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            code = getattr(response, "status", 200)

        if 200 <= code < 400:
            return "Available"
        return "Unavailable"

    except Exception:
        # A timeout, anti-bot block, or HEAD restriction is not proof
        # that the PDF is unavailable.
        return "Link available"

docs["url"] = docs["report_url"].map(normalize_url)

docs["_year"] = pd.to_numeric(
    docs["report_year"]
    .astype(str)
    .str.extract(r"(\d{4})", expand=False),
    errors="coerce",
)

years = sorted(
    docs["_year"].dropna().astype(int).unique().tolist(),
    reverse=True,
)

if years:
    selected_year = st.selectbox(
        "Year filter",
        ["All"] + [str(y) for y in years],
    )

    if selected_year != "All":
        docs = docs[docs["_year"].eq(int(selected_year))].copy()

st.subheader(f"Annual Reports — {ticker}")

for row in docs.itertuples(index=False):
    year = row.report_year
    url = row.url
    status = check_url(url)

    c1, c2, c3 = st.columns([1, 2, 3])

    with c1:
        st.write(f"**{year}**")

    with c2:
        if status == "Available":
            st.success("Available")
        elif status == "Unavailable":
            st.error("Report unavailable")
        elif status == "No link":
            st.warning("No PDF link")
        else:
            st.info("Link available")

    with c3:
        if url:
            st.markdown(f"[Open Annual Report]({url})")
        else:
            st.write("No PDF URL")

st.caption(
    "Source URLs are displayed without modification. Network timeouts and "
    "servers that reject HEAD requests are not treated as proof of a missing report."
)
