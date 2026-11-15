"""Page 1 — Executive Overview."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import (callout, card, end_card, fmt_inr, fmt_num, fmt_pct,
                           kpi, page_title)
from src.analytics import network as net
from src.analytics.filters import monthly
from src.database import store
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("Executive Overview",
               "Network-wide swap performance, growth and revenue trajectory")

    kpis = net.network_kpis(f["cities"], f["date_min"], f["date_max"])
    if not kpis:
        st.warning("No data for selected filters.")
        return

    # KPI row
    c = st.columns(6)
    kpi("Swap attempts", fmt_num(kpis["attempts"]), "all events incl. failures")
    kpi("Completed swaps", fmt_num(kpis["completed"]),
        f"{fmt_num(kpis['failed'])} failed · {fmt_num(kpis['abandoned'])} abandoned")
    kpi("Success rate", fmt_pct(kpis["success_rate"]),
        "completed / attempts", accent=TEAL if kpis["success_rate"] > 0.9 else "#F59E0B")
    kpi("Revenue", fmt_inr(kpis["revenue"]),
        f"{fmt_inr(kpis['list_price_total'])} list value")
    kpi("Rev / completed swap", fmt_inr(kpis["rev_per_swap"]),
        f"avg discount {fmt_inr(kpis['discount_total'])}")
    kpi("Energy delivered", f"{kpis['energy_kwh']/1000:,.1f} MWh",
        f"{kpis['active_days']} active days")

    st.write("")

    # Monthly trend
    mt = net.monthly_trend(f["cities"], f["date_min"], f["date_max"])
    if not mt.empty:
        card("Monthly network performance", "Attempts vs completed swaps and success rate")
        fig = go.Figure()
        fig.add_bar(x=mt["month"], y=mt["attempts"], name="Attempts",
                    marker_color="#C7D2FE", opacity=0.7)
        fig.add_bar(x=mt["month"], y=mt["completed"], name="Completed",
                    marker_color=INDIGO)
        fig.add_scatter(x=mt["month"], y=mt["success_rate"] * 100,
                        name="Success %", yaxis="y2", line=dict(color=TEAL, width=2.5))
        fig.update_layout(barmode="overlay",
                          yaxis=dict(title="Swaps", tickformat=",", gridcolor="#F1EFF6"),
                          yaxis2=dict(title="Success %", overlaying="y", side="right",
                                      ticksuffix="%", range=[50, 100], gridcolor="#F1EFF6"),
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True, height=400)
        end_card()

    c1, c2 = st.columns(2)
    with c1:
        # City comparison
        cc = net.city_comparison(f["cities"], f["date_min"], f["date_max"])
        if not cc.empty:
            card("City performance", "Attempts share and success rate")
            fig = go.Figure()
            fig.add_bar(x=cc["city"], y=cc["attempts"], name="Attempts",
                        marker_color=VIOLET, opacity=0.85,
                        text=cc["attempts"].map(lambda v: f"{v/1000:.0f}K"),
                        textposition="outside")
            fig.add_scatter(x=cc["city"], y=cc["success_rate"] * 100,
                            name="Success %", yaxis="y2",
                            line=dict(color=TEAL, width=3),
                            mode="lines+markers")
            fig.update_layout(barmode="overlay",
                              yaxis=dict(title="Attempts", gridcolor="#F1EFF6"),
                              yaxis2=dict(title="Success %", overlaying="y", side="right",
                                          ticksuffix="%", range=[0, 100], gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=340)
            end_card()
    with c2:
        # Revenue by month
        if not mt.empty:
            card("Revenue trajectory", "Monthly recognized revenue")
            fig = go.Figure(go.Scatter(
                x=mt["month"], y=mt["revenue"], mode="lines+markers",
                line=dict(color=TEAL, width=3),
                fill="tozeroy", fillcolor="rgba(13,148,136,0.08)",
                hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"))
            fig.update_yaxes(tickprefix="₹", tickformat=",", gridcolor="#F1EFF6")
            fig.update_xaxes(gridcolor="#F1EFF6")
            st.plotly_chart(fig, use_container_width=True, height=340)
            end_card()

    # Insights
    st.write("")
    card("Executive insights", "Auto-generated from filtered data")
    dc = store.get("daily_city")
    insights = []
    if not mt.empty and len(mt) > 2:
        last = mt.iloc[-1]; prev = mt.iloc[-2]
        growth = (last["completed"] - prev["completed"]) / prev["completed"] if prev["completed"] else 0
        insights.append(f"Completed swaps {fmt_pct(growth,1)} MoM in {last['month']} "
                        f"({fmt_num(prev['completed'])} → {fmt_num(last['completed'])}).")
        fail_trend = last["success_rate"] - prev["success_rate"]
        insights.append(f"Success rate moved {fmt_pct(fail_trend,2)} MoM — "
                        + ("improving." if fail_trend > 0 else "deteriorating; see Operations page."))
    if kpis["rev_per_swap"]:
        insights.append(f"Average revenue per completed swap is {fmt_inr(kpis['rev_per_swap'])}; "
                        f"discounts totalled {fmt_inr(kpis['discount_total'])} "
                        f"({fmt_pct(kpis['discount_total']/kpis['list_price_total'],1)} of list value).")
    cc = net.city_comparison(f["cities"], f["date_min"], f["date_max"])
    if not cc.empty:
        insights.append(f"Largest network: {cc.iloc[0]['city']} ({fmt_num(cc.iloc[0]['attempts'])} attempts); "
                        f"highest success: {cc.loc[cc['success_rate'].idxmax(),'city']} "
                        f"({fmt_pct(cc['success_rate'].max())}).")
    for i in insights:
        callout(i)
    end_card()
