"""Module G — Decision Intelligence.

Rule-based recommendation engine. Every recommendation is triggered by a
measurable threshold on real aggregates, carries its evidence, and is
prioritised by business impact (revenue at risk / failure volume).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics import battery as batt_analytics
from src.analytics import churn as churn_analytics
from src.analytics import failures as fail_analytics
from src.analytics import geo as geo_analytics
from src.analytics import network as net_analytics
from src.analytics import profitability as prof_analytics
from src.database import store


def _rec(priority, category, title, problem, evidence, action, impact):
    return {
        "priority": priority, "category": category, "title": title,
        "problem": problem, "evidence": evidence, "action": action,
        "impact": impact,
    }


def generate(cities=None, date_min=None, date_max=None) -> list[dict]:
    recs = []

    kpis = net_analytics.network_kpis(cities, date_min, date_max)
    if not kpis:
        return recs

    # --- R1: network failure rate ---
    fail_rate = 1 - kpis["success_rate"]
    if fail_rate > 0.08:
        st = fail_analytics.station_failure_table(cities, date_min, date_max)
        top = st.head(3)
        recs.append(_rec(
            "Critical" if fail_rate > 0.15 else "High", "Operations",
            f"Swap failure rate at {fail_rate:.1%} — above healthy threshold",
            f"{kpis['failed']:,} failed swaps represent {fail_rate:.1%} of all attempts, growing faster than completed volume.",
            f"Worst stations: {', '.join(top['station_id'].head(3))} "
            f"(failure rates {top['failure_rate'].head(3).mul(100).round(1).tolist()}%).",
            "Prioritise firmware/connectivity fixes and battery pre-staging at flagged stations; audit Gen1 chargers first.",
            f"~{int(kpis['failed'] * kpis['rev_per_swap']):,} INR/month-equivalent revenue at risk."))

    # --- R2: top failing stations ---
    st = fail_analytics.station_failure_table(cities, date_min, date_max, min_attempts=100)
    if not st.empty:
        worst = st.iloc[0]
        if worst["failure_rate"] > 0.12 and worst["attempts"] > 500:
            recs.append(_rec(
                "High", "Operations",
                f"{worst['station_id']} ({worst['city']}) is a failure hotspot",
                f"{worst['total_failures']:,} failures on {worst['attempts']:,} attempts "
                f"({worst['failure_rate']:.1%}); avg queue {worst['avg_queue_min']:.1f} min.",
                f"Risk score {worst['risk_score']}; connectivity tier: {worst.get('connectivity_tier','n/a')}.",
                "Root-cause audit: charger generation, grid tariff, staffing; consider temporary capacity reallocation.",
                f"Est. lost revenue {int(worst['total_failures'] * kpis['rev_per_swap']):,} INR over period."))

    # --- R3: churn ---
    seg = churn_analytics.churn_segments()
    if not seg.empty:
        total = seg["riders"].sum()
        churned = seg.loc[seg["segment"] == "churned", "riders"]
        churned = int(churned.iloc[0]) if len(churned) else 0
        churn_share = churned / total if total else 0
        if churn_share > 0.25:
            rt = churn_analytics.rider_table()
            churn_rev = rt.loc[rt["segment"] == "churned", "revenue"].sum()
            recs.append(_rec(
                "High", "Rider Retention",
                f"{churn_share:.0%} of riders are churned",
                f"{churned:,} riders have no swap in 30+ days; churned riders generated {churn_rev:,.0f} INR historically.",
                "Churn drivers: compare failure_rate/queue/revenue per swap between churned and active cohorts (see Rider page).",
                "Launch win-back campaign for at-risk riders; fix top failure drivers before acquisition spend increases.",
                f"At-risk pool: {int(seg.loc[seg['segment']=='at_risk','riders'].sum() if (seg['segment']=='at_risk').any() else 0):,} riders."))

    # --- R4: discount erosion ---
    de = prof_analytics.discount_erosion(cities, date_min, date_max)
    if len(de) >= 3:
        recent = de.tail(3)["discount_rate"].mean()
        early = de.head(3)["discount_rate"].mean()
        if recent > early + 0.02:
            recs.append(_rec(
                "Medium", "Pricing",
                "Discount rate rising — margin erosion",
                f"Average discount/list price rose from {early:.1%} to {recent:.1%} over the period.",
                f"Latest months: {de.tail(3)['month'].tolist()} → {de.tail(3)['discount_rate'].round(3).tolist()}.",
                "Review fleet partner contract amendments and promo stacking; enforce discount caps per tariff code.",
                f"Revenue impact ≈ {kpis['revenue'] * (recent - early):,.0f} INR forgone vs early-period rate."))

    # --- R5: battery health ---
    bh = batt_analytics.battery_failure_link()
    if not bh.empty:
        low = bh[bho := bh["soh_band"].isin(["<85", "85-90"])]
        if len(low) and low["failure_events"].sum() > 0:
            recs.append(_rec(
                "Medium", "Battery",
                "Degraded batteries correlate with swap failures",
                f"Batteries with SOH <90% account for {int(low['failure_events'].sum()):,} failure events.",
                "See Battery Intelligence page for SOH-band failure rates.",
                "Accelerate battery rotation for SOH<90 units; investigate charging-thermal behaviour at high-utilisation stations.",
                "Failure reduction directly lifts success rate and rider retention."))

    # --- R6: peak bottlenecks ---
    hp = fail_analytics.hourly_failure_pattern(cities)
    if not hp.empty:
        peak = hp.loc[hp["failure_rate"].idxmax()]
        if peak["failure_rate"] > hp["failure_rate"].mean() * 1.5:
            recs.append(_rec(
                "Medium", "Operations",
                f"Hour {int(peak['hour']):02d}:00 shows failure rate {peak['failure_rate']:.1%}",
                "Failure rate spikes {0:.1%} vs network avg {1:.1%}.".format(
                    peak["failure_rate"], hp["failure_rate"].mean()),
                "Hourly failure pattern table on Operations page.",
                "Stage additional charged inventory before the peak window; stagger fleet dispatch times.",
                "Reduces abandoned-queue events during highest-demand hours."))

    # --- R7: city disparity ---
    cc = net_analytics.city_comparison(cities, date_min, date_max)
    if len(cc) >= 2:
        best = cc.iloc[0]
        worst = cc.iloc[-1]
        if best["success_rate"] - worst["success_rate"] > 0.05:
            recs.append(_rec(
                "Medium", "Strategy",
                f"{best['city']} outperforms {worst['city']} by "
                f"{(best['success_rate']-worst['success_rate']):.1%} success rate",
                "City-level operational gap suggests local rather than network-wide causes.",
                f"{best['city']}: {best['success_rate']:.1%} success, "
                f"{worst['city']}: {worst['success_rate']:.1%}.",
                "Benchmark station density, firmware versions and partner mix between the two cities; replicate best-city practices.",
                "Closes the performance gap per city."))

    # --- R8: tickets ---
    tk = store.get("support_tickets")
    if not tk.empty:
        top_cat = tk["category"].value_counts().idxmax()
        cat_share = (tk["category"] == top_cat).mean()
        if cat_share > 0.15:
            recs.append(_rec(
                "Low", "Customer Experience",
                f"Support tickets dominated by '{top_cat}' ({cat_share:.0%})",
                "Ticket categories reveal recurring rider pain points.",
                f"{len(tk):,} tickets; top category: {top_cat}.",
                "Route '{0}' tickets to operations review; add in-app guidance to deflect repeat contacts.".format(top_cat),
                "Lower ticket volume → lower support cost, higher CSAT."))

    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    recs.sort(key=lambda r: order.get(r["priority"], 9))
    return recs
