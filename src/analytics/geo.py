"""Module F — Geographical Intelligence: rankings, maps, station explorer."""
from __future__ import annotations

import pandas as pd

from src.analytics.failures import station_failure_table
from src.analytics.filters import add_rates, filter_station_daily
from src.database import store


def station_rankings(cities=None, date_min=None, date_max=None,
                     sort_by="risk_score") -> pd.DataFrame:
    return station_failure_table(cities, date_min, date_max)


def station_metrics(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Per-station KPI frame for maps/tables."""
    t = station_failure_table(cities, date_min, date_max, min_attempts=1)
    if t.empty:
        return pd.DataFrame()
    keep = ["station_id", "city", "zone", "latitude", "longitude",
            "location_type", "host_type", "connectivity_tier",
            "charger_generation", "slots_2w", "slots_3w",
            "attempts", "completed", "success_rate", "failure_rate",
            "abandon_rate", "avg_queue_min", "revenue", "rev_per_swap",
            "risk_score", "active_days", "failures_per_day"]
    return t[[c for c in keep if c in t.columns]]


def city_ranking(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    from src.analytics.network import city_comparison
    return city_comparison(cities, date_min, date_max)


def underperformers(cities=None, date_min=None, date_max=None,
                    n=15) -> pd.DataFrame:
    t = station_failure_table(cities, date_min, date_max)
    if t.empty:
        return pd.DataFrame()
    return t.head(n)


def utilization_by_station(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Attempts per slot per day — capacity pressure proxy."""
    t = station_failure_table(cities, date_min, date_max, min_attempts=1)
    if t.empty:
        return pd.DataFrame()
    t = t.copy()
    t["slots"] = t["slots_2w"].fillna(0) + t["slots_3w"].fillna(0)
    t["attempts_per_slot_day"] = t["attempts"] / (t["slots"].replace(0, pd.NA) * t["active_days"].replace(0, pd.NA))
    return t.sort_values("attempts_per_slot_day", ascending=False)
