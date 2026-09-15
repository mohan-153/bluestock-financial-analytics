# Bluestock Day 24 — Screener & Peer Comparison

Implemented:
- 10 screener controls
- Preset definitions for Quality Compounder, Value Pick, Growth Accelerator,
  Dividend Champion, Debt-Free Blue Chip, and Turnaround Watch
- Financial-sector D/E bypass
- Debt-Free ICR bypass
- Composite quality score when source metrics are available
- Ranked result table
- CSV export
- Peer group selector
- Company vs peer-average radar chart
- Peer company table

Run:
```powershell
streamlit run src/dashboard/app.py
```

If needed:
```powershell
pip install plotly
```
