# VoltPulse AI — Data Dictionary

Simulated EV battery-swapping network operated by **VoltRelay Energy** across six
Indian cities. Events span **2024-01-01 → 2025-06-30** (~3.88M swap events).

## swap_events (`swap_events.csv`) — fact table, ~3.88M rows

One row per swap *attempt* (a rider may retry; `attempt_seq` > 1 indicates a retry).

| Column | Type | Description |
|---|---|---|
| event_id | string | PK, `SW-#########` |
| rider_id | string | FK → riders.rider_id |
| station_id | string | FK → stations.station_id |
| event_ts | timestamp | Event time (local) |
| event_type | string | `swap_completed`, `failed_no_charged_battery`, `failed_system_error`, `abandoned_queue`, `cancelled_by_rider` |
| attempt_seq | int | Attempt number for this rider/station session |
| queue_wait_sec | int | Seconds spent in queue (may be null) |
| battery_in_id | string | Battery returned by rider (`BAT-<class>-<n>`) |
| battery_out_id | string | Charged battery handed to rider |
| soc_in_pct / soc_out_pct | float | State of charge % on return / on dispatch |
| soh_in_pct / soh_out_pct | float | State of health % (degradation proxy) |
| km_since_last_swap | float | Distance ridden since rider's previous swap |
| tariff_code | string | `STD`, `PEAK`, `OFFPEAK`, `PARTNER` |
| list_price_inr | float | Pre-discount price |
| discount_inr | float | Discount amount |
| amount_charged_inr | float | Final amount (0/absent on failures) |
| payment_mode | string | e.g. `partner_invoice`, UPI/card |
| energy_to_recharge_kwh | float | Energy delivered to battery |
| station_firmware | string | Firmware version at station |
| sync_mode | string | `realtime` / `offline_batch` |

## stations (`stations.csv`) — 152 stations

`station_id` PK (`STN-<CITY>-###`), `city`, `zone`, `latitude`, `longitude`,
`location_type`, `host_type`, `commissioned_date`, `decommissioned_date`,
`expansion_wave`, `charger_generation` (Gen1/Gen2), `slots_2w`, `slots_3w`,
`inventory_target_2w/3w`, `monthly_rent_inr`, `monthly_maintenance_inr`,
`grid_tariff_inr_kwh`, `connectivity_tier` (good/poor), `firmware_version`,
`firmware_updated_date`, `competitor_within_1_5km_since`.

## riders (`riders.csv`) — 20,000 riders

`rider_id` PK (`RD-#######`), `partner_id` FK, `vehicle_class` (2W/3W),
`vehicle_model`, `home_zone`, `signup_date`, `signup_channel`, `plan_type`,
`declared_shift`, `age_band`, `kyc_verified`, `home_city`.

## fleet_partners (`fleet_partners.csv`) — 12 partners

`partner_id` PK (`FP-##`), `partner_name`, `partner_segment`, `vehicle_class`,
`contract_type`, `contract_start_date`, `discount_pct`,
`amendment_date`, `discount_pct_after_amendment`, `peak_surcharge_billable`,
`payment_terms_days`, `cities_active` (`|`-delimited).

## support_tickets (`support_tickets.csv`) — 44,000 tickets

`ticket_id` PK, `rider_id`, `station_id`, `battery_id` (sparse), `created_ts`,
`channel`, `category`, `rider_comment`, `priority`, `resolution_status`,
`resolution_hours`, `csat_score`.

## city_daily_context (`city_daily_context.csv`) — 3,282 city-days

`city`, `date`, `max_temp_c`, `min_temp_c`, `rainfall_mm`, `heat_alert`,
`flood_disruption`, `festival_or_event`, `is_public_holiday`,
`grid_outage_hours`, `competitor_promo_active`, `ecommerce_sale_event`.

## Derived Parquet tables (`data/processed/parquet/`)

| Table | Grain | Contents |
|---|---|---|
| daily_city | city × date | attempts, completed, failure-type counts, retries, revenue, list price, discount, energy, queue seconds, km |
| hourly_city_type | month × city × hour × event_type | event counts + revenue |
| station_daily | station × date | same metrics as daily_city at station grain |
| station_dow_hour | station × dow × hour | attempts/completed/failures/queue — bottleneck patterns |
| rider_profile | rider | lifetime events, completions, failure counts, revenue split (partner vs retail), first/last swap, energy, km, distinct stations |
| battery_profile | battery | swaps in/out, SOC/SOH means & minima, failure exposure, energy, active window, vehicle class parsed from ID |
| stations / riders / fleet_partners / city_daily_context / support_tickets | dimension copies | cleaned versions of raw files |

## Churn definition (operational)

A rider is **churned** if their last observed swap is ≥30 days before the
data end date AND they were first seen ≥45 days before data end (excludes
new riders still in their trial window). **At-risk** riders have recency
8–30 days. See `src/analytics/churn.py`.
