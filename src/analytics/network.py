"""Module A — Network Performance & Module F — Geographic Intelligence."""
from __future__ import annotations

import pandas as pd

from src.analytics.filters import add_rates, filter_daily_city, monthly
from src.database import store


def network_kpis(cities=None, date_min=None, date_max=None) -> dict:
    dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
    if dc.empty:
        return {}
    attempts = int(dc["attempts"].sum())
    completed = int(dc["completed"].sum())
    failed = int(dc.get("failed_battery", 0).sum() + dc.get("failed_system", 0).sum())
    abandoned = int(dc.get("abandoned", 0).sum())
    cancelled = int(dc.get("cancelled", 0).sum())
    revenue = float(dc["revenue"].sum())
    return {
        "attempts": attempts,
        "completed": completed,
        "failed": failed,
        "abandoned": abandoned,
        "cancelled": cancelled,
        "success_rate": completed / attempts if attempts else 0.0,
        "revenue": revenue,
        "rev_per_swap": revenue / completed if completed else 0.0,
        "list_price_total": float(dc["list_price"].sum()),
        "discount_total": float(dc["discount"].sum()),
        "energy_kwh": float(dc["energy"].sum()),
        "km": float(dc["km"].sum()),
        "active_days": int(dc["date"].nunique()),
    }


def monthly_trend(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = monthly(filter_daily_city(store.get("daily_city"), cities, date_min, date_max))
    g = dc.groupby("month", as_index=False).agg(
        attempts=("attempts", "sum"), completed=("completed", "sum"),
        failed_battery=("failed_battery", "sum"), failed_system=("failed_system", "sum"),
        abandoned=("abandoned", "sum"), cancelled=("cancelled", "sum"),
        revenue=("revenue", "sum"), energy=("energy", "sum"))
    return add_rates(g).sort_values("month")


def daily_activity(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
    g = dc.groupby("date", as_index=False).agg(
        attempts=("attempts", "sum"), completed=("completed", "sum"),
        revenue=("revenue", "sum"))
    return add_rates(g)


def hourly_profile(cities=None, month=None) -> pd.DataFrame:
    h = store.get("hourly_city_type")
    if h.empty:
        return pd.DataFrame()
    if cities:
        h = h[h["city"].isin(cities)]
    if month:
        h = h[h["month"] == month]
    piv = h.pivot_table(index="hour", columns="event_type",
                        values="events", aggfunc="sum", fill_value=0)
    piv["total"] = piv.sum(axis=1)
    return piv.reset_index()


def city_comparison(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
    g = dc.groupby("city", as_index=False).agg(
        attempts=("attempts", "sum"), completed=("completed", "sum"),
        failed_battery=("failed_battery", "sum"), failed_system=("failed_system", "sum"),
        abandoned=("abandoned", "sum"), cancelled=("cancelled", "sum"),
        revenue=("revenue", "sum"), energy=("energy", "sum"),
        discount=("discount", "sum"), list_price=("list_price", "sum"))
    out = add_rates(g)
    out["stations"] = out["city"].map(
        store.get("stations").groupby("city")["station_id"].nunique())
    out["avg_rev_per_swap"] = out["revenue"] / out["completed"].replace(0, pd.NA)
    out = out.sort_values("attempts", ascending=False).reset_index(drop=True)
    out["rank"] = range(1, len(out) + 1)
    return out


def revenue_mix(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Revenue by tariff code requires event-level data; approximated via
    hourly_city_type which keeps event_type only — so compute from daily_city
    is impossible. Return tariff split if a dedicated table exists."""
    return pd.DataFrame()
