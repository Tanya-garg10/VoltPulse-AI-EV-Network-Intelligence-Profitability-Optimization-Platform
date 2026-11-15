"""Module G prep + ML models.

Models (trained on aggregate features, evaluated honestly):
  1. Rider churn classifier — predicts churned vs active/at-risk.
  2. Station failure-risk regressor — predicts station failure rate.
  3. Demand forecast — seasonal-naive vs linear trend on daily completed swaps.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.analytics.churn import rider_table
from src.analytics.failures import station_failure_table
from src.analytics.filters import monthly
from src.database import store
from src.utils import get_logger

log = get_logger("models")


# ---------------- Rider churn model ----------------
@lru_cache(maxsize=1)
def _train_churn_model_cached() -> dict:
    return _train_churn_model_impl()


def train_churn_model() -> dict:
    return _train_churn_model_cached()


CHURN_FEATURES = ["completed", "events", "stations_used", "swaps_per_week",
                  "failure_rate", "avg_queue_min", "rev_per_swap", "km",
                  "tenure_days", "energy"]


def _train_churn_model_impl() -> dict:
    df = rider_table()
    if df.empty:
        return {"status": "no_data"}
    df = df[df["segment"].isin(["churned", "active", "at_risk"])].copy()
    X = df[CHURN_FEATURES].apply(pd.to_numeric, errors="coerce")
    y = (df["segment"] == "churned").astype(int)
    mask = X.notna().all(axis=1) & np.isfinite(X).all(axis=1)
    X, y = X[mask], y[mask]
    if len(X) < 200 or y.nunique() < 2:
        return {"status": "insufficient_data", "n": len(X)}
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(Xtr)
    Xte_s = scaler.transform(Xte)
    clf = HistGradientBoostingClassifier(max_iter=200, random_state=42)
    clf.fit(Xtr_s, ytr)
    proba = clf.predict_proba(Xte_s)[:, 1]
    pred = (proba >= 0.5).astype(int)
    auc = roc_auc_score(yte, proba) if yte.nunique() > 1 else float("nan")
    # feature importance via permutation on a subsample
    from sklearn.inspection import permutation_importance
    imp = permutation_importance(clf, Xte_s, yte, n_repeats=3,
                                 random_state=42, scoring="roc_auc")
    importance = pd.DataFrame({
        "feature": CHURN_FEATURES,
        "importance": imp.importances_mean,
    }).sort_values("importance", ascending=False)
    # score all riders
    Xall_s = scaler.transform(X)
    df_all = df.loc[mask].copy()
    df_all["churn_probability"] = clf.predict_proba(Xall_s)[:, 1]
    df_all["risk_band"] = pd.cut(df_all["churn_probability"],
                                 bins=[0, 0.33, 0.66, 1.0],
                                 labels=["low", "medium", "high"])
    return {
        "status": "ok",
        "n_train": len(Xtr), "n_test": len(Xte),
        "accuracy": float(accuracy_score(yte, pred)),
        "f1": float(f1_score(yte, pred)),
        "auc": float(auc),
        "importance": importance,
        "scored": df_all[["rider_id", "churn_probability", "risk_band",
                          "segment", "home_city", "partner_id",
                          "revenue", "completed"]],
        "definition": ("churned = no swap in last 30 days of data window "
                       "and rider age >= 45 days"),
    }


def churn_risk_table() -> pd.DataFrame:
    res = train_churn_model()
    if res.get("status") != "ok":
        return pd.DataFrame()
    return res["scored"]


# ---------------- Station failure risk ----------------
@lru_cache(maxsize=1)
def train_station_risk() -> dict:
    return _train_station_risk_impl()


def _train_station_risk_impl() -> dict:
    t = station_failure_table(min_attempts=50)
    if t.empty or len(t) < 30:
        return {"status": "insufficient_data"}
    feats = ["attempts", "completed", "revenue", "energy", "active_days",
             "slots_2w", "slots_3w", "monthly_rent_inr",
             "monthly_maintenance_inr", "grid_tariff_inr_kwh"]
    feats = [c for c in feats if c in t.columns]
    X = t[feats].apply(pd.to_numeric, errors="coerce").fillna(0)
    y = (t["failure_rate"] * 100).clip(upper=100)  # failure rate %
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)
    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=2)
    rf.fit(Xtr, ytr)
    pred = rf.predict(Xte)
    mae = mean_absolute_error(yte, pred)
    base = mean_absolute_error(yte, np.full_like(yte, ytr.mean()))
    imp = pd.DataFrame({"feature": feats,
                        "importance": rf.feature_importances_}
                       ).sort_values("importance", ascending=False)
    t2 = t.copy()
    t2["predicted_failure_rate"] = rf.predict(X)
    return {
        "status": "ok", "n_stations": len(t),
        "mae": float(mae), "baseline_mae": float(base),
        "beat_baseline": bool(mae < base),
        "importance": imp,
        "ranked": t2[["station_id", "city", "failure_rate",
                      "predicted_failure_rate", "attempts", "risk_score"]]
                  .sort_values("predicted_failure_rate", ascending=False),
    }


# ---------------- Demand forecast ----------------
@lru_cache(maxsize=4)
def demand_forecast(horizon_days: int = 30) -> dict:
    return _demand_forecast_impl(horizon_days)


def _demand_forecast_impl(horizon_days: int = 30) -> dict:
    dc = store.get("daily_city")
    if dc.empty:
        return {"status": "no_data"}
    d = dc.copy()
    d["date"] = pd.to_datetime(d["date"])
    daily = d.groupby("date", as_index=False)["completed"].sum().sort_values("date")
    daily["doy"] = daily["date"].dt.dayofyear
    # features: trend + day-of-year seasonality (Fourier) + dow
    X = pd.DataFrame({
        "t": np.arange(len(daily)),
        "dow": daily["date"].dt.dayofweek,
        "sin1": np.sin(2 * np.pi * daily["doy"] / 365.25),
        "cos1": np.cos(2 * np.pi * daily["doy"] / 365.25),
        "sin2": np.sin(4 * np.pi * daily["doy"] / 365.25),
        "cos2": np.cos(4 * np.pi * daily["doy"] / 365.25),
    })
    y = daily["completed"].values
    # hold out last 60 days
    split = len(daily) - 60
    if split < 200:
        return {"status": "insufficient_data"}
    lr = LinearRegression()
    lr.fit(X.iloc[:split], y[:split])
    pred_te = lr.predict(X.iloc[split:])
    mae_model = mean_absolute_error(y[split:], pred_te)
    # seasonal-naive baseline: same weekday last week
    naive = daily["completed"].shift(7).values[split:]
    mae_naive = mean_absolute_error(y[split:], naive)
    # future forecast
    last = daily["date"].max()
    fut_dates = pd.date_range(last + pd.Timedelta(days=1), periods=horizon_days)
    Xf = pd.DataFrame({
        "t": np.arange(split + len(y) - split, split + len(y) - split + horizon_days),
        "dow": fut_dates.dayofweek,
        "sin1": np.sin(2 * np.pi * fut_dates.dayofyear / 365.25),
        "cos1": np.cos(2 * np.pi * fut_dates.dayofyear / 365.25),
        "sin2": np.sin(4 * np.pi * fut_dates.dayofyear / 365.25),
        "cos2": np.cos(4 * np.pi * fut_dates.dayofyear / 365.25),
    })
    # continue t from full history
    Xf["t"] = np.arange(len(daily), len(daily) + horizon_days)
    lr_full = LinearRegression().fit(X, y)
    fc = lr_full.predict(Xf)
    fc = np.clip(fc, 0, None)
    future = pd.DataFrame({"date": fut_dates, "forecast_completed": fc})
    hist = daily[["date", "completed"]].rename(columns={"completed": "actual"})
    return {
        "status": "ok",
        "mae_model": float(mae_model), "mae_naive": float(mae_naive),
        "model_beats_naive": bool(mae_model < mae_naive),
        "history": hist, "future": future,
        "test_actual": daily.iloc[split:][["date", "completed"]].rename(
            columns={"completed": "actual"}).assign(forecast=pred_te),
    }
