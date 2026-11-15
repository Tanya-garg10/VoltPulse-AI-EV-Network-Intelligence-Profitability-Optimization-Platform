# ⚡ VoltPulse AI

**EV Network Intelligence & Profitability Optimization Platform**

A production-grade business-intelligence platform for **VoltRelay Energy's**
battery-swapping network across six Indian cities — Bengaluru, Delhi NCR,
Hyderabad, Pune, Mumbai and Jaipur. Built for the **Gradient Learnings Data
Analytics Hackathon**.

VoltPulse AI ingests **3.88 million swap events**, 152 stations, 20,000
riders, 12 fleet partners, 44,000 support tickets and daily city context
(weather, holidays, grid outages, competitor promos) — then converts them
into an executive decision-support system. Not a generic dashboard.

![stack](https://img.shields.io/badge/streamlit-1.3x-red?logo=streamlit)
![python](https://img.shields.io/badge/python-3.11+-blue)
![data](https://img.shields.io/badge/events-3.88M-orange)

---

## Live demo

Deployed on **Streamlit Community Cloud** — the processed Parquet warehouse
is committed to the repo, so the app runs out-of-the-box after `git clone`.

> Local run: `streamlit run app.py` → http://localhost:8501

## What it answers

| Business question | Module |
|---|---|
| Is the network growing profitably? | A — Network Performance |
| Why are swaps failing, and where? | B — Failure Intelligence |
| Why is new-rider retention declining? | C — Rider Retention & Churn |
| Are degraded batteries causing failures? | D — Battery Intelligence |
| Where is margin being eroded? | E — Profitability Analytics |
| Which cities/stations underperform? | F — Geographical Intelligence |
| What should leadership do next? | G — Decision Center |

## Architecture

```
data/raw/*.csv            immutable source files (728 MB events file)
      │
      ▼  src/transformation/build_aggregates.py
      │  chunked (200k rows) → groupby → Parquet rollups
      ▼
data/processed/parquet/  ~14 compact aggregate tables (≈5 MB total)
      │
      ▼  src/database/store.py        cached lazy loads
      ▼  src/analytics/*               modules A–F + ML models
      ▼  src/recommendations/engine.py evidence-backed rules
      ▼
app.py → views/01..08 → premium Streamlit UI
```

**Why aggregates?** The raw fact table is never loaded into the dashboard.
All analytics run on compact Parquet rollups (largest ≈ 62k rows), so pages
render fast and global filters stay cheap. The pipeline is deterministic and
re-runnable; raw data is never modified.

## Quick start

```bash
pip install -r requirements.txt

# Option A — use committed aggregates (dashboard only)
streamlit run app.py

# Option B — rebuild the warehouse from raw CSVs
python -m src.ingestion.profile               # reports/dataset_inventory.csv + data_quality_report.md
python -m src.transformation.build_aggregates # ~3 min → data/processed/parquet/
streamlit run app.py
```

## Dashboard pages

1. **Executive Overview** — attempts, completions, success rate, revenue,
   monthly trends, city comparison, auto-generated insights.
2. **Operations Intelligence** — failure composition, station risk ranking,
   city×hour heatmaps, dow×hour bottlenecks, downtime proxies, weather &
   grid-outage correlations.
3. **Rider Intelligence** — lifecycle segments, churn drivers, cohort
   retention, repeat usage, ML churn-risk scoring (ROC-AUC reported honestly).
4. **Battery Intelligence** — SOH distribution, degradation by age,
   vehicle-class segmentation, failure exposure, utilisation.
5. **Profitability Analytics** — revenue trends, tariff mix, discount
   erosion, city unit economics (estimates clearly labelled), fleet partner
   economics.
6. **City & Station Explorer** — six-city leaderboard, interactive station
   map, filterable station table, underperformer detection.
7. **Decision Center** — prioritised recommendations with evidence and
   quantifiable impact, plus a 30-day demand forecast.
8. **Data Explorer** — table browser, schema/quality inspection, CSV export.

Global filters (cities, date range, stations) apply to every page.

## Project structure

```
voltpulse-ai/
├── app.py                        # router, theme, global filters
├── requirements.txt
├── README.md
├── data_dictionary.md            # full schema documentation
├── .gitignore
├── data/
│   ├── raw/                      # source CSVs (not committed — too large)
│   └── processed/parquet/        # committed aggregates
├── src/
│   ├── config.py  utils.py
│   ├── ingestion/profile.py           # inventory + quality reports
│   ├── transformation/build_aggregates.py
│   ├── database/{store,duckdb_layer}.py
│   ├── analytics/{filters,network,failures,churn,battery,
│   │             profitability,geo,models}.py
│   ├── recommendations/engine.py      # Module G
│   └── ui/theme.py
├── components/ui.py              # design system: KPI cards, charts, callouts
├── views/01..08_*.py             # dashboard pages
├── reports/                      # generated reports + profiling output
├── tests/                        # pytest suite
└── docs/methodology.md           # methodology, limitations, assumptions
```

## Machine learning

- **Rider churn classifier** — HistGradientBoosting on lifetime features;
  stratified 75/25 split, permutation importance, scored risk bands.
- **Station failure-risk model** — RandomForestRegressor; MAE vs
  predict-the-mean baseline reported honestly.
- **Demand forecast** — trend + Fourier annual seasonality + day-of-week;
  evaluated against a seasonal-naive baseline; labelled as model output,
  not observation.

## Data limitations (stated, not hidden)

- **No cost data** — contribution margin uses only amortised station rent +
  maintenance; true margin is unavailable.
- **No battery supplier field** — segmentation uses vehicle class encoded in
  battery IDs.
- **No rider cancellation flag** — churn is operational (30-day inactivity
  + 45-day tenure).
- **Cohort retention** is tenure-based; monthly per-rider activity is not
  stored.
- Full detail in [`docs/methodology.md`](docs/methodology.md).

## Reports

- `reports/dataset_inventory.csv` — file inventory
- `reports/data_quality_report.md` — profiling & quality findings
- `reports/key_findings.md` — headline numbers & recommendations

## Tests

```bash
pytest tests/ -v
```

## Deployment

Works on **Streamlit Community Cloud**, Hugging Face Spaces or any host
running `streamlit run app.py`. The committed Parquet warehouse means no
data upload step is needed.
