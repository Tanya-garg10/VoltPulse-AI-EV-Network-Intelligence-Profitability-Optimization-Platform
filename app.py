"""VoltPulse AI — application entry point.

Run:  streamlit run app.py
"""
import os
import sys
from pathlib import Path

# Cap native thread pools — the analytics stack is small-data; unbounded
# OpenBLAS threads can exhaust memory on constrained machines.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from components.ui import (callout, end_card, card, download_button, fmt_inr,
                           fmt_num, fmt_pct, header, inject_theme, kpi,
                           page_title)
from src.database import store
from src.ui.theme import CSS

st.set_page_config(
    page_title="VoltPulse AI — EV Network Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    ("Executive Overview", "01_Executive_Overview", "▦"),
    ("Operations Intelligence", "02_Operations_Intelligence", "⚙"),
    ("Rider Intelligence", "03_Rider_Intelligence", "🚴"),
    ("Battery Intelligence", "04_Battery_Intelligence", "🔋"),
    ("Profitability Analytics", "05_Profitability_Analytics", "₹"),
    ("City & Station Explorer", "06_City_Station_Explorer", "🗺"),
    ("Decision Center", "07_Decision_Center", "🎯"),
    ("Data Explorer", "08_Data_Explorer", "🗄"),
]


def sidebar_nav() -> str:
    st.sidebar.markdown(
        "<div style='padding:6px 4px 8px 4px'>"
        "<div style='display:flex;align-items:center;gap:10px'>"
        "<div style='width:36px;height:36px;border-radius:11px;"
        "background:linear-gradient(135deg,#4F46E5,#7C3AED);display:flex;"
        "align-items:center;justify-content:center;color:#fff;font-weight:800;"
        "font-size:17px;font-family:Sora;box-shadow:0 4px 12px rgba(79,70,229,.45)'>⚡</div>"
        "<div>"
        "<div style='font-family:Sora;font-size:20px;font-weight:800;color:#fff;"
        "letter-spacing:-.02em;line-height:1.1'>VoltPulse AI</div>"
        "<div style='font-size:10.5px;color:#9C97C4;letter-spacing:.06em;"
        "text-transform:uppercase;font-weight:600;margin-top:2px'>"
        "EV Network Intelligence</div>"
        "</div></div>"
        "<div style='margin-top:12px;padding:10px 12px;border-radius:12px;"
        "background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1)'>"
        "<div style='font-size:10px;font-weight:700;letter-spacing:.08em;"
        "text-transform:uppercase;color:#9C97C4;margin-bottom:5px'>"
        "VoltRelay Energy · Live dataset</div>"
        "<div style='font-size:11.5px;color:#D6D3F5;line-height:1.65'>"
        "3.88M swap events · 152 stations<br>"
        "6 cities · 20K riders · 12 partners<br>"
        "Jan 2024 – Jun 2025</div></div></div>",
        unsafe_allow_html=True)
    st.sidebar.markdown(
        "<div style='font-size:10px;font-weight:700;letter-spacing:.1em;"
        "text-transform:uppercase;color:#9C97C4;padding:4px 4px 8px 4px'>"
        "Workspace</div>",
        unsafe_allow_html=True)
    if "page" not in st.session_state:
        st.session_state.page = PAGES[0][1]
    for label, module, icon in PAGES:
        if module == "07_Decision_Center":
            st.sidebar.markdown(
                "<div style='font-size:10px;font-weight:700;letter-spacing:.1em;"
                "text-transform:uppercase;color:#9C97C4;padding:14px 4px 6px 4px'>"
                "Decisions & Data</div>", unsafe_allow_html=True)
        active = st.session_state.page == module
        btn = st.sidebar.button(
            f"{icon}  {label}",
            use_container_width=True,
            type="primary" if active else "secondary",
            key=f"nav_{module}")
        if btn:
            st.session_state.page = module
            st.rerun()
    st.sidebar.markdown(
        "<div style='margin-top:16px;padding:12px;border-radius:12px;"
        "background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1)'>"
        "<div style='font-size:10.5px;font-weight:700;letter-spacing:.08em;"
        "text-transform:uppercase;color:#9C97C4;margin-bottom:6px'>"
        "Gradient Learnings</div>"
        "<div style='font-size:12px;color:#D6D3F5;line-height:1.6'>"
        "Data Analytics Hackathon<br>Evidence-backed BI for VoltRelay</div></div>",
        unsafe_allow_html=True)
    return st.session_state.page


def global_filters() -> dict:
    """Top filter bar; returns filter dict used by all pages."""
    dc = store.get("daily_city")
    if dc.empty:
        return {"cities": None, "date_min": None, "date_max": None,
                "stations": None}
    dates = pd.to_datetime(dc["date"])
    dmin, dmax = dates.min().date(), dates.max().date()

    cities_all = store.city_filter_options()
    lc, bc = st.columns([6, 1])
    with lc:
        st.markdown(
            '<div class="vp-tag" style="margin-bottom:2px">Global filters — '
            'apply to every page</div>', unsafe_allow_html=True)
    with bc:
        if st.button("Clear filters", use_container_width=True,
                     type="primary", key="clear_filters"):
            st.session_state["f_cities"] = cities_all
            st.session_state["f_daterange"] = (dmin, dmax)
            st.session_state["f_stations"] = []
            st.rerun()
    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        cities = st.multiselect("Cities", cities_all,
                                default=st.session_state.get("f_cities", cities_all),
                                key="f_cities")
    with c2:
        dr = st.date_input("Date range", value=(dmin, dmax),
                           min_value=dmin, max_value=dmax, key="f_daterange")
        date_min = str(dr[0]) if isinstance(dr, tuple) and dr else str(dmin)
        date_max = str(dr[1]) if isinstance(dr, tuple) and dr else str(dmax)
    with c3:
        stations_all = sorted(store.get("stations")["station_id"].tolist())
        stations = st.multiselect("Stations", stations_all,
                                  default=st.session_state.get("f_stations", []),
                                  key="f_stations")
    return {"cities": cities or None, "date_min": date_min, "date_max": date_max,
            "stations": stations or None}


def main() -> None:
    inject_theme()
    page_module = sidebar_nav()
    filters = global_filters()

    import importlib
    mod = importlib.import_module(f"views.{page_module}")
    mod.render(filters)


if __name__ == "__main__":
    main()
