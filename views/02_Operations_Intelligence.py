"""Page 2 — Operations Intelligence."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import card, end_card, fmt_num, fmt_pct, page_title
from src.analytics import failures as fail
from src.database import store
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("Operations Intelligence",
               "Failure modes, station bottlenecks, hourly patterns and downtime")

    # KPI strip
    st_tab = fail.station_failure_table(f["cities"], f["date_min"], f["date_max"])
    if st_tab.empty:
        st.warning("No station data for selected filters.")
        return
    c = st.columns(5)
    total_att = st_tab["attempts"].sum()
    total_fail = st_tab["total_failures"].sum()
    c[0].metric("Stations analysed", f"{len(st_tab)}")
    c[1].metric("Failure rate (network)", fmt_pct(total_fail / total_att))
    c[2].metric("Battery failures", fmt_num(st_tab["failed_battery"].sum()))
    c[3].metric("System failures", fmt_num(st_tab["failed_system"].sum()))
    c[4].metric("Abandoned queues", fmt_num(st_tab["abandoned"].sum()))

    st.write("")

    t1, t2, t3, t4 = st.tabs(["Failure trends", "Station risk", "Heatmaps & patterns", "Downtime & context"])

    with t1:
        card("Monthly failure composition", "Failed battery vs system vs abandoned vs cancelled")
        bf = fail.battery_vs_system_failures(f["cities"], f["date_min"], f["date_max"])
        if not bf.empty:
            fig = go.Figure()
            for col, name, color in [("battery", "No charged battery", "#EF4444"),
                                     ("system", "System error", "#F59E0B"),
                                     ("abandoned", "Abandoned queue", VIOLET),
                                     ("cancelled", "Cancelled by rider", TEAL)]:
                fig.add_bar(x=bf["month"], y=bf[col], name=name, marker_color=color)
            fig.update_layout(barmode="stack", yaxis=dict(tickformat=",", gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=380)
        end_card()

        card("Hourly failure pattern", "Failure share by hour of day (network)")
        hp = fail.hourly_failure_pattern(f["cities"])
        if not hp.empty:
            fig = go.Figure(go.Bar(x=hp["hour"].map(lambda h: f"{h:02d}:00"),
                                   y=hp["failure_rate"] * 100,
                                   marker_color=[INDIGO if v < hp["failure_rate"].mean() else "#EF4444"
                                                 for v in hp["failure_rate"]],
                                   hovertemplate="%{x}<br>%{y:.2f}%<extra></extra>"))
            fig.add_hline(y=hp["failure_rate"].mean() * 100, line_dash="dash",
                          line_color=TEAL, annotation_text="network avg")
            fig.update_yaxes(ticksuffix="%", gridcolor="#F1EFF6")
            fig.update_xaxes(gridcolor="#F1EFF6")
            st.plotly_chart(fig, use_container_width=True, height=320)
        end_card()

    with t2:
        card("Station risk ranking", "Composite risk = failure rate + abandon rate + queue time "
             "(min 100 attempts). Click column headers to sort.")
        cols = ["station_id", "city", "attempts", "failure_rate", "battery_fail_rate",
                "system_fail_rate", "abandon_rate", "avg_queue_min", "risk_score",
                "connectivity_tier", "charger_generation"]
        disp = st_tab[cols].copy()
        for c_ in ["failure_rate", "battery_fail_rate", "system_fail_rate",
                   "abandon_rate", "avg_queue_min", "risk_score"]:
            disp[c_] = disp[c_].map(lambda v: f"{v:.3f}")
        disp = disp.rename(columns={
            "station_id": "Station", "city": "City", "attempts": "Attempts",
            "failure_rate": "Fail rate", "battery_fail_rate": "Batt fail",
            "system_fail_rate": "Sys fail", "abandon_rate": "Abandon",
            "avg_queue_min": "Queue (min)", "risk_score": "Risk",
            "connectivity_tier": "Conn.", "charger_generation": "Charger"})
        st.dataframe(disp, use_container_width=True, height=520)
        end_card()

    with t3:
        card("Demand heatmap — hour × city", "Total events by hour-of-day and city")
        hm = fail.failure_heatmap(f["cities"])
        if not hm.empty:
            # hm: index=hour, columns=city → transpose so rows=cities, cols=hours
            hm_t = hm.T
            fig = go.Figure(go.Heatmap(
                z=hm_t.values, x=[f"{h:02d}:00" for h in hm.index],
                y=hm_t.index.tolist(), colorscale="Purples",
                colorbar=dict(title="Events"),
                hovertemplate="%{y} @ %{x}<br>%{z:,.0f} events<extra></extra>"))
            st.plotly_chart(fig, use_container_width=True, height=360)
        end_card()
        card("Station × day-of-week × hour bottlenecks",
             "Top stations by attempts during their worst dow/hour cell")
        sdh = store.get("station_dow_hour")
        if not sdh.empty:
            sdh = sdh.copy()
            sdh["fail_rate"] = (sdh["failed_battery"] + sdh["failed_system"]) / sdh["attempts"].replace(0, pd.NA)
            # worst cell per station
            worst = sdh.sort_values("fail_rate", ascending=False).groupby("station_id").head(1)
            worst = worst.merge(store.get("stations")[["station_id", "city"]], on="station_id", how="left")
            if f["cities"]:
                worst = worst[worst["city"].isin(f["cities"])]
            show = worst.nlargest(15, "fail_rate")[
                ["station_id", "city", "dow", "hour", "attempts", "fail_rate"]].copy()
            show["dow"] = show["dow"].map({0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"})
            show["fail_rate"] = show["fail_rate"].map(lambda v: f"{v:.1%}" if pd.notna(v) else "—")
            show.columns = ["Station", "City", "Day", "Hour", "Attempts", "Fail rate"]
            st.dataframe(show, use_container_width=True, height=380)
        end_card()

    with t4:
        card("Proxy downtime — stations with zero-completed-swap days",
             "Days where a station recorded attempts but zero completions")
        dz = fail.downtime_analysis(f["cities"], f["date_min"], f["date_max"])
        if not dz.empty:
            st.dataframe(dz.head(15), use_container_width=True, height=340)
        end_card()
        card("Environmental correlates of failure rate",
             "Correlation of city-day context features with daily failure rate")
        corr = fail.context_correlations(f["cities"])
        if not corr.empty:
            fig = go.Figure(go.Bar(
                x=corr["feature"], y=corr["correlation"],
                marker_color=[TEAL if v >= 0 else "#EF4444" for v in corr["correlation"]],
                hovertemplate="%{x}<br>r=%{y:.3f}<extra></extra>"))
            fig.update_layout(yaxis=dict(gridcolor="#F1EFF6", zeroline=True))
            st.plotly_chart(fig, use_container_width=True, height=320)
        end_card()
