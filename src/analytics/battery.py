"""Module D — Battery Intelligence."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.database import store


def battery_table() -> pd.DataFrame:
    b = store.get("battery_profile")
    if b.empty:
        return pd.DataFrame()
    df = b.copy()
    df["first_ts"] = pd.to_datetime(df["first_ts"], errors="coerce")
    df["last_ts"] = pd.to_datetime(df["last_ts"], errors="coerce")
    df["active_days"] = (df["last_ts"] - df["first_ts"]).dt.days.clip(lower=0)
    df["swaps_total"] = df[["swaps_in", "swaps_out"]].fillna(0).sum(axis=1)
    # degradation proxy: min SOH observed vs max SOH observed (SOH declines over life)
    df["soh_min"] = df[["min_soh_in", "min_soh_out"]].min(axis=1)
    df["soh_mean"] = df[["avg_soh_in", "avg_soh_out"]].mean(axis=1)
    df["failure_rate"] = df["failure_events"].fillna(0) / df["swaps_total"].replace(0, np.nan)
    df["utilization"] = df["swaps_total"] / (df["active_days"] + 1)
    return df


def health_distribution() -> pd.DataFrame:
    df = battery_table()
    if df.empty:
        return pd.DataFrame()
    bins = [0, 80, 85, 90, 95, 100, 105, 200]
    labels = ["<80", "80-85", "85-90", "90-95", "95-100", "100-105", ">105"]
    df["soh_band"] = pd.cut(df["soh_mean"], bins=bins, labels=labels)
    return (df.groupby("soh_band", observed=True)
            .agg(batteries=("battery_id", "nunique"),
                 avg_swaps=("swaps_total", "mean"),
                 failure_rate=("failure_rate", "mean"))
            .reset_index())


def degradation_by_age() -> pd.DataFrame:
    """SOH vs battery age (days since first seen)."""
    df = battery_table()
    if df.empty:
        return pd.DataFrame()
    end = store.data_end_date()
    df["age_days"] = (end - df["first_ts"]).dt.days
    df["age_band"] = pd.cut(df["age_days"], bins=[0, 90, 180, 365, 730, 5000],
                            labels=["<3m", "3-6m", "6-12m", "1-2y", "2y+"])
    return (df.groupby("age_band", observed=True)
            .agg(batteries=("battery_id", "nunique"),
                 avg_soh=("soh_mean", "mean"),
                 avg_min_soh=("soh_min", "mean"),
                 failure_rate=("failure_rate", "mean"))
            .reset_index())


def supplier_performance() -> pd.DataFrame:
    """Battery 'supplier' is not an explicit field; vehicle_class parsed from
    battery_id (BAT-2W-/BAT-3W-) is the available segmentation."""
    df = battery_table()
    if df.empty:
        return pd.DataFrame()
    return (df.groupby("vehicle_class", dropna=False)
            .agg(batteries=("battery_id", "nunique"),
                 avg_soh=("soh_mean", "mean"),
                 avg_swaps=("swaps_total", "mean"),
                 failure_rate=("failure_rate", "mean"),
                 avg_utilization=("utilization", "mean"))
            .reset_index())


def battery_failure_link() -> pd.DataFrame:
    """SOH bands vs failure exposure."""
    df = battery_table()
    if df.empty:
        return pd.DataFrame()
    df["soh_band"] = pd.cut(df["soh_mean"], bins=[0, 85, 90, 95, 100, 105, 200],
                            labels=["<85", "85-90", "90-95", "95-100", "100-105", ">105"])
    return (df.groupby("soh_band", observed=True)
            .agg(batteries=("battery_id", "nunique"),
                 failure_events=("failure_events", "sum"),
                 swaps=("swaps_total", "sum"),
                 failure_rate=("failure_rate", "mean"))
            .reset_index())


def utilization_distribution() -> pd.DataFrame:
    df = battery_table()
    if df.empty:
        return pd.DataFrame()
    df["util_band"] = pd.qcut(df["utilization"].clip(upper=df["utilization"].quantile(0.99)),
                              q=5, labels=["Q1 (low)", "Q2", "Q3", "Q4", "Q5 (high)"],
                              duplicates="drop")
    return (df.groupby("util_band", observed=True)
            .agg(batteries=("battery_id", "nunique"),
                 avg_soh=("soh_mean", "mean"),
                 failure_rate=("failure_rate", "mean"))
            .reset_index())
