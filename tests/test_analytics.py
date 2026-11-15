"""Tests for VoltPulse AI analytics and pipeline."""
import numpy as np
import pandas as pd
import pytest

from src.analytics.filters import add_rates, filter_daily_city


def sample_daily():
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "city": ["Pune", "Pune", "Mumbai"],
        "attempts": [100, 200, 50],
        "completed": [90, 150, 40],
        "failed_battery": [5, 20, 3],
        "failed_system": [5, 30, 7],
        "abandoned": [0, 0, 0],
        "cancelled": [0, 0, 0],
        "revenue": [900.0, 1500.0, 400.0],
        "list_price": [1000.0, 1700.0, 450.0],
        "discount": [100.0, 200.0, 50.0],
        "energy": [10.0, 20.0, 5.0],
        "queue_sum": [600.0, 1200.0, 300.0],
        "km": [1000.0, 2000.0, 500.0],
    })


def test_filter_daily_city():
    df = sample_daily()
    out = filter_daily_city(df, cities=["Pune"])
    assert len(out) == 2
    out2 = filter_daily_city(df, cities=["Pune"], date_min="2024-01-02")
    assert len(out2) == 1 and out2.iloc[0]["date"] == "2024-01-02"


def test_add_rates():
    df = add_rates(sample_daily())
    row = df.iloc[0]
    assert abs(row["success_rate"] - 0.9) < 1e-9
    assert abs(row["rev_per_swap"] - 10.0) < 1e-9
    assert abs(row["avg_queue_min"] - 0.1) < 1e-9


def test_kpis_consistency():
    from src.analytics import network as net
    # use real store if parquet exists, else skip
    pytest.importorskip("src.database.store")
    k = net.network_kpis()
    if not k:
        pytest.skip("no parquet data")
    assert 0 <= k["success_rate"] <= 1
    assert k["completed"] <= k["attempts"]
    assert k["revenue"] >= 0


def test_recommendation_structure():
    from src.recommendations import engine
    recs = engine.generate()
    for r in recs:
        assert r["priority"] in ("Critical", "High", "Medium", "Low")
        assert r["title"] and r["evidence"] and r["action"]


def test_churn_definition():
    from src.analytics import churn as ch
    rt = ch.rider_table()
    if rt.empty:
        pytest.skip("no rider data")
    assert set(rt["segment"].unique()) <= {"new", "active", "at_risk", "churned"}
    churned = rt[rt["segment"] == "churned"]
    if len(churned):
        assert (churned["recency_days"] >= ch.CHURN_DAYS).all()


def test_model_metrics_bounded():
    from src.analytics import models as ml
    res = ml.train_churn_model()
    if res.get("status") != "ok":
        pytest.skip("model not trainable")
    assert 0 <= res["auc"] <= 1
    assert 0 <= res["accuracy"] <= 1
    assert res["importance"] is not None
