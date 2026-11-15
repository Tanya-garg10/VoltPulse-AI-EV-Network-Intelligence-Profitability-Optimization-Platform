"""VoltPulse AI design system — premium enterprise BI theme."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');

:root {
  --vp-bg: #F7F5F2;
  --vp-surface: #FFFFFF;
  --vp-border: #ECE8F1;
  --vp-border-soft: #F1EEF6;
  --vp-indigo: #4F46E5;
  --vp-violet: #7C3AED;
  --vp-teal: #0D9488;
  --vp-ink: #191733;
  --vp-ink-2: #3D3A55;
  --vp-muted: #8A8699;
  --vp-radius: 16px;
  --vp-shadow: 0 1px 2px rgba(25,23,51,.04), 0 4px 16px rgba(25,23,51,.05);
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: var(--vp-bg); color: var(--vp-ink); }

/* ============ SIDEBAR ============ */
section[data-testid="stSidebar"] {
  background: linear-gradient(168deg, #17153A 0%, #241F5E 48%, #312E81 100%);
  border-right: 1px solid rgba(255,255,255,.06);
  box-shadow: 4px 0 24px rgba(23,21,58,.18);
}
section[data-testid="stSidebar"] > div { padding-top: 18px; }
section[data-testid="stSidebar"] * { color: #D6D3F5 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { display: none; }
section[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,.07) !important;
  border: 1px solid rgba(255,255,255,.12) !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  padding: 10px 14px !important;
  transition: all .15s ease;
  text-align: left !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,.16) !important;
  transform: translateX(2px);
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[aria-pressed="true"] {
  background: linear-gradient(90deg, #4F46E5, #7C3AED) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(99,102,241,.4);
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12) !important; }
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] small { color: #9C97C4 !important; }

/* ============ HEADER ============ */
.vp-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 0 18px 0; margin-bottom: 20px;
  border-bottom: 1px solid var(--vp-border);
}
.vp-logo {
  font-family: 'Sora', sans-serif; font-size: 24px; font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(92deg, #312E81 10%, #4F46E5 55%, #7C3AED 95%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.vp-tag {
  font-size: 11px; letter-spacing: 0.09em; text-transform: uppercase;
  color: var(--vp-muted); font-weight: 600;
}
.vp-header-right { text-align: right; }
.vp-header-right .date-chip {
  display: inline-block; padding: 6px 14px; border-radius: 999px;
  background: var(--vp-surface); border: 1px solid var(--vp-border);
  font-size: 12px; font-weight: 600; color: var(--vp-ink-2);
  box-shadow: var(--vp-shadow);
}

/* ============ PAGE TITLES ============ */
.vp-section-title {
  font-family: 'Sora', sans-serif; font-size: 26px; font-weight: 800;
  letter-spacing: -0.02em; color: var(--vp-ink); margin: 4px 0 2px 0;
}
.vp-section-sub { color: var(--vp-muted); font-size: 13.5px; margin-bottom: 22px; }

/* ============ KPI CARDS ============ */
.vp-kpi {
  background: var(--vp-surface); border: 1px solid var(--vp-border);
  border-radius: var(--vp-radius); padding: 18px 20px 16px;
  box-shadow: var(--vp-shadow); height: 100%;
  position: relative; overflow: hidden;
  transition: transform .15s ease, box-shadow .15s ease;
}
.vp-kpi:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(25,23,51,.09); }
.vp-kpi::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent, var(--vp-indigo));
}
.vp-kpi .label {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--vp-muted); margin-bottom: 8px;
}
.vp-kpi .value {
  font-family: 'Sora', sans-serif; font-size: 27px; font-weight: 800;
  color: var(--vp-ink); line-height: 1.15; letter-spacing: -0.02em;
}
.vp-kpi .sub { font-size: 12px; color: var(--vp-muted); margin-top: 6px; }
.vp-kpi .delta {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11.5px; font-weight: 700; margin-top: 8px;
  padding: 2px 8px; border-radius: 999px;
}
.vp-kpi .delta.up { color: #047857; background: #ECFDF5; }
.vp-kpi .delta.down { color: #B91C1C; background: #FEF2F2; }
.vp-kpi .delta.flat { color: var(--vp-muted); background: var(--vp-border-soft); }

/* ============ CARDS ============ */
.vp-card {
  background: var(--vp-surface); border: 1px solid var(--vp-border);
  border-radius: var(--vp-radius); padding: 22px 24px;
  box-shadow: var(--vp-shadow); margin-bottom: 18px;
}
.vp-card h3 {
  font-family: 'Sora', sans-serif; font-size: 15.5px; font-weight: 700;
  letter-spacing: -0.01em; margin: 0 0 3px 0; color: var(--vp-ink);
}
.vp-card .card-sub { font-size: 12.5px; color: var(--vp-muted); margin-bottom: 14px; }
.vp-card:last-child { margin-bottom: 0; }

/* ============ CALLOUTS ============ */
.vp-callout {
  border-left: 3px solid var(--vp-indigo); background: #EEF0FE;
  border-radius: 0 12px 12px 0; padding: 12px 16px; font-size: 13px;
  color: #312E81; margin: 12px 0; line-height: 1.5;
}
.vp-callout.warn { border-color: #D97706; background: #FFFBEB; color: #78350F; }
.vp-callout.bad { border-color: #DC2626; background: #FEF2F2; color: #7F1D1D; }
.vp-callout.good { border-color: var(--vp-teal); background: #F0FDFA; color: #134E4A; }

/* ============ TABLES ============ */
[data-testid="stDataFrame"] {
  border: 1px solid var(--vp-border) !important;
  border-radius: 14px !important;
  overflow: hidden;
  box-shadow: var(--vp-shadow);
}
[data-testid="stDataFrame"] thead th {
  background: #F7F6FB !important;
  font-weight: 700 !important;
  font-size: 11.5px !important;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--vp-muted) !important;
  border-bottom: 1px solid var(--vp-border) !important;
}

/* ============ TABS ============ */
.stTabs [data-baseweb="tab-list"] {
  gap: 6px; background: var(--vp-border-soft);
  padding: 4px; border-radius: 12px; border: 1px solid var(--vp-border);
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-radius: 9px !important;
  padding: 8px 16px !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  color: var(--vp-ink-2) !important;
}
.stTabs [aria-selected="true"] {
  background: var(--vp-surface) !important;
  color: var(--vp-indigo) !important;
  box-shadow: 0 1px 4px rgba(25,23,51,.1) !important;
}

/* ============ WIDGETS ============ */
.stMultiSelect, .stDateInput, .stSelectbox {
  border-radius: 12px;
}
.stMultiSelect > div, .stDateInput > div, .stSelectbox > div {
  border-radius: 12px !important;
  border: 1px solid var(--vp-border) !important;
  box-shadow: none !important;
}
.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
}
.stDownloadButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--vp-border) !important;
  background: var(--vp-surface) !important;
  color: var(--vp-ink) !important;
  font-weight: 600 !important;
}
[data-testid="stMetric"] {
  background: var(--vp-surface); border: 1px solid var(--vp-border);
  border-radius: 14px; padding: 14px 18px; box-shadow: var(--vp-shadow);
}
[data-testid="stMetricLabel"] p { font-size: 11px !important; font-weight: 700;
  letter-spacing: .07em; text-transform: uppercase; color: var(--vp-muted) !important; }
[data-testid="stMetricValue"] { font-family: 'Sora', sans-serif !important;
  font-size: 24px !important; font-weight: 800 !important; color: var(--vp-ink) !important; }

details.vp-exp {
  background: var(--vp-surface); border: 1px solid var(--vp-border);
  border-radius: 12px; padding: 12px 16px; margin: 8px 0;
}
details.vp-exp summary { font-weight: 600; cursor: pointer; color: var(--vp-ink); font-size: 13px; }
details.vp-exp[open] summary { margin-bottom: 8px; }

.vp-badge {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em;
}
.vp-badge.critical { background: #FEE2E2; color: #B91C1C; }
.vp-badge.high { background: #FFEDD5; color: #C2410C; }
.vp-badge.medium { background: #FEF9C3; color: #A16207; }
.vp-badge.low { background: #E0F2FE; color: #0369A1; }
.vp-badge.good { background: #D1FAE5; color: #047857; }
.vp-badge.info { background: #EDE9FE; color: #6D28D9; }

/* ============ MISC ============ */
hr { border-color: var(--vp-border) !important; }
.streamlit-expanderHeader { font-weight: 600; }
a { color: var(--vp-indigo); }
</style>
"""

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", size=12, color="#3D3A55"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=8, t=24, b=8),
    hoverlabel=dict(font=dict(family="Inter", size=12, color="#191733"),
                    bgcolor="#FFFFFF", bordercolor="#ECE8F1"),
    legend=dict(font=dict(size=11.5, color="#8A8699")),
)

PLOTLY_TEMPLATE = "plotly_white"

INDIGO = "#4F46E5"
VIOLET = "#7C3AED"
TEAL = "#0D9488"
AMBER = "#F59E0B"
RED = "#EF4444"
GREEN = "#10B981"
PALETTE = [INDIGO, VIOLET, TEAL, AMBER, RED, GREEN, "#6366F1", "#14B8A6"]
