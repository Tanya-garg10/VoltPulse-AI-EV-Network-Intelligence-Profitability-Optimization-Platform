"""Build compact analytical Parquet tables from raw CSVs.

The 3.9M-row swap_events.csv is processed in chunks and reduced to
pre-aggregated tables so the dashboard never loads raw events.
Raw CSVs are never modified.
"""
import pandas as pd

from src.config import (CHUNK_SIZE, CONTEXT_CSV, FLEET_CSV, PARQUET_DIR,
                        RIDERS_CSV, STATIONS_CSV, SWAP_EVENTS_CSV, TICKETS_CSV)
from src.utils import get_logger

log = get_logger("transform")

EVENT_TYPES = ["swap_completed", "failed_no_charged_battery",
               "failed_system_error", "abandoned_queue", "cancelled_by_rider"]


def _save(df: pd.DataFrame, name: str) -> None:
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET_DIR / f"{name}.parquet", index=False)
    log.info("wrote %s.parquet (%d rows)", name, len(df))


def _load_dimensions() -> None:
    """Clean + persist dimension tables (small files)."""
    st = pd.read_csv(STATIONS_CSV)
    for c in ["commissioned_date", "decommissioned_date",
              "firmware_updated_date", "competitor_within_1_5km_since"]:
        st[c] = pd.to_datetime(st[c], errors="coerce")
    _save(st, "stations")

    rd = pd.read_csv(RIDERS_CSV, parse_dates=["signup_date"])
    _save(rd, "riders")

    fp = pd.read_csv(FLEET_CSV, parse_dates=["contract_start_date", "amendment_date"])
    _save(fp, "fleet_partners")

    cx = pd.read_csv(CONTEXT_CSV, parse_dates=["date"])
    _save(cx, "city_daily_context")

    tk = pd.read_csv(TICKETS_CSV, parse_dates=["created_ts"])
    tk["resolution_hours"] = pd.to_numeric(tk["resolution_hours"], errors="coerce")
    tk["csat_score"] = pd.to_numeric(tk["csat_score"], errors="coerce")
    _save(tk, "support_tickets")


class _Accumulator:
    """Collect groupby results across chunks and concat at the end."""

    def __init__(self):
        self.parts = {}

    def add(self, key: str, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        self.parts.setdefault(key, []).append(df)

    def flush(self, name: str, index_cols: list[str],
              special_aggs: dict | None = None) -> pd.DataFrame:
        parts = self.parts.get(name, [])
        if not parts:
            return pd.DataFrame()
        df = pd.concat(parts, ignore_index=True)
        if special_aggs:
            aggs = {}
            for c in df.columns:
                if c in index_cols:
                    continue
                if c in special_aggs:
                    aggs[c] = special_aggs[c]
                elif pd.api.types.is_numeric_dtype(df[c]):
                    aggs[c] = "sum"
            out = df.groupby(index_cols, as_index=False).agg(aggs)
        else:
            out = df.groupby(index_cols, as_index=False).sum(numeric_only=True)
        _save(out, name)
        return out


def build_swap_aggregates() -> None:
    stations = pd.read_parquet(PARQUET_DIR / "stations.parquet",
                               columns=["station_id", "city"])
    city_map = dict(zip(stations["station_id"], stations["city"]))

    acc = _Accumulator()
    nrows = 0

    usecols = ["rider_id", "station_id", "event_ts", "event_type",
               "attempt_seq", "queue_wait_sec", "battery_in_id",
               "battery_out_id", "soc_in_pct", "soh_in_pct",
               "soc_out_pct", "soh_out_pct", "km_since_last_swap",
               "tariff_code", "list_price_inr", "discount_inr",
               "amount_charged_inr", "payment_mode",
               "energy_to_recharge_kwh"]

    for chunk in pd.read_csv(SWAP_EVENTS_CSV, chunksize=CHUNK_SIZE,
                             usecols=usecols, parse_dates=["event_ts"]):
        nrows += len(chunk)
        chunk["city"] = chunk["station_id"].map(city_map)
        chunk["date"] = chunk["event_ts"].dt.date.astype(str)
        chunk["month"] = chunk["event_ts"].dt.to_period("M").astype(str)
        chunk["hour"] = chunk["event_ts"].dt.hour
        chunk["dow"] = chunk["event_ts"].dt.dayofweek
        chunk["completed"] = (chunk["event_type"] == "swap_completed").astype("int8")
        chunk["failed_battery"] = (chunk["event_type"] == "failed_no_charged_battery").astype("int8")
        chunk["failed_system"] = (chunk["event_type"] == "failed_system_error").astype("int8")
        chunk["abandoned"] = (chunk["event_type"] == "abandoned_queue").astype("int8")
        chunk["cancelled"] = (chunk["event_type"] == "cancelled_by_rider").astype("int8")
        chunk["retry"] = (chunk["attempt_seq"] > 1).astype("int8")
        chunk["revenue"] = chunk["amount_charged_inr"].where(
            chunk["event_type"] == "swap_completed", 0.0).fillna(0.0)
        # queue wait only meaningful when present; fillna 0
        chunk["queue_wait_sec"] = chunk["queue_wait_sec"].fillna(0)
        chunk["energy"] = chunk["energy_to_recharge_kwh"].fillna(0)
        chunk["km"] = chunk["km_since_last_swap"].fillna(0)
        chunk["list_price"] = chunk["list_price_inr"].fillna(0)
        chunk["discount"] = chunk["discount_inr"].fillna(0)

        # ---- daily x city ----
        g = chunk.groupby(["date", "city"], as_index=False).agg(
            attempts=("event_type", "size"),
            completed=("completed", "sum"),
            failed_battery=("failed_battery", "sum"),
            failed_system=("failed_system", "sum"),
            abandoned=("abandoned", "sum"),
            cancelled=("cancelled", "sum"),
            retries=("retry", "sum"),
            revenue=("revenue", "sum"),
            list_price=("list_price", "sum"),
            discount=("discount", "sum"),
            energy=("energy", "sum"),
            queue_sum=("queue_wait_sec", "sum"),
            km=("km", "sum"),
        )
        acc.add("daily_city", g)

        # ---- daily x city x tariff (pricing analysis) ----
        t = chunk.groupby(["date", "city", "tariff_code"], as_index=False).agg(
            events=("event_type", "size"),
            completed=("completed", "sum"),
            revenue=("revenue", "sum"),
            list_price=("list_price", "sum"),
            discount=("discount", "sum"),
        )
        acc.add("daily_city_tariff", t)

        # ---- monthly x city x hour x event_type (heatmaps/seasonality) ----
        h = chunk.groupby(["month", "city", "hour", "event_type"],
                          as_index=False).agg(
                              events=("event_type", "size"),
                              revenue=("revenue", "sum"))
        acc.add("hourly_city_type", h)

        # ---- station x date ----
        s = chunk.groupby(["station_id", "date"], as_index=False).agg(
            attempts=("event_type", "size"),
            completed=("completed", "sum"),
            failed_battery=("failed_battery", "sum"),
            failed_system=("failed_system", "sum"),
            abandoned=("abandoned", "sum"),
            cancelled=("cancelled", "sum"),
            retries=("retry", "sum"),
            revenue=("revenue", "sum"),
            queue_sum=("queue_wait_sec", "sum"),
            energy=("energy", "sum"),
        )
        acc.add("station_daily", s)

        # ---- station x dow x hour (bottleneck pattern) ----
        sh = chunk.groupby(["station_id", "dow", "hour"], as_index=False).agg(
            attempts=("event_type", "size"),
            completed=("completed", "sum"),
            failed_battery=("failed_battery", "sum"),
            failed_system=("failed_system", "sum"),
            abandoned=("abandoned", "sum"),
            queue_sum=("queue_wait_sec", "sum"),
        )
        acc.add("station_dow_hour", sh)

        # ---- rider profile ----
        r = chunk.groupby("rider_id", as_index=False).agg(
            events=("event_type", "size"),
            completed=("completed", "sum"),
            failed_battery=("failed_battery", "sum"),
            failed_system=("failed_system", "sum"),
            abandoned=("abandoned", "sum"),
            cancelled=("cancelled", "sum"),
            revenue=("revenue", "sum"),
            list_price=("list_price", "sum"),
            discount=("discount", "sum"),
            energy=("energy", "sum"),
            queue_sum=("queue_wait_sec", "sum"),
            km=("km", "sum"),
            first_ts=("event_ts", "min"),
            last_ts=("event_ts", "max"),
            partner_billed_rev=("revenue", lambda x: 0.0),  # placeholder replaced below
        )
        # partner vs retail revenue split
        part = chunk.assign(
            rev_partner=chunk["revenue"].where(chunk["payment_mode"] == "partner_invoice", 0.0),
            rev_retail=chunk["revenue"].where(chunk["payment_mode"] != "partner_invoice", 0.0),
        ).groupby("rider_id", as_index=False).agg(
            rev_partner=("rev_partner", "sum"), rev_retail=("rev_retail", "sum"))
        r = r.drop(columns=["partner_billed_rev"]).merge(part, on="rider_id", how="left")
        acc.add("rider_profile", r)

        # rider x station usage pairs (for exact nunique at the end)
        rs = chunk[["rider_id", "station_id"]].drop_duplicates()
        acc.add("rider_station_pairs", rs)

        # ---- battery profiles: battery swapped OUT (charged, handed to rider) ----
        bo = chunk.dropna(subset=["battery_out_id"])
        b_out = bo.groupby("battery_out_id", as_index=False).agg(
            swaps_out=("completed", "sum"),
            events_out=("event_type", "size"),
            soc_out_sum=("soc_out_pct", "sum"),
            n_soc_out=("soc_out_pct", "count"),
            soh_out_sum=("soh_out_pct", "sum"),
            n_soh_out=("soh_out_pct", "count"),
            min_soh_out=("soh_out_pct", "min"),
            first_ts=("event_ts", "min"),
            last_ts=("event_ts", "max"),
            energy_out=("energy", "sum"),
        ).rename(columns={"battery_out_id": "battery_id"})
        acc.add("battery_out", b_out)

        bi = chunk.dropna(subset=["battery_in_id"])
        b_in = bi.groupby("battery_in_id", as_index=False).agg(
            swaps_in=("completed", "sum"),
            soc_in_sum=("soc_in_pct", "sum"),
            n_soc_in=("soc_in_pct", "count"),
            soh_in_sum=("soh_in_pct", "sum"),
            n_soh_in=("soh_in_pct", "count"),
            min_soh_in=("soh_in_pct", "min"),
            energy_in=("energy", "sum"),
        ).rename(columns={"battery_in_id": "battery_id"})
        acc.add("battery_in", b_in)

        # ---- battery involvement in failures ----
        fail = chunk[chunk["event_type"].str.startswith("failed", na=False)]
        bf = fail.melt(value_vars=["battery_in_id", "battery_out_id"],
                       value_name="battery_id").dropna(subset=["battery_id"])
        if not bf.empty:
            bfail = bf.groupby("battery_id", as_index=False).agg(
                failure_events=("battery_id", "size"))
            acc.add("battery_failures", bfail)

        if nrows % (CHUNK_SIZE * 5) == 0:
            log.info("processed %d rows", nrows)

    log.info("swap_events fully processed: %d rows", nrows)

    # flush accumulators
    acc.flush("daily_city", ["date", "city"])
    acc.flush("daily_city_tariff", ["date", "city", "tariff_code"])
    acc.flush("hourly_city_type", ["month", "city", "hour", "event_type"])
    acc.flush("station_daily", ["station_id", "date"])
    acc.flush("station_dow_hour", ["station_id", "dow", "hour"])

    # rider_profile needs sum-merge of first/last ts
    parts = acc.parts.get("rider_profile", [])
    if parts:
        rp = pd.concat(parts, ignore_index=True)
        grp_cols = [c for c in rp.columns if c not in
                    ("first_ts", "last_ts", "stations_used", "rev_partner", "rev_retail")]
        agg_map = {c: "sum" for c in grp_cols if c != "rider_id"}
        rp = rp.groupby("rider_id", as_index=False).agg(
            **{c: (c, "sum") for c in grp_cols if c != "rider_id"},
            first_ts=("first_ts", "min"), last_ts=("last_ts", "max"),
            rev_partner=("rev_partner", "sum"), rev_retail=("rev_retail", "sum"),
        )
        # exact distinct-station count per rider
        rs_parts = acc.parts.get("rider_station_pairs", [])
        if rs_parts:
            rs_all = pd.concat(rs_parts, ignore_index=True).drop_duplicates()
            st_counts = rs_all.groupby("rider_id").size().rename("stations_used")
            rp = rp.merge(st_counts, on="rider_id", how="left")
        rp["stations_used"] = rp["stations_used"].fillna(0).astype(int)
        _save(rp, "rider_profile")

    # battery merge
    batt_special = {"first_ts": "min", "last_ts": "max",
                    "min_soh_out": "min", "min_soh_in": "min"}
    bo = acc.flush("battery_out", ["battery_id"], batt_special) if acc.parts.get("battery_out") else pd.DataFrame()
    bi = acc.flush("battery_in", ["battery_id"], batt_special) if acc.parts.get("battery_in") else pd.DataFrame()
    batt = bo.merge(bi, on="battery_id", how="outer")
    for pre, ncol, out in [("soc_out", "n_soc_out", "avg_soc_out"),
                           ("soh_out", "n_soh_out", "avg_soh_out"),
                           ("soc_in", "n_soc_in", "avg_soc_in"),
                           ("soh_in", "n_soh_in", "avg_soh_in")]:
        s = f"{pre}_sum"
        if s in batt.columns:
            batt[out] = batt[s] / batt[ncol].replace(0, pd.NA)
    batt = batt.drop(columns=[c for c in batt.columns
                              if c.endswith("_sum") or c.startswith("n_so")])
    bf_parts = acc.parts.get("battery_failures", [])
    if bf_parts:
        bf = pd.concat(bf_parts).groupby("battery_id", as_index=False).agg(
            failure_events=("failure_events", "sum"))
        batt = batt.merge(bf, on="battery_id", how="left")
    batt["failure_events"] = batt.get("failure_events", 0)
    batt["vehicle_class"] = batt["battery_id"].str.extract(r"BAT-(\w+?)-", expand=False)
    _save(batt, "battery_profile")


def run() -> None:
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    log.info("loading dimension tables")
    _load_dimensions()
    log.info("aggregating swap_events")
    build_swap_aggregates()
    log.info("pipeline complete")


if __name__ == "__main__":
    run()
