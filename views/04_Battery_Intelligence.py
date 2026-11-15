"""Page 4 — Battery Intelligence."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import card, end_card, expander, fmt_num, fmt_pct, page_title
from src.analytics import battery as batt
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("Battery Intelligence",
               "Fleet health, degradation, utilisation and failure exposure")
    bt = batt.battery_table()
    if bt.empty:
        st.warning("No battery data.")
        return
    if f["cities"]:
        # batteries have no city; filter is not directly applicable — note it
        st.caption("Battery-level filters by city are not applicable; "
                   "battery assets are pooled network-wide.")

    total = len(bt)
    avg_soh = bt["soh_mean"].mean()
    degraded = (bt["soh_mean"] < 90).sum()
    high_fail = bt["failure_rate"].quantile(0.9)

    c = st.columns(4)
    c[0].metric("Batteries tracked", f"{total:,}")
    c[1].metric("Avg SOH", f"{avg_soh:.1f}%")
    c[2].metric("Degraded (SOH<90)", f"{degraded:,}",
                delta=f"{degraded/total:.0%} of fleet")
    c[3].metric("Failure-exposed", f"{(bt['failure_events'].fillna(0)>0).sum():,}")

    st.write("")
    t1, t2 = st.tabs(["Health & degradation", "Failures & utilisation"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            card("SOH distribution", "Mean state-of-health per battery")
            hd = batt.health_distribution()
            if not hd.empty:
                fig = go.Figure(go.Bar(x=hd["soh_band"].astype(str), y=hd["batteries"],
                                       marker_color=VIOLET,
                                       text=hd["batteries"].map(lambda v: f"{v:,}"),
                                       textposition="outside"))
                fig.update_yaxes(gridcolor="#F1EFF6", tickformat=",")
                fig.update_xaxes(gridcolor="#F1EFF6", title="SOH band")
                st.plotly_chart(fig, use_container_width=True, height=340)
            end_card()
        with c2:
            card("Degradation by battery age",
                 "Average SOH declines with asset age (proxy for degradation)")
            dg = batt.degradation_by_age()
            if not dg.empty:
                fig = go.Figure()
                fig.add_bar(x=dg["age_band"].astype(str), y=dg["avg_soh"],
                            name="Avg SOH", marker_color=TEAL)
                fig.add_scatter(x=dg["age_band"].astype(str), y=dg["avg_min_soh"],
                                name="Avg min SOH", mode="lines+markers",
                                line=dict(color="#EF4444", width=2))
                fig.update_layout(barmode="overlay", yaxis=dict(gridcolor="#F1EFF6"),
                                  legend=dict(orientation="h", y=1.12))
                st.plotly_chart(fig, use_container_width=True, height=340)
            end_card()

        card("Vehicle-class segmentation", "2W vs 3W battery packs")
        sp = batt.supplier_performance()
        if not sp.empty:
            fig = go.Figure()
            for col, name, color in [("avg_soh", "Avg SOH", TEAL),
                                     ("failure_rate", "Failure rate", "#EF4444"),
                                     ("avg_swaps", "Avg swaps", VIOLET)]:
                fig.add_bar(x=sp["vehicle_class"].astype(str), y=sp[col],
                            name=name, marker_color=color, opacity=0.85)
            fig.update_layout(barmode="group", yaxis=dict(gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=340)
            st.dataframe(sp, use_container_width=True, hide_index=True)
        end_card()
        expander("Note on 'supplier performance'",
                 "The dataset does not contain a battery supplier/manufacturer field. "
                 "Battery IDs encode vehicle class (BAT-2W-…, BAT-3W-…). Supplier-level "
                 "analysis is therefore limited to vehicle-class segmentation; this is "
                 "documented as a data limitation rather than fabricated.")

    with t2:
        card("SOH band vs failure exposure",
             "Do degraded batteries fail more? Failure events per battery observed in failed_* events")
        bf = batt.battery_failure_link()
        if not bf.empty:
            fig = go.Figure()
            fig.add_bar(x=bf["soh_band"].astype(str), y=bf["failure_events"],
                        name="Failure events", marker_color="#EF4444")
            fig.add_scatter(x=bf["soh_band"].astype(str), y=bf["failure_rate"] * bf["batteries"],
                            name="Failure rate × fleet", mode="lines+markers",
                            line=dict(color=INDIGO, width=2.5))
            fig.update_layout(yaxis=dict(gridcolor="#F1EFF6", title="Count"),
                              xaxis=dict(title="SOH band"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=360)
            st.dataframe(bf, use_container_width=True, hide_index=True)
        end_card()

        c1, c2 = st.columns(2)
        with c1:
            card("Utilisation distribution", "Swaps per battery per active day")
            ud = batt.utilization_distribution()
            if not ud.empty:
                fig = go.Figure(go.Bar(x=ud["util_band"].astype(str), y=ud["batteries"],
                                       marker_color=VIOLET,
                                       text=ud["batteries"].map(lambda v: f"{v:,}"),
                                       textposition="outside"))
                fig.update_yaxes(gridcolor="#F1EFF6", tickformat=",")
                fig.update_xaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=320)
            end_card()
        with c2:
            card("Lowest-SOH batteries", "Worst 20 assets by mean SOH — rotation candidates")
            worst = bt.nsmallest(20, "soh_mean")[
                ["battery_id", "vehicle_class", "swaps_total", "soh_mean",
                 "soh_min", "failure_events", "avg_soc_out"]].copy()
            worst["failure_events"] = worst["failure_events"].fillna(0).astype(int)
            st.dataframe(worst, use_container_width=True, height=340,
                         hide_index=True)
            st.download_button("Download battery health table",
                               bt.to_csv(index=False).encode(),
                               file_name="battery_health.csv", mime="text/csv")
            end_card()
