"""Analytical data store.

Loads the compact Parquet aggregate tables once per process and serves
them to analytics functions. Raw 3.9M-row events are never loaded.
"""
from functools import lru_cache

import pandas as pd

from src.config import PARQUET_DIR
from src.utils import get_logger

log = get_logger("store")

TABLES = [
    "daily_city", "daily_city_tariff", "hourly_city_type", "station_daily", "station_dow_hour",
    "rider_profile", "battery_profile", "stations", "riders",
    "fleet_partners", "city_daily_context", "support_tickets",
]


@lru_cache(maxsize=1)
def load_all() -> dict[str, pd.DataFrame]:
    tables = {}
    for name in TABLES:
        path = PARQUET_DIR / f"{name}.parquet"
        if path.exists():
            tables[name] = pd.read_parquet(path)
            log.info("loaded %s: %d rows", name, len(tables[name]))
        else:
            log.warning("missing parquet: %s", path)
            tables[name] = pd.DataFrame()
    # derived helpers
    if "stations" in tables and not tables["stations"].empty:
        tables["station_city"] = tables["stations"][["station_id", "city"]]
    return tables


def get(name: str) -> pd.DataFrame:
    return load_all()[name]


def data_end_date() -> pd.Timestamp:
    dc = get("daily_city")
    if dc.empty:
        return pd.Timestamp("2025-06-30")
    return pd.to_datetime(dc["date"]).max()


def city_filter_options() -> list[str]:
    st = get("stations")
    if st.empty:
        return []
    return sorted(st["city"].dropna().unique().tolist())
