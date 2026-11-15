"""Page 3 — Rider Intelligence."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import card, end_card, expander, fmt_inr, fmt_num, fmt_pct, page_title
from src.analytics import churn as ch
from src.analytics import models as ml
from src.database import store
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("Rider Intelligence",
               "Acquisition, retention, churn drivers and predictive risk scoring")

    rt = ch.rider_table()
    if rt.empty:
        st.warning("No rider data.")
        return
    if f["cities"]:
        rt = rt[rt["home_city"].isin(f["cities"])]

    seg = ch.churn_segments()
    total_riders = int(seg["riders"].sum()) if not seg.empty else len(rt)
    churned = int(seg.loc[seg["segment"] == "churned", "riders"].sum()) if not seg.empty else 0
    at_risk = int(seg.loc[seg["segment"] == "at_risk", "riders"].sum()) if not seg.empty else 0

    c = st.columns(4)
    c[0].metric("Total riders", f"{total_riders:,}")
    c[1].metric("Active (<8d)", f"{int(seg.loc[seg['segment']=='active','riders'].sum()) if not seg.empty else 0:,}")
    c[2].metric("At risk (8–30d)", f"{at_risk:,}")
    c[3].metric("Churned (30d+)", f"{churned:,}",
                delta=f"{churned/total_riders:.0%} of base" if total_riders else "")

    st.write("")
    t1, t2, t3 = st.tabs(["Segments & drivers", "Cohorts & acquisition", "Churn prediction"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            card("Lifecycle segments", "Operational definition: churned = no swap in final 30 days "
                 "of the data window and rider age ≥45 days.")
            if not seg.empty:
                fig = go.Figure(go.Bar(
                    x=seg["segment"], y=seg["riders"],
                    marker_color=[TEAL, "#F59E0B", "#EF4444", INDIGO][:len(seg)],
                    text=seg["riders"].map(lambda v: f"{v:,}"), textposition="outside"))
                fig.update_yaxes(gridcolor="#F1EFF6", tickformat=",")
                fig.update_xaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=320)
            end_card()
        with c2:
            card("Segment economics", "Average completed swaps, revenue and failure rate")
            if not seg.empty:
                disp = seg.rename(columns={
                    "segment": "Segment", "riders": "Riders",
                    "avg_completed": "Avg swaps", "avg_revenue": "Avg revenue",
                    "avg_swaps_per_week": "Swaps/wk", "avg_failure_rate": "Fail rate",
                    "avg_queue_min": "Queue min"})
                for c_ in ["Avg swaps", "Avg revenue", "Swaps/wk", "Fail rate", "Queue min"]:
                    disp[c_] = disp[c_].map(lambda v: f"{v:,.2f}")
                st.dataframe(disp, use_container_width=True, height=300)
            end_card()

        card("Churn vs active — feature comparison",
             "Mean values per rider by segment; larger gaps indicate churn drivers")
        drv = ch.churn_drivers()
        if not drv.empty:
            fig = go.Figure()
            for segname, color in [("churned", "#EF4444"), ("active", TEAL), ("at_risk", "#F59E0B")]:
                if segname in drv.columns:
                    fig.add_bar(x=drv["feature"], y=drv[segname], name=segname,
                                marker_color=color)
            fig.update_layout(barmode="group", yaxis=dict(gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12), height=380)
            st.plotly_chart(fig, use_container_width=True)
        end_card()

        expander("Methodology",
                 "Churn is defined operationally, not by a cancellation flag (none exists): "
                 "a rider is churned when their last swap precedes the dataset end by ≥30 days "
                 "and they are ≥45 days past first swap (excludes new riders in trial window). "
                 "At-risk = recency 8–30 days. Active = recency <8 days.")

    with t2:
        card("New rider acquisition by month", "Riders whose first swap occurred in each month")
        acq = ch.acquisition_retention(f["cities"])
        if not acq.empty:
            fig = go.Figure(go.Bar(x=acq["month"], y=acq["new_riders"],
                                   marker_color=VIOLET, name="New riders"))
            fig.update_yaxes(gridcolor="#F1EFF6", tickformat=",")
            fig.update_xaxes(gridcolor="#F1EFF6")
            st.plotly_chart(fig, use_container_width=True, height=300)
        end_card()

        card("Retention proxy by signup cohort",
             "Share of each signup cohort still active at 30/60/90/180 days "
             "(measured by swap tenure — riders with no activity events in between are "
             "not individually observable at monthly grain)")
        coh = ch.cohort_retention()
        if not coh.empty:
            coh = coh.tail(12)
            fig = go.Figure()
            for m, color in [("m1", TEAL), ("m2", INDIGO), ("m3", VIOLET), ("m6", "#F59E0B")]:
                fig.add_bar(x=coh["cohort"], y=coh[m] * 100, name=m.upper(),
                            marker_color=color)
            fig.update_layout(barmode="group", yaxis=dict(ticksuffix="%", gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=340)
            st.dataframe(coh.rename(columns={
                "cohort": "Cohort", "riders": "Riders", "m1": "M1 (30d)",
                "m2": "M2 (60d)", "m3": "M3 (90d)", "m6": "M6 (180d)"}),
                use_container_width=True, hide_index=True)
        end_card()

        card("Repeat usage distribution", "Completed swaps per rider")
        bins = [0, 1, 5, 10, 25, 50, 100, 500, 10000]
        labels = ["1", "2-5", "6-10", "11-25", "26-50", "51-100", "101-500", "500+"]
        rt2 = rt.copy()
        rt2["usage_band"] = pd.cut(rt2["completed"], bins=bins, labels=labels)
        ub = rt2.groupby("usage_band", observed=True).agg(
            riders=("rider_id", "nunique")).reset_index()
        fig = go.Figure(go.Bar(x=ub["usage_band"].astype(str), y=ub["riders"],
                               marker_color=INDIGO,
                               text=ub["riders"].map(lambda v: f"{v:,}"),
                               textposition="outside"))
        fig.update_yaxes(gridcolor="#F1EFF6", tickformat=",")
        fig.update_xaxes(gridcolor="#F1EFF6", title="Completed swaps")
        st.plotly_chart(fig, use_container_width=True, height=300)
        end_card()

    with t3:
        with st.spinner("Training churn model…"):
            res = ml.train_churn_model()
        if res.get("status") != "ok":
            st.warning(f"Churn model unavailable: {res.get('status')} "
                       f"(n={res.get('n','?')}). Insufficient labelled data or features.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ROC-AUC", f"{res['auc']:.3f}")
            c2.metric("Accuracy", f"{res['accuracy']:.3f}")
            c3.metric("F1", f"{res['f1']:.3f}")
            c4.metric("Train / test", f"{res['n_train']:,} / {res['n_test']:,}")
            st.caption(res["definition"])

            c1, c2 = st.columns(2)
            with c1:
                card("Feature importance", "Permutation importance on held-out test set")
                imp = res["importance"].head(10)
                fig = go.Figure(go.Bar(
                    x=imp["importance"], y=imp["feature"], orientation="h",
                    marker_color=TEAL, hovertemplate="%{y}: %{x:.4f}<extra></extra>"))
                fig.update_xaxes(gridcolor="#F1EFF6")
                fig.update_yaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=360)
                end_card()
            with c2:
                card("Predicted churn risk distribution",
                     "Model scores for all scored riders")
                scored = res["scored"]
                fig = go.Figure(go.Histogram(x=scored["churn_probability"] * 100,
                                             nbinsx=40, marker_color=VIOLET,
                                             opacity=0.85))
                fig.update_xaxes(title="Churn probability %", gridcolor="#F1EFF6")
                fig.update_yaxes(gridcolor="#F1EFF6", title="Riders")
                st.plotly_chart(fig, use_container_width=True, height=360)
                end_card()

            card("High-risk rider cohort", "Top decile of predicted churn probability")
            top = scored.nlargest(200, "churn_probability")
            disp = top[["rider_id", "home_city", "partner_id", "revenue",
                        "completed", "churn_probability", "risk_band", "segment"]].copy()
            disp["churn_probability"] = disp["churn_probability"].map(lambda v: f"{v:.1%}")
            disp["revenue"] = disp["revenue"].map(lambda v: f"₹{v:,.0f}")
            st.dataframe(disp, use_container_width=True, height=360)
            st.download_button("Download risk scores",
                               scored.to_csv(index=False).encode(),
                               file_name="churn_risk_scores.csv", mime="text/csv")
            end_card()
