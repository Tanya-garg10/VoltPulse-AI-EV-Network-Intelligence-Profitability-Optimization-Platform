"""Module E — Profitability Analytics.

IMPORTANT: No cost-per-swap data exists in the dataset. Revenue-side metrics
are computed exactly; margin metrics use station-level fixed costs
(rent + maintenance) amortized over completed swaps, clearly labelled as
ESTIMATES. Fleet partner economics use actual contract discount fields.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.filters import filter_daily_city
from src.database import store


def revenue_trend(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
    dc = dc.copy()
    dc["month"] = pd.to_datetime(dc["date"]).dt.to_period("M").astype(str)
    g = dc.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), completed=("completed", "sum"),
        attempts=("attempts", "sum"), list_price=("list_price", "sum"),
        discount=("discount", "sum"))
    g["rev_per_swap"] = g["revenue"] / g["completed"].replace(0, np.nan)
    g["discount_rate"] = g["discount"] / g["list_price"].replace(0, np.nan)
    return g


def tariff_analysis(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    t = store.get("daily_city_tariff")
    if t.empty:
        return pd.DataFrame()
    if cities:
        t = t[t["city"].isin(cities)]
    if date_min:
        t = t[t["date"] >= str(date_min)]
    if date_max:
        t = t[t["date"] <= str(date_max)]
    g = t.groupby("tariff_code", as_index=False).agg(
        events=("events", "sum"), completed=("completed", "sum"),
        revenue=("revenue", "sum"), list_price=("list_price", "sum"),
        discount=("discount", "sum"))
    g["avg_price"] = g["revenue"] / g["completed"].replace(0, np.nan)
    g["share_revenue"] = g["revenue"] / g["revenue"].sum()
    return g.sort_values("revenue", ascending=False)


def city_profitability(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
    st = store.get("stations")
    if dc.empty:
        return pd.DataFrame()
    g = dc.groupby("city", as_index=False).agg(
        revenue=("revenue", "sum"), completed=("completed", "sum"),
        attempts=("attempts", "sum"), energy=("energy", "sum"))
    # estimated fixed cost: (rent + maintenance) per station per month
    months = dc["date"].nunique() / 30.4 if len(dc) else 1
    st_cost = st.groupby("city").agg(
        stations=("station_id", "nunique"),
        monthly_fixed=("monthly_rent_inr", "sum"))
    st_cost["monthly_fixed"] = st_cost["monthly_fixed"] + \
        st.groupby("city")["monthly_maintenance_inr"].sum()
    # scale by active months observed
    st_cost["est_fixed_cost"] = st_cost["monthly_fixed"] * months
    g = g.merge(st_cost[["stations", "est_fixed_cost"]],
                left_on="city", right_index=True, how="left")
    g["rev_per_swap"] = g["revenue"] / g["completed"].replace(0, np.nan)
    g["est_contribution"] = g["revenue"] - g["est_fixed_cost"]
    g["est_margin_pct"] = g["est_contribution"] / g["revenue"].replace(0, np.nan)
    return g.sort_values("revenue", ascending=False)


def station_unit_economics(cities=None, date_min=None, date_max=None,
                           min_attempts=50) -> pd.DataFrame:
    sd = store.get("station_daily")
    st = store.get("stations")
    if sd.empty:
        return pd.DataFrame()
    if cities:
        valid = set(st.loc[st["city"].isin(cities), "station_id"])
        sd = sd[sd["station_id"].isin(valid)]
    if date_min:
        sd = sd[sd["date"] >= str(date_min)]
    if date_max:
        sd = sd[sd["date"] <= str(date_max)]
    g = sd.groupby("station_id", as_index=False).agg(
        attempts=("attempts", "sum"), completed=("completed", "sum"),
        revenue=("revenue", "sum"), active_days=("date", "nunique"))
    g = g[g["attempts"] >= min_attempts]
    months = max(g["active_days"].max() / 30.4, 1) if len(g) else 1
    g = g.merge(st[["station_id", "city", "monthly_rent_inr",
                    "monthly_maintenance_inr", "grid_tariff_inr_kwh"]],
                on="station_id", how="left")
    g["est_fixed_cost"] = (g["monthly_rent_inr"] + g["monthly_maintenance_inr"]) * months
    g["est_contribution"] = g["revenue"] - g["est_fixed_cost"]
    g["est_margin_pct"] = g["est_contribution"] / g["revenue"].replace(0, np.nan)
    g["rev_per_swap"] = g["revenue"] / g["completed"].replace(0, np.nan)
    return g.sort_values("est_contribution")


def fleet_economics(cities=None) -> pd.DataFrame:
    """Fleet partner revenue exposure via rider_profile partner/retail split."""
    rp = store.get("rider_profile")
    rd = store.get("riders")
    fp = store.get("fleet_partners")
    if rp.empty or rd.empty:
        return pd.DataFrame()
    df = rp.merge(rd[["rider_id", "partner_id"]], on="rider_id", how="left")
    if cities:
        df = df[df["home_city"].isin(cities)] if "home_city" in df else df
    g = df.groupby("partner_id", as_index=False).agg(
        riders=("rider_id", "nunique"),
        partner_rev=("rev_partner", "sum"),
        retail_rev=("rev_retail", "sum"),
        total_rev=("revenue", "sum"),
        completed=("completed", "sum"))
    g = g.merge(fp, on="partner_id", how="left")
    g["partner_share"] = g["partner_rev"] / g["total_rev"].replace(0, np.nan)
    g["discount_pct_effective"] = g["discount_pct"]
    # riders df has home_city; merge it
    return g.sort_values("total_rev", ascending=False)


def discount_erosion(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    """Monthly discount rate = discount / list price — margin erosion signal."""
    t = store.get("daily_city_tariff")
    if t.empty:
        dc = filter_daily_city(store.get("daily_city"), cities, date_min, date_max)
        dc = dc.copy()
        dc["month"] = pd.to_datetime(dc["date"]).dt.to_period("M").astype(str)
        g = dc.groupby("month", as_index=False).agg(
            revenue=("revenue", "sum"), list_price=("list_price", "sum"),
            discount=("discount", "sum"), completed=("completed", "sum"))
    else:
        tt = t.copy()
        if cities:
            tt = tt[tt["city"].isin(cities)]
        if date_min:
            tt = tt[tt["date"] >= str(date_min)]
        if date_max:
            tt = tt[tt["date"] <= str(date_max)]
        tt["month"] = pd.to_datetime(tt["date"]).dt.to_period("M").astype(str)
        g = tt.groupby("month", as_index=False).agg(
            revenue=("revenue", "sum"), list_price=("list_price", "sum"),
            discount=("discount", "sum"), completed=("completed", "sum"))
    g["discount_rate"] = g["discount"] / g["list_price"].replace(0, np.nan)
    g["net_realization"] = g["revenue"] / g["list_price"].replace(0, np.nan)
    return g


def peak_vs_offpeak(cities=None, date_min=None, date_max=None) -> pd.DataFrame:
    return tariff_analysis(cities, date_min, date_max)
