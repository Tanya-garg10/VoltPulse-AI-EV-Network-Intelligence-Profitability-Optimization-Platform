"""Page 7 — Decision Center."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import card, end_card, fmt_inr, fmt_num, fmt_pct, page_title
from src.analytics import models as ml
from src.analytics import network as net
from src.recommendations import engine
from src.ui.theme import INDIGO, TEAL

PRIORITY_COLOR = {"Critical": "#DC2626", "High": "#EA580C",
                  "Medium": "#CA8A04", "Low": "#2563EB"}


def render(f):
    page_title("Decision Center",
               "Evidence-backed recommendations prioritised by measurable impact")

    recs = engine.generate(f["cities"], f["date_min"], f["date_max"])
    if not recs:
        st.warning("No recommendations could be generated for the current filters.")
        return

    # summary strip
    counts = pd.Series([r["priority"] for r in recs]).value_counts()
    c = st.columns(4)
    for i, p in enumerate(["Critical", "High", "Medium", "Low"]):
        c[i].metric(p, int(counts.get(p, 0)))

    st.write("")

    for i, r in enumerate(recs, 1):
        color = PRIORITY_COLOR.get(r["priority"], "#64748B")
        st.markdown(f"""
        <div class="vp-card" style="border-left:5px solid {color}; margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <span class="vp-badge {'critical' if r['priority']=='Critical' else 'high' if r['priority']=='High' else 'medium' if r['priority']=='Medium' else 'low'}">{r['priority'].upper()}</span>
              <span style="font-size:11px;color:#6B6780;font-weight:700;letter-spacing:.06em;margin-left:8px">{r['category'].upper()}</span>
            </div>
            <div style="font-family:Sora;font-weight:800;color:#1E1B2E">#{i}</div>
          </div>
          <h3 style="margin-top:10px">{r['title']}</h3>
          <p style="font-size:13px;color:#3F3D56;margin:6px 0 10px 0">{r['problem']}</p>
          <div style="background:#F6F4FB;border-radius:10px;padding:10px 14px;font-size:12.5px;color:#312E81;margin-bottom:10px">
            <b>Evidence:</b> {r['evidence']}
          </div>
          <div style="font-size:13px;color:#1E1B2E"><b>Recommended action:</b> {r['action']}</div>
          <div style="font-size:12px;color:#0D9488;font-weight:600;margin-top:6px">Impact: {r['impact']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Action plan table
    card("Prioritised action plan", "Sorted by priority; impact quantified only where data supports it")
    plan = pd.DataFrame([{
        "Priority": r["priority"], "Category": r["category"],
        "Recommendation": r["title"], "Expected impact": r["impact"],
    } for r in recs])
    st.dataframe(plan, use_container_width=True, hide_index=True, height=320)
    end_card()

    # Forecast snapshot
    with st.spinner("Running demand forecast…"):
        fc = ml.demand_forecast(horizon_days=30)
    if fc.get("status") == "ok":
        card("Demand outlook — next 30 days",
             f"Linear trend + annual seasonality model. "
             f"Test MAE {fc['mae_model']:,.0f} vs naive {fc['mae_naive']:,.0f} "
             f"({'model better' if fc['model_beats_naive'] else 'naive baseline better — forecast shown for directional use only'}).")
        fut = fc["future"].copy()
        hist_tail = fc["history"].tail(60)
        fig = go.Figure()
        fig.add_scatter(x=hist_tail["date"], y=hist_tail["actual"],
                        name="Actual (last 60d)", line=dict(color=INDIGO, width=2))
        fig.add_scatter(x=fut["date"], y=fut["forecast_completed"],
                        name="Forecast", line=dict(color=TEAL, width=2.5, dash="dash"))
        fig.update_yaxes(tickformat=",", gridcolor="#F1EFF6", title="Completed swaps/day")
        fig.update_xaxes(gridcolor="#F1EFF6")
        fig.update_layout(legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True, height=340)
        end_card()
        st.caption("Forecasts are model outputs, not observations. Evaluate before "
                   "using for capacity planning.")
    else:
        st.info(f"Demand forecast unavailable ({fc.get('status')}).")
