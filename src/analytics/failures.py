"""Module B — Failure Intelligence."""
from __future__ import annotations

import pandas as pd

from src.analytics.filters import (add_rates, filter_daily_city,
                                   filter_station_daily, monthly)
from src.database import store


def station_failure_table(cities=None, date_min=None, date_max=None,
                          min_attempts=30) -> pd.DataFrame:
    sd = filter_station_daily(store.get("station_daily"), cities=cities,
                              station_city=store.get("station_city"),
                              date_min=date_min, date_max=date_max)
    if sd.empty:
        return pd.DataFrame()
    g = sd.groupby("station_id", as_index=False).agg(
        attempts=("attempts", "sum"), completed=("completed", "sum"),
        failed_battery=("failed_battery", "sum"), failed_system=("failed_system", "sum"),
        abandoned=("abandoned", "sum"), cancelled=("cancelled", "sum"),
        retries=("retries", "sum"), revenue=("revenue", "sum"),
        queue_sum=("queue_sum", "sum"), energy=("energy", "sum"),
        active_days=("date", "nunique"))
    g = g[g["attempts"] >= min_attempts].copy()
    g = add_rates(g)
    st = store.get("stations")
    g = g.merge(st[["station_id", "city", "zone", "location_type",
                    "host_type", "connectivity_tier", "charger_generation",
                    "slots_2w", "slots_3w", "latitude", "longitude",
                    "monthly_rent_inr", "monthly_maintenance_inr",
                    "grid_tariff_inr_kwh"]], on="station_id", how="left")
    g["failure_rate"] = g["failed_battery"] + g["failed_system"]
    g["failure_rate"] = g["failure_rate"] / g["attempts"]
    g["total_failures"] = g["failed_battery"] + g["failed_system"]
    g["fail_share_battery"] = g["failed_battery"] / g["total_failures"].replace(0, pd.NA)
    g["failures_per_day"] = g["total_failures"] / g["active_days"].replace(0, pd.NA)
    g["rev_per_attempt"] = g["revenue"] / g["attempts"].replace(0, pd.NA)
    # composite risk score: failure rate + abandon rate + queue time, normalized
    for col in ["failure_rate", "abandon_rate", "avg_queue_min"]:
        g[f"{col}_n"] = (g[col] - g[col].min()) / (g[col].max() - g[col].min() + 1e-9)
    g["risk_score"] = (0.5 * g["failure_rate_n"] + 0.3 * g["abandon_rate_n"]
                       + 0.2 * g["avg_queue_min_n"]).round(3)
    return g.sort_values("risk_score", ascending=False).reset_index(drop=True)


def failure_heatmap(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Avg failure rate by city x hour-of-day."""
    h = store.get("hourly_city_type")
    if h.empty:
        return pd.DataFrame()
    if cities:
        h = h[h["city"].isin(cities)]
    if date_min or date_max:
        h = h[(h["month"] >= str(date_min)[:7] if date_min else True) &
              (h["month"] <= str(date_max)[:7] if date_max else True)]
    piv = h.pivot_table(index="hour", columns="city", values="events",
                        aggfunc="sum", fill_value=0)
    return piv


def hourly_failure_pattern(cities=None) -> pd.DataFrame:
    """Failure share by hour across network."""
    h = store.get("hourly_city_type")
    if h.empty:
        return pd.DataFrame()
    if cities:
        h = h[h["city"].isin(cities)]
    fails = h[h["event_type"].str.startswith(("failed", "abandoned"))]
    tot = h.groupby("hour", as_index=False)["events"].sum().rename(
        columns={"events": "total"})
    f = fails.groupby("hour", as_index=False)["events"].sum().rename(
        columns={"events": "failures"})
    out = tot.merge(f, on="hour", how="left").fillna({"failures": 0})
    out["failure_rate"] = out["failures"] / out["total"].replace(0, pd.NA)
    return out.sort_values("hour")


def battery_vs_system_failures(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = monthly(filter_daily_city(store.get("daily_city"), cities, date_min, date_max))
    g = dc.groupby("month", as_index=False).agg(
        battery=("failed_battery", "sum"), system=("failed_system", "sum"),
        abandoned=("abandoned", "sum"), cancelled=("cancelled", "sum"),
        completed=("completed", "sum"), attempts=("attempts", "sum"))
    return g


def downtime_analysis(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Proxy for station downtime: days with zero completed swaps per station,
    plus grid outage hours from context."""
    sd = filter_station_daily(store.get("station_daily"), cities=cities,
                              station_city=store.get("station_city"),
                              date_min=date_min, date_max=date_max)
    if sd.empty:
        return pd.DataFrame()
    g = sd.groupby(["station_id", "date"], as_index=False).agg(
        completed=("completed", "sum"), attempts=("attempts", "sum"))
    zero_days = g[g["completed"] == 0]
    per_station = zero_days.groupby("station_id").size().rename("zero_swap_days")
    attempts_per_station = sd.groupby("station_id")["attempts"].sum()
    out = pd.DataFrame({"zero_swap_days": per_station,
                        "total_attempts": attempts_per_station}).reset_index()
    out["zero_day_rate"] = out["zero_swap_days"] / (
        out["total_attempts"] / out["total_attempts"].median() + 1e-9)
    st = store.get("stations")[["station_id", "city"]]
    return out.merge(st, on="station_id", how="left").sort_values(
        "zero_swap_days", ascending=False)


def context_correlations(cities=None) -> pd.DataFrame:
    """Correlate city-day context (temp, rain, outages) with failure rates."""
    cx = store.get("city_daily_context")
    dc = store.get("daily_city")
    if cx.empty or dc.empty:
        return pd.DataFrame()
    dc = dc.copy()
    dc["date"] = pd.to_datetime(dc["date"])
    dc["fail_rate"] = (dc["failed_battery"] + dc["failed_system"]) / dc["attempts"].replace(0, pd.NA)
    dc["month"] = dc["date"].dt.to_period("M").astype(str)
    daily = dc.groupby(["city", "date"], as_index=False).agg(
        fail_rate=("fail_rate", "mean"), attempts=("attempts", "sum"))
    m = daily.merge(cx, on=["city", "date"], how="inner")
    if cities:
        m = m[m["city"].isin(cities)]
    cols = ["max_temp_c", "min_temp_c", "rainfall_mm", "heat_alert",
            "grid_outage_hours", "competitor_promo_active",
            "is_public_holiday", "fail_rate", "attempts"]
    m["heat_alert"] = m["heat_alert"].astype(int)
    m["competitor_promo_active"] = m["competitor_promo_active"].astype(int)
    m["is_public_holiday"] = m["is_public_holiday"].astype(int)
    corr = m[cols].corr(numeric_only=True)["fail_rate"].drop("fail_rate")
    return corr.reset_index().rename(columns={"index": "feature", "fail_rate": "correlation"})
