"""Page 6 — City & Station Explorer."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.ui import card, end_card, fmt_inr, fmt_num, fmt_pct, page_title
from src.analytics import geo as geo
from src.analytics import network as net
from src.database import store
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("City & Station Explorer",
               "Six-city benchmarking, station map and underperformer detection")

    cc = geo.city_ranking(f["cities"], f["date_min"], f["date_max"])
    if cc.empty:
        st.warning("No data.")
        return

    c = st.columns(6)
    for i, (_, row) in enumerate(cc.iterrows()):
        with c[i]:
            st.metric(row["city"], fmt_pct(row["success_rate"]),
                      f"{fmt_num(row['attempts'])} attempts")

    st.write("")
    t1, t2 = st.tabs(["City comparison", "Station explorer"])

    with t1:
        card("City leaderboard", "Composite view: volume, success, revenue, failures")
        disp = cc.copy()
        for col in ["attempts", "completed", "failed_battery", "failed_system",
                    "abandoned", "cancelled", "revenue", "energy", "discount",
                    "list_price"]:
            if col in disp:
                disp[col] = disp[col].map(lambda v: f"{v:,.0f}")
        for col in ["success_rate", "battery_fail_rate", "system_fail_rate",
                    "abandon_rate", "rev_per_swap"]:
            if col in disp:
                disp[col] = disp[col].map(lambda v: f"{v:.3f}")
        disp = disp.rename(columns={
            "city": "City", "rank": "Rank", "stations": "Stations",
            "attempts": "Attempts", "completed": "Completed",
            "success_rate": "Success", "failed_battery": "Batt fail",
            "failed_system": "Sys fail", "abandoned": "Abandoned",
            "cancelled": "Cancelled", "revenue": "Revenue",
            "rev_per_swap": "Rev/swap", "avg_rev_per_swap": "Avg rev/swap",
            "energy": "Energy kWh", "discount": "Discount", "list_price": "List"})
        keep = [c_ for c_ in ["Rank", "City", "Stations", "Attempts", "Completed",
                             "Success", "Batt fail", "Sys fail", "Abandoned",
                             "Revenue", "Rev/swap", "Avg rev/swap"] if c_ in disp.columns]
        st.dataframe(disp[keep], use_container_width=True, hide_index=True,
                     height=340)
        end_card()

        c1, c2 = st.columns(2)
        with c1:
            card("Revenue vs success rate", "Each bubble = one city")
            fig = px.scatter(cc, x="success_rate", y="revenue", size="attempts",
                             color="city", text="city", size_max=50,
                             color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_traces(textposition="top center")
            fig.update_yaxes(tickprefix="₹", tickformat=",", gridcolor="#F1EFF6")
            fig.update_xaxes(ticksuffix="%", gridcolor="#F1EFF6")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            end_card()
        with c2:
            card("Failure composition by city", "Stacked failure types")
            comp = cc.melt(id_vars="city", value_vars=["failed_battery", "failed_system",
                                                      "abandoned", "cancelled"],
                           var_name="type", value_name="count")
            comp["type"] = comp["type"].map({
                "failed_battery": "No battery", "failed_system": "System",
                "abandoned": "Abandoned", "cancelled": "Cancelled"})
            fig = px.bar(comp, x="city", y="count", color="type", barmode="stack",
                         color_discrete_sequence=["#EF4444", "#F59E0B", VIOLET, TEAL])
            fig.update_layout(height=380, legend=dict(orientation="h", y=1.12),
                              yaxis=dict(gridcolor="#F1EFF6", tickformat=","),
                              xaxis=dict(gridcolor="#F1EFF6"))
            st.plotly_chart(fig, use_container_width=True)
            end_card()

    with t2:
        sm = geo.station_metrics(f["cities"], f["date_min"], f["date_max"])
        if sm.empty:
            st.info("No station metrics.")
        else:
            # filters
            fc1, fc2, fc3 = st.columns(3)
            cities_sel = fc1.multiselect("City", sorted(sm["city"].dropna().unique()),
                                         default=f["cities"] or [])
            min_att = fc2.slider("Min attempts", 10, 5000, 50, step=10)
            sort_by = fc3.selectbox("Sort by",
                                    ["risk_score", "failure_rate", "success_rate",
                                     "revenue", "attempts_per_slot_day" if "attempts_per_slot_day" in sm else "revenue"])
            view = sm[sm["attempts"] >= min_att].copy()
            if cities_sel:
                view = view[view["city"].isin(cities_sel)]
            if sort_by in view.columns:
                view = view.sort_values(sort_by, ascending=False)

            # map
            card("Station map", "Bubble size = attempts; colour = failure rate")
            m = view.dropna(subset=["latitude", "longitude"])
            if not m.empty:
                fig = px.scatter_map(
                    m, lat="latitude", lon="longitude", size="attempts",
                    color="failure_rate", size_max=18, zoom=4,
                    color_continuous_scale="RdYlGn_r",
                    hover_name="station_id", hover_data=["city", "success_rate", "revenue"],
                    map_style="carto-positron")
                fig.update_layout(height=460, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No geocoded stations for current filters.")
            end_card()

            card("Station table", f"{len(view)} stations · sorted by {sort_by}")
            disp = view.copy()
            for col in ["success_rate", "failure_rate", "abandon_rate",
                        "avg_queue_min", "failures_per_day"]:
                if col in disp:
                    disp[col] = disp[col].map(lambda v: f"{v:.3f}" if pd.notna(v) else "—")
            disp["revenue"] = disp["revenue"].map(lambda v: f"₹{v:,.0f}")
            disp["rev_per_swap"] = disp["rev_per_swap"].map(
                lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—")
            keep = [c_ for c_ in ["station_id", "city", "zone", "location_type",
                                 "charger_generation", "connectivity_tier",
                                 "slots_2w", "slots_3w", "attempts", "completed",
                                 "success_rate", "failure_rate", "abandon_rate",
                                 "avg_queue_min", "revenue", "rev_per_swap",
                                 "risk_score"] if c_ in disp.columns]
            disp = disp[keep].rename(columns={
                "station_id": "Station", "city": "City", "zone": "Zone",
                "location_type": "Type", "charger_generation": "Charger",
                "connectivity_tier": "Conn.", "slots_2w": "2W slots",
                "slots_3w": "3W slots", "attempts": "Attempts",
                "completed": "Completed", "success_rate": "Success",
                "failure_rate": "Fail rate", "abandon_rate": "Abandon",
                "avg_queue_min": "Queue min", "revenue": "Revenue",
                "rev_per_swap": "Rev/swap", "risk_score": "Risk"})
            st.dataframe(disp, use_container_width=True, height=480)
            st.download_button("Download station table",
                               view.to_csv(index=False).encode(),
                               file_name="station_metrics.csv", mime="text/csv")
            end_card()

            card("Underperforming stations", "Highest failure rate with meaningful volume")
            up = geo.underperformers(f["cities"], f["date_min"], f["date_max"], n=15)
            if not up.empty:
                show = up[["station_id", "city", "attempts", "failure_rate",
                           "abandon_rate", "avg_queue_min", "risk_score",
                           "connectivity_tier", "charger_generation"]].copy()
                show["failure_rate"] = show["failure_rate"].map(lambda v: f"{v:.1%}")
                show["abandon_rate"] = show["abandon_rate"].map(lambda v: f"{v:.1%}")
                show["avg_queue_min"] = show["avg_queue_min"].map(lambda v: f"{v:.1f}")
                show.columns = ["Station", "City", "Attempts", "Fail rate",
                                "Abandon", "Queue min", "Risk", "Conn.", "Charger"]
                st.dataframe(show, use_container_width=True, height=380, hide_index=True)
            end_card()
