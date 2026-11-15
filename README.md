# VoltPulse AI

**EV Network Intelligence & Profitability Optimization Platform**

A production-grade business-intelligence platform for **VoltRelay Energy's**
battery-swapping network across six Indian cities (Bengaluru, Delhi NCR,
Hyderabad, Pune, Mumbai, Jaipur). Built for the Gradient Learnings Data
Analytics Hackathon.

VoltPulse AI ingests **3.88 million swap events**, 152 stations, 20,000
riders, 12 fleet partners and 44,000 support tickets, then transforms them
into an executive decision-support system — not a generic dashboard.

---

## What it answers

| Business question | Module |
|---|---|
| Is the network growing profitably? | A — Network Performance |
| Why are swaps failing, and where? | B — Failure Intelligence |
| Why is new-rider retention declining? | C — Rider Retention & Churn |
| Are batteries degrading into failures? | D — Battery Intelligence |
| Where is margin being eroded? | E — Profitability Analytics |
| Which cities/stations underperform? | F — Geographical Intelligence |
| What should leadership do next? | G — Decision Center |

## Architecture

```
data/raw/*.csv  (immutable, 728 MB events file)
      │
      ▼  src/transformation/build_aggregates.py
      │  chunked (200k rows) → groupby aggregation → Parquet
      ▼
data/processed/parquet/*.parquet   (~10 small aggregate tables)
      │
      ▼  src/database/store.py  (lazy, cached loads)
      ▼
src/analytics/*  (modules A–F)  +  src/analytics/models.py (ML)
      │
      ▼  src/recommendations/engine.py  (rule-based, evidence-backed)
      ▼
app.py  →  pages/01..08  →  Streamlit UI
```

**Why aggregates?** The raw fact table is never loaded into the dashboard.
All analytics run on compact Parquet rollups (largest ≈ 62k rows), so every
page renders in milliseconds and filters stay cheap.

## Setup

```bash
pip install -r requirements.txt
python -m src.ingestion.profile                  # optional: refresh reports
python -m src.transformation.build_aggregates    # build Parquet warehouse (~3 min)
streamlit run app.py
```

## Project structure

```
voltpulse-ai/
├── app.py                     # router, theme, global filters
├── requirements.txt
├── data_dictionary.md         # full schema documentation
├── data/{raw,processed,warehouse}/
├── src/
│   ├── config.py  utils.py
│   ├── ingestion/profile.py        # inventory + quality reports
│   ├── transformation/build_aggregates.py
│   ├── database/store.py           # cached Parquet loader
│   ├── analytics/{filters,network,failures,churn,battery,
│   │             profitability,geo,models}.py
│   ├── recommendations/engine.py   # Module G
│   └── ui/theme.py
├── components/ui.py            # KPI cards, chart helpers, design system
├── views/01..08_*.py           # dashboard pages
├── reports/                    # generated reports + profiling output
├── tests/
└── docs/
```

## Dashboard pages

1. **Executive Overview** — attempts, completions, success rate, revenue,
   monthly trends, city comparison, auto-insights.
2. **Operations Intelligence** — failure composition, station risk ranking,
   city×hour heatmaps, dow×hour bottlenecks, downtime proxies, weather/grid
   correlations.
3. **Rider Intelligence** — lifecycle segments, churn drivers, cohort
   retention, repeat usage, ML churn-risk scoring (ROC-AUC reported honestly).
4. **Battery Intelligence** — SOH distribution, degradation by age,
   vehicle-class segmentation, failure exposure, utilisation.
5. **Profitability Analytics** — revenue trends, tariff mix, discount
   erosion, city unit economics (estimates clearly labelled), fleet partner
   economics.
6. **City & Station Explorer** — six-city leaderboard, interactive station
   map (lat/lon), filterable station table, underperformer list.
7. **Decision Center** — prioritised recommendations with evidence and
   quantifiable impact, plus a 30-day demand forecast.
8. **Data Explorer** — table browser, schema/quality inspection, CSV export.

## Data limitations (stated, not hidden)

- **No cost data**: contribution margin uses only amortised station rent +
  maintenance; true margin is unavailable.
- **No battery supplier field**: battery segmentation uses vehicle class
  encoded in battery IDs.
- **No rider cancellation flag**: churn is defined operationally (30-day
  inactivity + 45-day tenure).
- **Cohort retention** is tenure-based (monthly activity per rider is not
  stored); documented on the page.

## Tests

```bash
pytest tests/ -v
```
