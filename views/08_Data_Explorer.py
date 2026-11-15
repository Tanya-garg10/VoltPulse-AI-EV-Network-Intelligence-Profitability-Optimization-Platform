"""Page 8 — Data Explorer."""
import pandas as pd
import streamlit as st

from components.ui import card, end_card, page_title
from src.database import store

TABLE_LABELS = {
    "daily_city": "Daily × City aggregates",
    "daily_city_tariff": "Daily × City × Tariff",
    "hourly_city_type": "Monthly × City × Hour × Event type",
    "station_daily": "Station × Date aggregates",
    "station_dow_hour": "Station × DOW × Hour",
    "rider_profile": "Rider lifetime profile",
    "battery_profile": "Battery health profile",
    "stations": "Stations (dimension)",
    "riders": "Riders (dimension)",
    "fleet_partners": "Fleet partners (dimension)",
    "city_daily_context": "City daily context (weather/calendar)",
    "support_tickets": "Support tickets",
}


def render(f):
    page_title("Data Explorer",
               "Inspect processed Parquet tables, quality and filters")

    tables = store.load_all()
    names = [n for n in TABLE_LABELS if n in tables and not tables[n].empty]
    sel = st.selectbox("Dataset", names,
                       format_func=lambda n: f"{TABLE_LABELS[n]}  ({len(tables[n]):,} rows)")
    df = tables[sel].copy()

    c = st.columns(4)
    c[0].metric("Rows", f"{len(df):,}")
    c[1].metric("Columns", len(df.columns))
    c[2].metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
    c[3].metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")

    st.write("")
    t1, t2 = st.tabs(["Schema & quality", "Browse & export"])

    with t1:
        card("Column profile")
        prof = pd.DataFrame({
            "column": df.columns,
            "dtype": df.dtypes.astype(str),
            "nulls": df.isna().sum().values,
            "null_%": (df.isna().sum() / len(df) * 100).round(2).values,
            "nunique": df.nunique().values,
        })
        st.dataframe(prof, use_container_width=True, hide_index=True, height=420)
        end_card()

        card("Categorical values", "Top values per low-cardinality column")
        for col in df.columns:
            if df[col].dtype == object and df[col].nunique() <= 15:
                vc = df[col].value_counts().head(10)
                st.markdown(f"**{col}**")
                st.dataframe(pd.DataFrame({"value": vc.index, "count": vc.values}),
                             use_container_width=True, hide_index=True, height=180)

    with t2:
        card("Filterable records", "Filters apply to this table only")
        fc = st.columns(3)
        text_cols = [c_ for c_ in df.columns if df[c_].dtype == object][:3]
        masks = pd.Series(True, index=df.index)
        for i, col in enumerate(text_cols):
            vals = sorted(df[col].dropna().unique().tolist())
            if len(vals) > 1:
                sel_vals = fc[i % 3].multiselect(col, vals)
                if sel_vals:
                    masks &= df[col].isin(sel_vals)
        view = df[masks]
        st.caption(f"Showing {len(view):,} of {len(df):,} rows")
        st.dataframe(view.head(5000), use_container_width=True, height=480)
        st.download_button("Export filtered CSV", view.to_csv(index=False).encode(),
                           file_name=f"{sel}.csv", mime="text/csv")
        end_card()

    st.write("")
    card("About the warehouse", "Data engineering notes")
    st.markdown("""
    - Raw CSVs are preserved untouched in `data/raw/` (728 MB events file).
    - The events fact table is processed in 200k-row chunks and reduced to
      pre-aggregated Parquet tables — the dashboard never loads 3.9M rows.
    - Tables are produced by `src/transformation/build_aggregates.py`.
    - `reports/dataset_inventory.csv` and `reports/data_quality_report.md`
      document profiling results.
    - DuckDB is the intended query engine; if unavailable the analytics layer
      falls back to Pandas/Parquet scans (all tables are small aggregates).
    """)
    end_card()
