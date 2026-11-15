# VoltPulse AI — Methodology, Limitations & Assumptions

## Methodology

### Ingestion & storage
- Raw CSVs are never modified (`data/raw/`).
- `swap_events.csv` (3.88M rows, 728 MB) is processed in 200k-row chunks.
- Per chunk, groupby aggregations are accumulated and written to Parquet:
  - `daily_city`, `daily_city_tariff` — city × date (× tariff)
  - `hourly_city_type` — month × city × hour × event_type
  - `station_daily`, `station_dow_hour` — station-level rollups
  - `rider_profile` — lifetime per-rider metrics (exact distinct-station
    counts via rider×station pair accumulation)
  - `battery_profile` — per-battery SOC/SOH sums & counts (correct weighted
    means across chunks), failure exposure, active window
- Dimension tables (stations, riders, fleet_partners, context, tickets) are
  cleaned (datetime parsing, numeric coercion) and stored as Parquet.

### Metric definitions
- **Attempt** = any swap event row.
- **Completed swap** = `event_type = 'swap_completed'`.
- **Failure** = `failed_no_charged_battery` or `failed_system_error`.
- **Success rate** = completed / attempts.
- **Revenue** = Σ `amount_charged_inr` over completed events.
- **List value** = Σ `list_price_inr`; **Discount** = Σ `discount_inr`.
- **Avg queue** = Σ `queue_wait_sec` / attempts / 60.
- **Station risk score** = 0.5·norm(failure rate) + 0.3·norm(abandon rate)
  + 0.2·norm(avg queue minutes), min-max normalised across stations.

### Churn (operational definition)
No cancellation flag exists. A rider is:
- **churned** — last swap ≥30 days before data end AND first swap ≥45 days
  before data end;
- **at_risk** — recency 8–30 days;
- **active** — recency <8 days;
- **new** — rider age <45 days.

### Machine learning
- **Churn classifier**: HistGradientBoosting on rider lifetime features;
  75/25 stratified split; StandardScaler; permutation importance (3 repeats)
  on the test fold. Metrics reported on held-out data only.
- **Station failure risk**: RandomForestRegressor predicting failure-rate %
  from station volume/cost/capacity features; MAE compared to a
  predict-the-mean baseline.
- **Demand forecast**: OLS on trend + Fourier annual seasonality + day-of-week,
  trained on all but the last 60 days; MAE vs a seasonal-naive (t-7) baseline.
  Forecasts are labelled as model outputs, not observations.

### Recommendations
Rule-based engine: each rule fires only when its measurable threshold is
exceeded by the filtered data; evidence strings quote the actual numbers.
Priority order: Critical → High → Medium → Low.

## Limitations & assumptions

1. **No cost data** — energy procurement, battery capex/lease, charger opex and
   labour costs are absent. "Estimated contribution" subtracts only amortised
   station rent + maintenance and **overstates** true margin.
2. **No battery supplier field** — supplier analysis is limited to vehicle
   class parsed from battery IDs (`BAT-2W-*`, `BAT-3W-*`).
3. **No per-rider monthly activity table** — cohort retention uses swap-tenure
   thresholds as a proxy; riders inactive mid-window but returning later are
   not separately observable.
4. **Battery age** is inferred from first/last observation timestamps, not a
   manufacture/installation date.
5. **Station downtime** is proxied by zero-completion days and context
   `grid_outage_hours`; there is no explicit uptime log.
6. **Weather/calendar** joins at city × date grain only.
7. **DuckDB**: the `duckdb` package could not be installed in this environment
   (disk full). The pipeline and analytics use Pandas/Parquet; an optional
   SQL layer (`src/database/duckdb_layer.py`) activates automatically if
   duckdb is installed.
8. **Attempt-level detail** beyond the aggregates (e.g. individual failed
   event timelines) requires re-scanning the raw CSV; aggregates are the
   analytical contract.
