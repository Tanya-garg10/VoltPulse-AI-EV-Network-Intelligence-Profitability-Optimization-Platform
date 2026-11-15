"""Page 5 — Profitability Analytics."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import (callout, card, end_card, expander, fmt_inr, fmt_num,
                           fmt_pct, page_title)
from src.analytics import profitability as prof
from src.analytics import network as net
from src.ui.theme import INDIGO, TEAL, VIOLET


def render(f):
    page_title("Profitability Analytics",
               "Revenue, pricing, discounts and estimated unit economics")

    kpis = net.network_kpis(f["cities"], f["date_min"], f["date_max"])
    if not kpis:
        st.warning("No data.")
        return

    callout("<b>Data limitation:</b> the dataset contains revenue-side fields "
            "(list price, discount, amount charged) but <b>no cost-per-swap, "
            "battery capex, or energy procurement cost</b>. Contribution figures "
            "below amortise station fixed costs (rent + maintenance) only and are "
            "labelled <b>estimates</b>. True margin requires cost data.", "warn")

    c = st.columns(4)
    c[0].metric("Total revenue", fmt_inr(kpis["revenue"]))
    c[1].metric("Rev / completed swap", fmt_inr(kpis["rev_per_swap"]))
    c[2].metric("Gross discount given", fmt_inr(kpis["discount_total"]))
    c[3].metric("Realization vs list", fmt_pct(
        1 - kpis["discount_total"] / kpis["list_price_total"]))

    st.write("")
    t1, t2, t3 = st.tabs(["Revenue & pricing", "City economics", "Fleet partners"])

    with t1:
        rt = prof.revenue_trend(f["cities"], f["date_min"], f["date_max"])
        if not rt.empty:
            card("Revenue vs discount rate", "Monthly revenue and discount erosion")
            fig = go.Figure()
            fig.add_bar(x=rt["month"], y=rt["revenue"], name="Revenue",
                        marker_color=TEAL)
            fig.add_scatter(x=rt["month"], y=rt["discount_rate"] * 100,
                            name="Discount rate %", yaxis="y2",
                            line=dict(color="#EF4444", width=2.5),
                            mode="lines+markers")
            fig.update_layout(barmode="overlay",
                              yaxis=dict(title="Revenue (₹)", tickprefix="₹",
                                         tickformat=",", gridcolor="#F1EFF6"),
                              yaxis2=dict(title="Discount %", overlaying="y",
                                          side="right", ticksuffix="%",
                                          gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=380)
            end_card()

        c1, c2 = st.columns(2)
        with c1:
            card("Tariff mix", "Revenue by tariff code")
            ta = prof.tariff_analysis(f["cities"], f["date_min"], f["date_max"])
            if not ta.empty:
                fig = go.Figure(go.Pie(
                    labels=ta["tariff_code"], values=ta["revenue"],
                    hole=0.55, marker_colors=[INDIGO, TEAL, VIOLET, "#F59E0B"],
                    textinfo="label+percent", hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>"))
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, height=320)
            end_card()
        with c2:
            card("Tariff economics", "Avg realised price per completed swap")
            if not ta.empty:
                fig = go.Figure(go.Bar(
                    x=ta["tariff_code"], y=ta["avg_price"],
                    marker_color=[INDIGO, TEAL, VIOLET, "#F59E0B"][:len(ta)],
                    text=ta["avg_price"].map(lambda v: f"₹{v:.0f}"),
                    textposition="outside",
                    hovertemplate="%{x}<br>₹%{y:.2f}<extra></extra>"))
                fig.update_yaxes(tickprefix="₹", gridcolor="#F1EFF6")
                fig.update_xaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=320)
                st.dataframe(ta.rename(columns={
                    "tariff_code": "Tariff", "events": "Events",
                    "completed": "Completed", "revenue": "Revenue",
                    "list_price": "List value", "discount": "Discount",
                    "avg_price": "Avg price", "share_revenue": "Rev share"}),
                    use_container_width=True, hide_index=True)
            end_card()

        card("Discount / realization trend", "Monthly discount rate and net realization")
        de = prof.discount_erosion(f["cities"], f["date_min"], f["date_max"])
        if not de.empty:
            fig = go.Figure()
            fig.add_scatter(x=de["month"], y=de["discount_rate"] * 100,
                            name="Discount rate", line=dict(color="#EF4444", width=2.5))
            fig.add_scatter(x=de["month"], y=de["net_realization"] * 100,
                            name="Net realization", line=dict(color=TEAL, width=2.5))
            fig.update_layout(yaxis=dict(ticksuffix="%", gridcolor="#F1EFF6"),
                              legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True, height=340)
        end_card()

    with t2:
        cp = prof.city_profitability(f["cities"], f["date_min"], f["date_max"])
        if not cp.empty:
            card("City unit economics", "Revenue, rev/swap, and estimated contribution "
                 "(revenue − amortised station rent & maintenance). ESTIMATE.")
            disp = cp.copy()
            for c_ in ["revenue", "est_fixed_cost", "est_contribution"]:
                disp[c_] = disp[c_].map(lambda v: f"₹{v:,.0f}")
            disp["rev_per_swap"] = disp["rev_per_swap"].map(lambda v: f"₹{v:,.0f}")
            disp["est_margin_pct"] = disp["est_margin_pct"].map(lambda v: f"{v:.1%}")
            disp = disp.rename(columns={
                "city": "City", "revenue": "Revenue", "completed": "Completed",
                "attempts": "Attempts", "energy": "Energy kWh",
                "stations": "Stations", "est_fixed_cost": "Est fixed cost",
                "est_contribution": "Est contribution", "rev_per_swap": "Rev/swap",
                "est_margin_pct": "Est margin %"})
            st.dataframe(disp, use_container_width=True, hide_index=True)
            end_card()

            c1, c2 = st.columns(2)
            with c1:
                card("Revenue by city", "")
                fig = go.Figure(go.Bar(x=cp["city"], y=cp["revenue"],
                                       marker_color=VIOLET,
                                       text=cp["revenue"].map(lambda v: f"₹{v/1e5:,.1f}L"),
                                       textposition="outside"))
                fig.update_yaxes(tickprefix="₹", tickformat=",", gridcolor="#F1EFF6")
                fig.update_xaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=320)
                end_card()
            with c2:
                card("Estimated margin by city", "Contribution after fixed station costs")
                fig = go.Figure(go.Bar(x=cp["city"], y=cp["est_margin_pct"] * 100,
                                       marker_color=[TEAL if v >= 0 else "#EF4444"
                                                     for v in cp["est_margin_pct"]],
                                       text=cp["est_margin_pct"].map(lambda v: f"{v:.1%}"),
                                       textposition="outside"))
                fig.update_yaxes(ticksuffix="%", gridcolor="#F1EFF6")
                fig.update_xaxes(gridcolor="#F1EFF6")
                st.plotly_chart(fig, use_container_width=True, height=320)
                end_card()

        ue = prof.station_unit_economics(f["cities"], f["date_min"], f["date_max"])
        if not ue.empty:
            card("Worst unit-economics stations", "Lowest estimated contribution "
                 "(est. fixed cost vs revenue). Estimates only.")
            show = ue.head(20).copy()
            for c_ in ["revenue", "est_fixed_cost", "est_contribution"]:
                show[c_] = show[c_].map(lambda v: f"₹{v:,.0f}")
            show["est_margin_pct"] = show["est_margin_pct"].map(lambda v: f"{v:.1%}")
            show = show.rename(columns={
                "station_id": "Station", "city": "City", "attempts": "Attempts",
                "completed": "Completed", "revenue": "Revenue",
                "est_fixed_cost": "Est fixed cost", "est_contribution": "Est contribution",
                "est_margin_pct": "Est margin", "rev_per_swap": "Rev/swap"})
            st.dataframe(show[["Station", "City", "Attempts", "Completed",
                               "Revenue", "Est fixed cost", "Est contribution",
                               "Est margin", "Rev/swap"]],
                         use_container_width=True, height=420, hide_index=True)
            end_card()

    with t3:
        fe = prof.fleet_economics(f["cities"])
        if fe.empty:
            st.info("No fleet partner data for filters.")
        else:
            card("Fleet partner economics",
                 "Partner-billed vs rider-paid revenue split from contract payment mode")
            disp = fe.copy()
            for c_ in ["partner_rev", "retail_rev", "total_rev"]:
                disp[c_] = disp[c_].map(lambda v: f"₹{v:,.0f}")
            disp["partner_share"] = disp["partner_share"].map(lambda v: f"{v:.1%}")
            disp = disp.rename(columns={
                "partner_id": "Partner", "partner_name": "Name",
                "partner_segment": "Segment", "vehicle_class": "Vehicle",
                "contract_type": "Contract", "discount_pct": "Disc %",
                "riders": "Riders", "partner_rev": "Partner-billed",
                "retail_rev": "Rider-paid", "total_rev": "Total rev",
                "completed": "Completed", "partner_share": "Partner share",
                "cities_active": "Cities", "payment_terms_days": "Terms (d)"})
            st.dataframe(disp[["Partner", "Name", "Segment", "Vehicle",
                               "Contract", "Disc %", "Riders", "Partner-billed",
                               "Rider-paid", "Total rev", "Completed",
                               "Partner share", "Cities", "Terms (d)"]],
                         use_container_width=True, height=420, hide_index=True)
            end_card()

            card("Partner revenue concentration", "Share of total revenue by partner")
            fig = go.Figure(go.Pie(
                labels=fe["partner_name"], values=fe["total_rev"], hole=0.55,
                textinfo="percent", hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>"))
            st.plotly_chart(fig, use_container_width=True, height=340)
            end_card()

    expander("Methodology & limitations",
             "Revenue = sum(amount_charged_inr) on swap_completed events only. "
             "List value = sum(list_price_inr); discounts = sum(discount_inr). "
             "Contribution margin is NOT available: no energy procurement, battery "
             "capex/lease, charger opex or labour cost fields exist. The 'estimated "
             "contribution' subtracts only amortised monthly_rent_inr + "
             "monthly_maintenance_inr over observed months — it overstates true "
             "margin. Fleet economics use payment_mode='partner_invoice' to split "
             "partner-billed vs rider-paid revenue.")
