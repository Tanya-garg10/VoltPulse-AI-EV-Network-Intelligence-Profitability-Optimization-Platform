"""Reusable premium UI components."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui.theme import CSS, INDIGO, PALETTE, PLOTLY_LAYOUT, TEAL, VIOLET


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(subtitle: str = "EV Network Intelligence & Profitability Optimization") -> None:
    st.markdown(f"""
    <div class="vp-header">
      <div>
        <div class="vp-logo">VoltPulse AI</div>
        <div class="vp-tag" style="margin-top:4px">{subtitle}</div>
      </div>
      <div class="vp-header-right">
        <div class="vp-tag" style="margin-bottom:6px">Powered by VoltRelay Energy data</div>
        <div class="date-chip">6 cities · 3.88M events · Jan 2024 – Jun 2025</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="vp-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="vp-section-sub">{subtitle}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", delta: str = "",
        delta_dir: str = "flat", accent: str = INDIGO) -> None:
    delta_html = ""
    if delta:
        cls = {"up": "up", "down": "down"}.get(delta_dir, "flat")
        arrow = {"up": "▲", "down": "▼"}.get(delta_dir, "•")
        delta_html = f'<div><span class="delta {cls}">{arrow} {delta}</span></div>'
    st.markdown(f"""
    <div class="vp-kpi" style="--accent:{accent}">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {delta_html}
      <div class="sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def card(title: str, sub: str = "") -> None:
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="vp-card"><h3>{title}</h3>{sub_html}', unsafe_allow_html=True)


def end_card() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def callout(text: str, kind: str = "info") -> None:
    st.markdown(f'<div class="vp-callout {kind}">{text}</div>', unsafe_allow_html=True)


def expander(title: str, body: str) -> None:
    st.markdown(f"<details class='vp-exp'><summary>{title}</summary><div>{body}</div></details>",
                unsafe_allow_html=True)


def fmt_num(v, decimals=0) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if abs(v) >= 1e7:
        return f"{v/1e7:,.1f}Cr"
    if abs(v) >= 1e5:
        return f"{v/1e5:,.1f}L"
    return f"{v:,.{decimals}f}"


def fmt_pct(v, decimals=1) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{v*100:.{decimals}f}%"


def fmt_inr(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if abs(v) >= 1e7:
        return f"₹{v/1e7:,.2f} Cr"
    if abs(v) >= 1e5:
        return f"₹{v/1e5:,.2f} L"
    return f"₹{v:,.0f}"


def chart(fig: go.Figure, height: int = 380, **kw) -> None:
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": height}, **kw)
    st.plotly_chart(fig, use_container_width=True)


def line_chart(df, x, y, color=INDIGO, title="", height=360, markers=False):
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="lines+markers" if markers else "lines",
        line=dict(color=color, width=2.5),
        fill="tozeroy", fillcolor="rgba(79,70,229,0.06)",
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    fig.update_yaxes(tickformat=",", gridcolor="#F1EFF6")
    fig.update_xaxes(gridcolor="#F1EFF6")
    chart(fig, height=height)


def bar_chart(df, x, y, color=VIOLET, title="", height=360, horizontal=False,
              text=None):
    fig = go.Figure(go.Bar(
        x=df[y] if horizontal else df[x],
        y=df[x] if horizontal else df[y],
        orientation="h" if horizontal else "v",
        marker_color=color,
        text=text if text is not None else (df[y] if horizontal else df[y]),
        textposition="outside",
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    if horizontal:
        fig.update_xaxes(tickformat=",", gridcolor="#F1EFF6")
    else:
        fig.update_yaxes(tickformat=",", gridcolor="#F1EFF6")
    fig.update_xaxes(gridcolor="#F1EFF6")
    chart(fig, height=height)


def download_button(df: pd.DataFrame, filename: str, label: str = "Download CSV"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, file_name=filename, mime="text/csv")
