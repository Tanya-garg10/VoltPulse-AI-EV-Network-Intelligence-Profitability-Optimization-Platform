"""Module C — Rider Retention & Churn.

Operational churn definition:
  churned  = last swap >= 30 days before data end AND rider is >= 45 days old
             (first swap >= 45 days before data end)
  at_risk  = recency 8-30 days
  active   = recency < 8 days
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.filters import add_rates
from src.database import store

CHURN_DAYS = 30
MIN_AGE_DAYS = 45
AT_RISK_DAYS = 8


def rider_table() -> pd.DataFrame:
    rp = store.get("rider_profile")
    rd = store.get("riders")
    if rp.empty:
        return pd.DataFrame()
    df = rp.merge(rd, on="rider_id", how="left")
    end = store.data_end_date()
    df["last_ts"] = pd.to_datetime(df["last_ts"])
    df["first_ts"] = pd.to_datetime(df["first_ts"])
    df["recency_days"] = (end - df["last_ts"]).dt.days
    df["tenure_days"] = (df["last_ts"] - df["first_ts"]).dt.days
    df["age_days"] = (end - df["first_ts"]).dt.days
    df["swaps_per_week"] = df["completed"] / (df["tenure_days"].clip(lower=1) / 7.0)
    df["failure_rate"] = (df["failed_battery"] + df["failed_system"]) / df["events"].replace(0, np.nan)
    df["rev_per_swap"] = df["revenue"] / df["completed"].replace(0, np.nan)
    df["avg_queue_min"] = df["queue_sum"] / df["events"].replace(0, np.nan) / 60.0
    cond_churn = (df["recency_days"] >= CHURN_DAYS) & (df["age_days"] >= MIN_AGE_DAYS)
    cond_risk = (df["recency_days"] >= AT_RISK_DAYS) & (df["recency_days"] < CHURN_DAYS)
    df["segment"] = np.select(
        [cond_churn, cond_risk, df["recency_days"] < AT_RISK_DAYS],
        ["churned", "at_risk", "active"], default="new")
    df.loc[(df["age_days"] < MIN_AGE_DAYS) & (df["recency_days"] < CHURN_DAYS), "segment"] = "new"
    return df


def acquisition_retention(cities=None) -> pd.DataFrame:
    """Monthly new riders vs returning riders."""
    rp = store.get("rider_profile")
    rd = store.get("riders")
    if rp.empty or rd.empty:
        return pd.DataFrame()
    df = rp[["rider_id", "first_ts", "completed"]].merge(
        rd[["rider_id", "home_city"]], on="rider_id", how="left")
    df["month"] = pd.to_datetime(df["first_ts"]).dt.to_period("M").astype(str)
    if cities:
        df = df[df["home_city"].isin(cities)]
    new_riders = df.groupby("month", as_index=False).agg(new_riders=("rider_id", "nunique"))
    # returning riders per month = riders active that month who signed up earlier
    # approximate via daily_city completed counts is city-level; use rider first_ts month cohort
    dc = store.get("daily_city")
    if not dc.empty and cities:
        dc = dc[dc["city"].isin(cities)]
    completed_m = dc.assign(month=pd.to_datetime(dc["date"]).dt.to_period("M").astype(str)) \
        .groupby("month", as_index=False)["completed"].sum()
    out = new_riders.merge(completed_m, on="month", how="outer").fillna(0)
    return out.sort_values("month")


def cohort_retention() -> pd.DataFrame:
    """Signup-month cohort retention: % of cohort riders swapping in each
    subsequent month relative to cohort size."""
    rd = store.get("riders")
    rp = store.get("rider_profile")
    if rd.empty or rp.empty:
        return pd.DataFrame()
    signup = rd[["rider_id", "signup_date"]].copy()
    signup["cohort"] = pd.to_datetime(signup["signup_date"]).dt.to_period("M").astype(str)
    # activity per rider per month is not stored; approximate using first_ts month
    # and tenure: riders with tenure_days >= k*30 are "retained at month k"
    df = rp.merge(signup[["rider_id", "cohort"]], on="rider_id", how="inner")
    df["tenure_days"] = (pd.to_datetime(df["last_ts"]) - pd.to_datetime(df["first_ts"])).dt.days
    cohorts = df.groupby("cohort").agg(
        riders=("rider_id", "nunique"),
        m1=("tenure_days", lambda s: (s >= 30).mean()),
        m2=("tenure_days", lambda s: (s >= 60).mean()),
        m3=("tenure_days", lambda s: (s >= 90).mean()),
        m6=("tenure_days", lambda s: (s >= 180).mean()),
    )
    cohorts = cohorts.reset_index().sort_values("cohort")
    return cohorts


def churn_segments() -> pd.DataFrame:
    df = rider_table()
    if df.empty:
        return pd.DataFrame()
    return (df.groupby("segment", as_index=False)
            .agg(riders=("rider_id", "nunique"),
                 avg_completed=("completed", "mean"),
                 avg_revenue=("revenue", "mean"),
                 avg_swaps_per_week=("swaps_per_week", "mean"),
                 avg_failure_rate=("failure_rate", "mean"),
                 avg_queue_min=("avg_queue_min", "mean")))


def churn_drivers() -> pd.DataFrame:
    """Compare feature means between churned and active riders."""
    df = rider_table()
    if df.empty:
        return pd.DataFrame()
    feats = ["completed", "events", "stations_used", "swaps_per_week",
             "failure_rate", "avg_queue_min", "rev_per_swap", "km",
             "tenure_days", "recency_days"]
    piv = df.groupby("segment")[feats].mean().T.reset_index().rename(
        columns={"index": "feature"})
    return piv


def tickets_per_rider() -> pd.DataFrame:
    tk = store.get("support_tickets")
    if tk.empty:
        return pd.DataFrame()
    return tk.groupby("rider_id").size().rename("tickets").reset_index()
