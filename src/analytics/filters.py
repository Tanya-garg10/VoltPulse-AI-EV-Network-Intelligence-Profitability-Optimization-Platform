"""Shared filter helpers for analytics functions."""
from __future__ import annotations

import pandas as pd


def filter_daily_city(df: pd.DataFrame, cities: list[str] | None = None,
                      date_min: str | None = None, date_max: str | None = None
                      ) -> pd.DataFrame:
    out = df
    if cities:
        out = out[out["city"].isin(cities)]
    if date_min:
        out = out[out["date"] >= str(date_min)]
    if date_max:
        out = out[out["date"] <= str(date_max)]
    return out


def filter_station_daily(df: pd.DataFrame, station_ids: list[str] | None = None,
                         cities: list[str] | None = None,
                         station_city: pd.DataFrame | None = None,
                         date_min: str | None = None,
                         date_max: str | None = None) -> pd.DataFrame:
    out = df
    if station_ids:
        out = out[out["station_id"].isin(station_ids)]
    elif cities and station_city is not None:
        valid = station_city.loc[station_city["city"].isin(cities), "station_id"]
        out = out[out["station_id"].isin(set(valid))]
    if date_min:
        out = out[out["date"] >= str(date_min)]
    if date_max:
        out = out[out["date"] <= str(date_max)]
    return out


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Add success/failure rate columns to an events-aggregate frame."""
    out = df.copy()
    out["success_rate"] = out["completed"] / out["attempts"].replace(0, pd.NA)
    out["battery_fail_rate"] = out.get("failed_battery", 0) / out["attempts"].replace(0, pd.NA)
    out["system_fail_rate"] = out.get("failed_system", 0) / out["attempts"].replace(0, pd.NA)
    out["abandon_rate"] = out.get("abandoned", 0) / out["attempts"].replace(0, pd.NA)
    out["rev_per_swap"] = out["revenue"] / out["completed"].replace(0, pd.NA)
    out["avg_queue_min"] = (out.get("queue_sum", 0) / out["attempts"].replace(0, pd.NA)) / 60.0
    return out


def monthly(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    d = df.copy()
    d["month"] = pd.to_datetime(d[date_col]).dt.to_period("M").astype(str)
    return d
