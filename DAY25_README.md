# Bluestock Day 25 Implementation

Implements the four Day 25 dashboard screens from the Nifty 100 project specification:

- `pages/05_trends.py` — Trend Analysis
- `pages/06_sectors.py` — Sector Analysis
- `pages/07_capital.py` — Capital Allocation Map
- `pages/08_reports.py` — Annual Reports
- `day25_common.py` — shared SQLite/data helpers

## Install
The project already uses Streamlit and Plotly. No database schema changes are required for these pages.

## Run
```powershell
streamlit run src/dashboard/app.py
```

## Notes
- Trend Analysis overlays up to 3 metrics and shows YoY percentage change.
- Sector Analysis uses Revenue vs ROE bubble chart; bubble size is market cap when available.
- Capital Allocation classifies the latest CFO/CFI/CFF sign pattern into 8 descriptive categories.
- Annual Reports reads the existing `documents` table and keeps source URLs unchanged.
