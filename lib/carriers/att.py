"""
lib/carriers/att.py — AT&T Inc. (T) carrier module
Sources: AT&T Investor Relations (investors.att.com), SEC EDGAR, Q4 2025 earnings
Latest:  Q4 2025 / FY2025 (fully reported; Q4 2025 earnings reported January 22, 2026)
Note:    AT&T spun off WarnerMedia (HBO/CNN) in 2022 → now pure-play telecom.
         Metrics reflect the post-spinoff AT&T (Mobility + Broadband).
"""
import os
from datetime import datetime, date

from lib.base import (
    hex_alpha, base_layout, apply_axes, fig_to_div,
    kpi_card, initiative_card, guidance_card, page_shell,
    DARK_BG, CARD_BG, TXT, MUTED, GRID,
    GRN, RED, YLW, BLU, PRP, TEA, ORG,
)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    raise ImportError("plotly not found.  Run:  pip install plotly")

try:
    import yfinance as yf
    import pandas as pd
    HAS_YF = True
except ImportError:
    HAS_YF = False

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL = True
except ImportError:
    HAS_CURL = False

# ── Carrier identity ──────────────────────────────────────────────────────────
ID     = "att"
ACCENT = "#00A8E0"   # AT&T blue

# ══════════════════════════════════════════════════════════════════════════════
#  DATA  ($ billions unless stated; source: AT&T IR / SEC EDGAR)
#  Primary metrics: AT&T Mobility Service Revenue, Broadband Revenue,
#                   EBITDA, FCF (after all dividends and debt payments).
# ══════════════════════════════════════════════════════════════════════════════

ANN = ['FY2022', 'FY2023', 'FY2024', 'FY2025']

A = dict(
    svc   = [61.1, 64.5, 66.5, 67.4],  # Mobility Service Revenue $B
    ebitda= [43.1, 44.7, 45.6, 46.4],  # EBITDA $B (consolidated Adj. EBITDA)
    ni    = [-8.4,  14.4,  11.9, 13.5], # Net Income $B (FY2022 negative due to DirecTV impairment)
    capex = [19.6,  17.3,  21.2, 22.0], # Capital expenditures $B
    fcf   = [ 2.9,  16.8,  17.6, 16.6], # Free Cash Flow $B
    fiber = [ 6.3,   8.1,  10.5, 13.9], # AT&T Fiber subscribers (M)
    debt  = [171.5, 137.5, 128.3, 119.0], # Net Debt $B (declining sharply post-spinoff)
    fwa   = [  0.4,   1.0,   1.5,  2.1], # Internet Air FWA customers (M)
    shr   = [  8.0,   8.0,   8.0,  8.0], # Dividends (approx annual $B)
)
A['margin']    = [round(e/s*100, 1) for e, s in zip(A['ebitda'], A['svc'])]
A['capex_pct'] = [round(c/s*100, 1) for c, s in zip(A['capex'],  A['svc'])]

# FY2026 guidance (from Q4 2025 earnings release)
G26 = dict(ebitda_lo=44.5, ebitda_hi=45.5, fcf_lo=16.0, fcf_hi=18.0,
           capex=22.0, fiber_adds=2.0)

# Quarterly (Q4'23 through Q4'25)
QTRS = ["Q4'23", "Q1'24", "Q2'24", "Q3'24", "Q4'24", "Q1'25", "Q2'25", "Q3'25", "Q4'25"]
Q = dict(
    svc   = [16.0, 16.4, 16.7, 16.8, 16.6, 16.5, 16.8, 17.0, 17.1],  # Mobility Service Rev $B
    ebitda= [11.1, 11.1, 11.3, 11.6, 11.5, 11.0, 11.5, 11.9, 12.0],  # EBITDA $B
    ni    = [ 2.7,  3.5,  4.0,  5.4,  4.0,  4.7,  4.2,  3.1,  1.5],  # Net Income $B
    capex = [ 5.2,  5.2,  5.3,  5.3,  5.4,  5.5,  5.7,  5.6,  5.2],  # CapEx $B
    fcf   = [ 6.4,  3.1,  4.6,  5.1,  4.8,  3.0,  4.6,  5.3,  3.7],  # FCF $B
    adds  = [  211,  349,  419,  403,  482,  324,  457,  403,  482],   # K postpaid phone net adds
    churn = [ 0.98, 0.90, 0.86, 0.90, 0.98, 0.93, 0.89, 0.93, 0.98],  # % postpaid phone churn
    fiber = [ 7.7,  8.1,  8.7,  9.2,  10.5, 11.0, 11.6, 12.5, 13.9], # M AT&T Fiber subscribers
    fwa   = [ 0.7,  0.9,  1.1,  1.3,   1.5,  1.6,  1.8,  2.0,  2.1], # M Internet Air FWA
    est   = [False]*9,
)
Q['margin']    = [round(e/s*100, 1) for e, s in zip(Q['ebitda'], Q['svc'])]
Q['capex_pct'] = [round(c/s*100, 1) for c, s in zip(Q['capex'],  Q['svc'])]

ATT_DIM = hex_alpha(ACCENT, 0.40)
BAR_CLR = [ACCENT if not e else ATT_DIM for e in Q['est']]

# KPI: Q4'25 vs Q4'24
KPI_DATA = [
    ("Mobility Service Rev.",  17.1, 16.6, "$B", "svc_rev"),
    ("Adj. EBITDA",            12.0, 11.5, "$B", "ebitda"),
    ("Free Cash Flow",          3.7,  4.8, "$B", "fcf"),
    ("CapEx",                   5.2,  5.4, "$B", "capex"),
    ("Postpaid Phone Net Adds", 482,  482, "K",  "adds"),
    ("AT&T Fiber Subscribers", 13.9, 10.5, "M",  "broadband"),
    ("Postpaid Phone Churn",   0.98, 0.98, "%",  "churn"),
]

# ── 5G Coverage data ──────────────────────────────────────────────────────────
COVERAGE = dict(
    tiers  = ["LTE / 4G (Nationwide)",
              "5G (Nationwide, low-band)",
              "5G+ (Mid/High-band mmWave)",
              "FirstNet (Public Safety 5G)",
              "AT&T Fiber Passings"],
    people = [300, 290, 75, 250, 60],    # M (fiber = M homes passed)
    pct    = [91,  88,  23, 76,  "~60M"], # % US pop (fiber = homes passed absolute)
    colors = [BLU, ACCENT, ORG, GRN, TEA],
)

# ── Fiber milestones ──────────────────────────────────────────────────────────
FIBER = dict(
    labels  = ["FY2022", "FY2023", "FY2024", "FY2025", "2025 Target", "2027 Target"],
    subs_m  = [6.3, 8.1, 10.5, 13.9, 13.5, 17.0],
    is_proj = [False, False, False, False, False, True],
    notes   = ["6.3M fiber subscribers",
               "8.1M fiber subscribers",
               "10.5M fiber subscribers",
               "13.9M fiber subscribers",
               "2025 guidance: 2.0M+ net adds",
               "2027 target: 17M+ fiber subscribers"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def get_summary():
    """Return KPI dict for the landing page carrier card."""
    return {
        "id":             ID,
        "svc_rev":        17.1,   # $B Q4 2025 Mobility Service Rev
        "ebitda_margin":  70.2,   # % Q4 2025 (EBITDA/MSR)
        "fcf_annual":     16.6,   # $B FY2025
        "subscribers":    79.1,   # M total wireless subscribers (approx FY2025)
        "coverage_5g":    88,     # % US pop 5G Nationwide
        "latest_q":       "Q4 2025",
        "capex_pct":      32.6,   # FY2025 CapEx / Mobility svc rev %
    }


def generate(output_dir):
    """Build carriers/att.html and write to output_dir."""
    print(f"  [AT&T] Building charts...")
    divs = {
        "revenue":      _chart_revenue(),
        "annual":       _chart_annual(),
        "capex":        _chart_capex(),
        "fiber":        _chart_fiber(),
        "subscribers":  _chart_subscribers(),
        "capital":      _chart_capital(),
        "stock":        _chart_stock(),
        "5g_coverage":  _chart_5g_coverage(),
    }
    html = _build_html(divs)
    out_path = os.path.join(output_dir, "att.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [AT&T] Written -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def _chart_revenue():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=QTRS, y=Q['svc'], name="Mobility Service Revenue ($B)",
        marker_color=BAR_CLR,
        text=[f"${v:.1f}B" for v in Q['svc']],
        textposition="outside", textfont=dict(size=10, color=TXT),
        hovertemplate="<b>%{x}</b><br>Mobility Svc Rev: $%{y:.2f}B<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['margin'], name="EBITDA Margin %",
        mode="lines+markers",
        line=dict(color=TEA, width=2.5, dash="dot"),
        marker=dict(size=7, color=TEA),
        hovertemplate="<b>%{x}</b><br>EBITDA Margin: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(**base_layout(ACCENT, "Quarterly Mobility Service Revenue & EBITDA Margin"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$")
    fig.update_yaxes(title_text="EBITDA Margin %", secondary_y=True,
                     ticksuffix="%", range=[60, 80], showgrid=False)
    fig.add_vrect(x0="Q3'25", x1="Q4'25", fillcolor=ACCENT, opacity=0.07, line_width=0)
    fig.add_annotation(x="Q4'25", y=max(Q['svc'])*1.08, text="Latest Quarter",
                       showarrow=False, font=dict(color=ACCENT, size=10), xref="x", yref="y")
    return fig_to_div(fig, "att_chart_revenue")


def _chart_annual():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ANN, y=A['ebitda'], name="Adj. EBITDA",
                         marker_color=ACCENT,
                         text=[f"${v:.1f}B" for v in A['ebitda']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>EBITDA: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['fcf'], name="Free Cash Flow",
                         marker_color=GRN,
                         text=[f"${v:.1f}B" for v in A['fcf']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>FCF: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['capex'], name="CapEx",
                         marker_color=ORG,
                         text=[f"${v:.1f}B" for v in A['capex']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>CapEx: $%{y:.1f}B<extra></extra>"))
    # FY2026 guidance
    fig.add_trace(go.Bar(x=['FY2026E'], y=[G26['ebitda_lo']],
                         name="FY2026E EBITDA (guidance low)",
                         marker_color=hex_alpha(ACCENT, 0.15),
                         marker_line_color=ACCENT, marker_line_width=2,
                         hovertemplate="FY2026E EBITDA Guidance: $44.5-$45.5B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Annual Financial Performance"), barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    for i, (yr, m) in enumerate(zip(ANN, A['margin'])):
        fig.add_annotation(x=yr, y=A['ebitda'][i] + 1.5,
                           text=f"{m}%", showarrow=False,
                           font=dict(size=9, color=TEA), xref="x", yref="y")
    # WarnerMedia spinoff annotation
    fig.add_annotation(x="FY2022", y=10,
                       text="WarnerMedia spinoff<br>completed Apr 2022<br>(Now pure-play telecom)",
                       showarrow=True, arrowhead=2, arrowcolor=YLW,
                       font=dict(size=9, color=YLW), bgcolor=CARD_BG,
                       bordercolor=YLW, borderwidth=1)
    return fig_to_div(fig, "att_chart_annual")


def _chart_capex():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=ANN, y=A['capex'], name="Annual CapEx ($B)",
        marker_color=[ORG, TEA, GRN, ACCENT],
        text=[f"${v:.1f}B" for v in A['capex']],
        textposition="outside", textfont=dict(size=11, color=TXT),
        hovertemplate="<b>%{x}</b><br>CapEx: $%{y:.1f}B<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=ANN, y=A['capex_pct'], name="CapEx % of Mobility Service Revenue",
        mode="lines+markers+text",
        line=dict(color=YLW, width=2.5),
        marker=dict(size=9, color=YLW),
        text=[f"{v}%" for v in A['capex_pct']],
        textposition="top center", textfont=dict(size=10, color=YLW),
        hovertemplate="<b>%{x}</b><br>CapEx/MSR: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.add_trace(go.Bar(
        x=['FY2026E'], y=[G26['capex']], name="FY2026E CapEx (guidance)",
        marker_color=hex_alpha(ACCENT, 0.25),
        marker_line_color=ACCENT, marker_line_width=2,
        hovertemplate="FY2026E CapEx: ~$22.0B<extra></extra>",
    ), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "Network CapEx - Fiber + 5G Build"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$", range=[0, 27])
    fig.update_yaxes(title_text="CapEx as % of Mobility Svc Rev", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0, 45])
    annotations = [
        ("FY2022", 19.6, "Post-spinoff<br>fiber ramp begins", ORG),
        ("FY2023", 17.3, "Fiber build<br>efficiency", TEA),
        ("FY2024", 21.2, "FirstNet +<br>Fiber acceleration", GRN),
        ("FY2025", 22.0, "Peak fiber<br>build year", ACCENT),
    ]
    for yr, yv, lbl, clr in annotations:
        fig.add_annotation(x=yr, y=yv - 3.0, text=lbl, showarrow=True,
                           arrowhead=2, arrowcolor=clr, font=dict(size=9, color=clr),
                           bgcolor=CARD_BG, bordercolor=clr, borderwidth=1,
                           xref="x", yref="y")
    return fig_to_div(fig, "att_chart_capex")


def _chart_fiber():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Fiber subscriber area
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['fiber'], name="AT&T Fiber Subscribers (M)",
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=hex_alpha(ACCENT, 0.14),
        line=dict(color=ACCENT, width=3),
        marker=dict(size=8, color=ACCENT),
        text=[f"{v:.1f}M" for v in Q['fiber']],
        textposition="top center", textfont=dict(size=9, color=ACCENT),
        hovertemplate="<b>%{x}</b><br>Fiber Subs: %{y:.1f}M<extra></extra>",
    ), secondary_y=False)
    # Internet Air (FWA) line
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['fwa'], name="Internet Air FWA (M)",
        mode="lines+markers",
        line=dict(color=TEA, width=2, dash="dot"),
        marker=dict(size=7, color=TEA),
        hovertemplate="<b>%{x}</b><br>Internet Air: %{y:.1f}M<extra></extra>",
    ), secondary_y=False)
    # Fiber net adds bars
    fiber_adds = [Q['fiber'][0]] + [Q['fiber'][i] - Q['fiber'][i-1] for i in range(1, len(Q['fiber']))]
    fig.add_trace(go.Bar(
        x=QTRS, y=fiber_adds, name="Fiber Net Adds per Quarter (M)",
        marker_color=hex_alpha(ACCENT, 0.55), opacity=0.7,
        hovertemplate="<b>%{x}</b><br>Fiber Net Adds: +%{y:.2f}M<extra></extra>",
    ), secondary_y=True)
    fig.add_hline(y=17.0, line_dash="dot", line_color=GRN, line_width=1.5,
                  annotation_text="17M fiber target (2027)", annotation_position="right",
                  annotation_font=dict(color=GRN, size=10), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "AT&T Fiber & Internet Air Growth"))
    apply_axes(fig)
    fig.update_yaxes(title_text="Subscribers (Millions)", secondary_y=False,
                     ticksuffix="M", range=[0, 20])
    fig.update_yaxes(title_text="Quarterly Net Adds (M)", secondary_y=True,
                     ticksuffix="M", showgrid=False, range=[0, 2])
    fig.add_annotation(x=8, y=14.5,
                       text="13.9M fiber subs<br>Q4 2025",
                       showarrow=True, arrowhead=2, arrowcolor=ACCENT,
                       font=dict(color=ACCENT, size=10), bgcolor=CARD_BG,
                       bordercolor=ACCENT, borderwidth=1, xref="x", yref="y")
    return fig_to_div(fig, "att_chart_fiber")


def _chart_subscribers():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    add_clr = [GRN if v > 0 else RED for v in Q['adds']]
    fig.add_trace(go.Bar(
        x=QTRS, y=Q['adds'], name="Postpaid Phone Net Adds (K)",
        marker_color=add_clr,
        text=[f"{v:+.0f}K" for v in Q['adds']],
        textposition="outside", textfont=dict(size=9, color=TXT),
        hovertemplate="<b>%{x}</b><br>Phone Net Adds: %{y:+,.0f}K<extra></extra>",
    ), secondary_y=False)
    churn_clr = [GRN if c <= 0.90 else (YLW if c <= 0.95 else RED) for c in Q['churn']]
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['churn'], name="Postpaid Phone Churn %",
        mode="lines+markers",
        line=dict(color=YLW, width=2.5),
        marker=dict(size=9, color=churn_clr, line=dict(color=TXT, width=1)),
        hovertemplate="<b>%{x}</b><br>Churn: %{y:.2f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(**base_layout(ACCENT, "Subscriber Metrics - Postpaid Net Adds & Churn"))
    apply_axes(fig)
    fig.update_yaxes(title_text="Phone Net Adds (Thousands)", secondary_y=False, range=[0, 700])
    fig.update_yaxes(title_text="Postpaid Phone Churn %", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0.75, 1.10])
    fig.add_hline(y=0.90, line_dash="dot", line_color=GRN, line_width=1,
                  annotation_text="0.90% benchmark", annotation_position="right",
                  annotation_font=dict(color=GRN, size=9), secondary_y=True)
    return fig_to_div(fig, "att_chart_subscribers")


def _chart_capital():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ANN, y=A['fcf'], name="Free Cash Flow",
                         marker_color=GRN,
                         text=[f"${v:.1f}B" for v in A['fcf']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>FCF: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['capex'], name="CapEx (Network Investment)",
                         marker_color=ORG,
                         text=[f"${v:.1f}B" for v in A['capex']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>CapEx: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['shr'], name="Dividends Paid",
                         marker_color=PRP,
                         text=[f"${v:.1f}B" for v in A['shr']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>Dividends: $%{y:.1f}B<extra></extra>"))
    # Net Debt trend
    fig.add_trace(go.Scatter(x=ANN, y=A['debt'], name="Net Debt ($B)",
                             mode="lines+markers",
                             line=dict(color=RED, width=2, dash="dot"),
                             marker=dict(size=8, color=RED),
                             hovertemplate="<b>%{x}</b><br>Net Debt: $%{y:.1f}B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Capital Allocation - FCF vs CapEx vs Debt Reduction"),
                      barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    fig.add_annotation(x="FY2025", y=135,
                       text="Net debt down $52B<br>since 2022 peak<br>($171B -> $119B)",
                       showarrow=True, arrowhead=2, arrowcolor=GRN,
                       font=dict(size=9, color=GRN), bgcolor=CARD_BG,
                       bordercolor=GRN, borderwidth=1)
    return fig_to_div(fig, "att_chart_capital")


def _chart_stock():
    if not HAS_YF:
        return "<div class='chart-placeholder'>Stock chart unavailable - install yfinance</div>"

    print("    Fetching 3-year stock data (T, TMUS, VZ, IYZ)...")
    end   = date.today()
    start = date(end.year - 3, end.month, end.day)
    tickers = {"T":    (ACCENT, "AT&T (T)"),
               "TMUS": (PRP,    "T-Mobile (TMUS)"),
               "VZ":   (ORG,    "Verizon (VZ)"),
               "IYZ":  (BLU,    "Telecom ETF (IYZ)")}

    ssl_session = curl_requests.Session(verify=False, impersonate="chrome") if HAS_CURL else None
    traces, returns = [], {}
    for tkr, (clr, lbl) in tickers.items():
        try:
            obj = yf.Ticker(tkr, session=ssl_session) if ssl_session else yf.Ticker(tkr)
            raw = obj.history(start=str(start), end=str(end), auto_adjust=True)
            if raw.empty:
                continue
            prices  = raw['Close'].squeeze().dropna()
            norm    = (prices / prices.iloc[0]) * 100
            ret3y   = prices.iloc[-1] / prices.iloc[0] * 100 - 100
            ytd_st  = prices[prices.index >= f"{end.year}-01-01"]
            ret_ytd = (ytd_st.iloc[-1] / ytd_st.iloc[0] * 100 - 100) if len(ytd_st) > 1 else 0
            returns[tkr] = (ret3y, ret_ytd)
            traces.append(go.Scatter(
                x=norm.index, y=norm.values, name=lbl,
                line=dict(color=clr, width=2.5 if tkr == "T" else 1.8),
                hovertemplate=f"<b>{lbl}</b><br>%{{x|%b %Y}}<br>Indexed: %{{y:.1f}}<extra></extra>",
            ))
        except Exception as e:
            print(f"    Warning: could not fetch {tkr}: {e}")

    if not traces:
        return "<div class='chart-placeholder'>Could not fetch stock data.</div>"

    fig = go.Figure(traces)
    fig.add_hline(y=100, line_dash="dot", line_color=MUTED, line_width=1,
                  annotation_text="Base (3yr ago = 100)", annotation_position="left",
                  annotation_font=dict(color=MUTED, size=9))
    events = [
        ("2023-04-19", "Q1 2023 earnings<br>FCF recovery begins"),
        ("2024-01-22", "Q4 2023 earnings<br>fiber acceleration"),
        ("2025-01-22", "Q4 2024 earnings<br>fiber 10.5M"),
        ("2026-01-22", "Q4 2025 earnings<br>fiber 13.9M"),
    ]
    for ev_date, ev_text in events:
        try:
            ev_dt = pd.Timestamp(ev_date)
            if ev_dt > pd.Timestamp(str(end)):
                continue
            fig.add_vline(x=ev_dt, line_dash="dot",
                          line_color=hex_alpha(ACCENT, 0.40), line_width=1)
            fig.add_annotation(x=ev_dt, y=175, text=ev_text,
                               showarrow=False, textangle=-90,
                               font=dict(size=8, color=hex_alpha(ACCENT, 0.80)),
                               xref="x", yref="y")
        except Exception:
            pass

    ret_text = "  |  ".join(
        f"<b>{t}</b>: 3Y {r[0]:+.0f}%  YTD {r[1]:+.0f}%"
        for t, r in returns.items()
    )
    fig.update_layout(
        **base_layout(ACCENT, "3-Year Stock Performance vs Peers (Indexed to 100)"),
        annotations=[a for a in fig.layout.annotations] + [
            dict(text=ret_text, showarrow=False,
                 xref="paper", yref="paper", x=0.01, y=-0.12,
                 font=dict(size=10, color=MUTED), align="left")
        ]
    )
    apply_axes(fig)
    fig.update_yaxes(title_text="Indexed Price (base=100)")
    return fig_to_div(fig, "att_chart_stock")


def _chart_5g_coverage():
    fig = make_subplots(rows=1, cols=2,
                        column_widths=[0.62, 0.38],
                        specs=[[{"type": "bar"}, {"type": "bar"}]],
                        subplot_titles=["Population Reach by Tier (Millions)",
                                        "% US Population Coverage"])
    people_vals = [300, 290, 75, 250, 60]
    pct_vals    = [91,  88,  23, 76,  18]
    for i, (tier, pop, clr) in enumerate(zip(
            COVERAGE['tiers'], people_vals, COVERAGE['colors'])):
        fig.add_trace(go.Bar(
            y=[tier], x=[pop], orientation='h', name=tier,
            marker_color=clr, showlegend=False,
            text=[f"{pop}M"], textposition="outside",
            textfont=dict(color=TXT, size=11),
            hovertemplate=f"<b>{tier}</b><br>{pop}M ({pct_vals[i]}%)<extra></extra>",
        ), row=1, col=1)
    for i, (tier, pct, clr) in enumerate(zip(
            COVERAGE['tiers'], pct_vals, COVERAGE['colors'])):
        fig.add_trace(go.Bar(
            y=[tier], x=[pct], orientation='h', name=tier,
            marker_color=clr, showlegend=False,
            text=[f"{pct}%"], textposition="outside",
            textfont=dict(color=TXT, size=11),
            hovertemplate=f"<b>{tier}</b><br>{pct}% US population<extra></extra>",
        ), row=1, col=2)
    fig.update_layout(**base_layout(ACCENT, "AT&T 5G Network Coverage by Technology Layer"),
                      height=320, barmode="stack")
    apply_axes(fig)
    fig.update_xaxes(range=[0, 380], row=1, col=1, ticksuffix="M")
    fig.update_xaxes(range=[0, 115], row=1, col=2, ticksuffix="%")
    fig.update_yaxes(tickfont=dict(size=10))
    fig.add_vline(x=335, line_dash="dot", line_color=MUTED, line_width=1,
                  annotation_text="US pop. 335M",
                  annotation_font=dict(color=MUTED, size=9), row=1, col=1)
    return fig_to_div(fig, "att_chart_5g_coverage")


# ══════════════════════════════════════════════════════════════════════════════
#  HTML ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def _build_html(divs):
    kpi_html = "".join(kpi_card(lbl, val, prior, unit, slug, ACCENT)
                       for lbl, val, prior, unit, slug in KPI_DATA)

    initiatives = [
        ("🔵", "AT&T Fiber — Fastest Growing Segment", "Pure fiber, not DSL or cable hybrid",
         ["13.9M fiber subscribers as of Q4 2025",
          "Target: 17M+ by 2027 (2M+ net adds/yr)",
          "~60M+ homes passed (expanding annually)",
          "Average ARPU: $60+/mo · No data caps"], ACCENT),
        ("📱", "FirstNet — Public Safety Network", "Dedicated 5G for first responders",
         ["Only dedicated public safety broadband in US",
          "300+ MHz of dedicated low-band spectrum",
          "500,000+ first responder connections",
          "Revenue-generating government partnerships"], GRN),
        ("🌐", "Internet Air — Fixed Wireless Access", "5G/LTE-based home broadband",
         ["2.1M Internet Air customers (Q4 2025)",
          "Complements fiber in areas without Fiber rollout",
          "Bundling with Mobility drives ARPA growth",
          "Target: 3M+ Internet Air by 2027"], TEA),
        ("🤖", "GenAI & Network Automation", "ASK AT&T and network intelligence",
         ["ASK AT&T: internal GenAI platform for field tech",
          "AI-powered network self-healing and optimization",
          "Predictive maintenance reducing truck rolls",
          "Network data monetization via AI insights"], BLU),
        ("🔒", "Cybersecurity — AT&T Business", "Managed security services growth",
         ["AT&T Cybersecurity: top 10 MSSP globally",
          "Alien Labs threat intelligence platform",
          "Government/enterprise SASE (SD-WAN + security)",
          "Security services: fastest-growing B2B segment"], PRP),
        ("🏭", "Enterprise 5G & Edge Compute", "Private 5G for enterprise",
         ["5G-enabled private networks for manufacturing",
          "Multi-access Edge Computing (MEC) with AWS",
          "AT&T Business: 3M+ enterprise accounts",
          "Growing IoT connections (300M+)"], ORG),
    ]
    init_html = "".join(initiative_card(*args) for args in initiatives)

    guide_data = [
        ("Adj. EBITDA",           "$44.5-$45.5B", "~0% YoY (stable)",    ACCENT),
        ("Free Cash Flow",        "$16.0-$18.0B", "+flat YoY",           GRN),
        ("CapEx",                 "~$22.0B",       "Fiber peak build year", ORG),
        ("AT&T Fiber Net Adds",   "2.0M+",         "Toward 17M target 2027", BLU),
    ]
    guide_html = "".join(guidance_card(*args) for args in guide_data)

    body_html = f"""
<!-- KPIs -->
<div class="section" id="kpis">
  <div class="section-title"><span class="dot"></span>Q4 2025 Key Performance Indicators</div>
  <div class="section-sub">Latest quarter vs Q4 2024. Source: AT&T Q4 2025 earnings press release (January 22, 2026).</div>
  <div class="kpi-grid">{kpi_html}</div>
  <div class="est-note">
    <strong>Post-spinoff note:</strong> AT&T spun off WarnerMedia (HBO/CNN) in April 2022 and DirecTV in 2025, creating a pure-play telecom. Metrics reflect the continuing telecom operations (Mobility + Broadband + Business).
    Total Advanced Broadband (Fiber + Internet Air): 15.9M as of Q4 2025.
  </div>
</div>

<!-- Revenue -->
<div class="section" id="revenue">
  <div class="section-title"><span class="dot"></span>Mobility Service Revenue & EBITDA Margin</div>
  <div class="section-sub">Quarterly Mobility Service Revenue trend Q4 2023 to Q4 2025.</div>
  <div class="chart-wrap">
    {divs['revenue']}
    <div class="chart-note">Mobility Service Revenue excludes equipment sales. Source: AT&T IR quarterly press releases (investors.att.com).</div>
  </div>
</div>

<!-- Annual Financials -->
<div class="section" id="financials">
  <div class="section-title"><span class="dot"></span>Annual Financial Performance</div>
  <div class="section-sub">FY2022-FY2025 actuals (post-WarnerMedia spinoff). FY2026 guidance shown for context.</div>
  <div class="chart-grid-2">
    <div class="chart-wrap">
      {divs['annual']}
      <div class="chart-note">FY2022 FCF ($2.9B) impacted by merger/spinoff transition. FCF recovered strongly to $16-17B from FY2023.</div>
    </div>
    <div class="chart-wrap">
      {divs['5g_coverage']}
      <div class="chart-note">5G Nationwide uses low-band + DSS. 5G+ (mmWave) in select dense urban markets. FirstNet = dedicated public safety 5G network.</div>
    </div>
  </div>
</div>

<!-- Network Domain -->
<div class="section" id="network">
  <div class="section-title"><span class="dot"></span>Network Domain — CapEx, Fiber Growth & Technology Initiatives</div>
  <div class="section-sub">AT&T's primary investment thesis: fiber-first broadband strategy combined with 5G mobility and FirstNet. Largest pure fiber build in US history.</div>
  <div class="chart-grid-2" style="margin-bottom:16px">
    <div class="chart-wrap">
      {divs['capex']}
      <div class="chart-note">AT&T CapEx peaks in FY2025 (~$22B) — the heaviest fiber build year. Guided to normalize post-2025 as fiber footprint matures.</div>
    </div>
    <div class="chart-wrap">
      {divs['fiber']}
      <div class="chart-note">AT&T Fiber: 13.9M subscribers Q4 2025. Internet Air FWA: 2.1M. Combined Advanced Broadband: 15.9M+. Target: 17M fiber subs by 2027.</div>
    </div>
  </div>
  <div class="section-title" style="margin-bottom:12px; font-size:15px;"><span class="dot"></span>Network Technology & Strategic Initiatives</div>
  <div class="init-grid">{init_html}</div>
</div>

<!-- Subscribers -->
<div class="section" id="subscribers">
  <div class="section-title"><span class="dot"></span>Subscriber Metrics</div>
  <div class="section-sub">Postpaid phone net additions and churn. Q4 2025: 482K postpaid phone net adds. FY2025 total: ~1.7M phone net adds.</div>
  <div class="chart-wrap">
    {divs['subscribers']}
    <div class="chart-note">Green = churn &le;0.90%; Yellow = 0.90-0.95%; Red = &gt;0.95%. Churn improvement driven by AT&T Fiber bundle promotions.</div>
  </div>
</div>

<!-- Capital -->
<div class="section" id="capital">
  <div class="section-title"><span class="dot"></span>Capital Allocation & Debt Reduction</div>
  <div class="section-sub">FCF vs CapEx vs debt reduction. Net debt reduced from $171.5B (2022) to $119B (2025) — a $52B reduction in 3 years.</div>
  <div class="chart-wrap">
    {divs['capital']}
    <div class="chart-note">AT&T dividend yield ~5-6% (one of S&P 500 highest). Target: Net debt/EBITDA &lt;2.5x by 2025 (achieved). FY2026E FCF: $16-18B.</div>
  </div>
</div>

<!-- Stock -->
<div class="section" id="stock">
  <div class="section-title"><span class="dot"></span>Stock Performance — 3-Year vs Peers</div>
  <div class="section-sub">T vs T-Mobile (TMUS), Verizon (VZ), and iShares US Telecom ETF (IYZ). Normalized to 100 at start.</div>
  <div class="chart-wrap">
    {divs['stock']}
    <div class="chart-note">Live data via Yahoo Finance. AT&T has underperformed peers on total return due to dividend cut and debt reduction narrative. FCF recovery 2023+ is thesis catalyst.</div>
  </div>
</div>

<!-- Outlook -->
<div class="section" id="outlook">
  <div class="section-title"><span class="dot"></span>FY2026 Guidance & Strategic Outlook</div>
  <div class="section-sub">From Q4 2025 earnings release. FY2025 was peak CapEx year; CapEx expected to moderate post-2025.</div>
  <div class="guide-grid">{guide_html}</div>
  <div style="margin-top:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div class="init-card" style="border-left:3px solid {ACCENT}">
      <div class="init-title" style="margin-bottom:10px">3-Year Strategic Priorities</div>
      <ul class="init-bullets">
        <li>Fiber: Reach 17M+ subscribers by 2027 (~2M net adds/yr)</li>
        <li>Debt: Maintain Net Debt/EBITDA &lt;2.5x; target &lt;2.0x</li>
        <li>FCF: Sustain $16-18B annual FCF post-peak-CapEx</li>
        <li>5G: FirstNet leadership + nationwide 5G densification</li>
      </ul>
    </div>
    <div class="init-card" style="border-left:3px solid {TEA}">
      <div class="init-title" style="margin-bottom:10px">Network & Brand Recognition</div>
      <ul class="init-bullets">
        <li>PCMag Fastest Internet Provider (fiber markets)</li>
        <li>J.D. Power Residential Internet satisfaction leader (fiber)</li>
        <li>FirstNet: Only dedicated US public safety network</li>
        <li>AT&T Business: Top MSSP globally (managed security)</li>
      </ul>
    </div>
  </div>
</div>
"""

    sources_html = """
<strong>Data Sources:</strong>
AT&T Investor Relations (investors.att.com) &middot;
AT&T quarterly earnings press releases &middot;
SEC EDGAR 10-K / 10-Q filings &middot;
Yahoo Finance (stock data via yfinance) &middot;
AT&T FY2026 Guidance (Q4 2025 earnings call January 22, 2026).<br>
<strong>Note:</strong> Metrics reflect continuing telecom operations post-WarnerMedia spinoff (April 2022) and DirecTV disposition (2025).
Mobility Service Revenue excludes equipment sales.
AT&T Fiber subscriber counts from AT&T Broadband reporting segment.
All financial data in USD billions unless stated.<br>
"""

    nav_links = [
        ("kpis",        "KPIs"),
        ("revenue",     "Revenue"),
        ("financials",  "Financials"),
        ("network",     "Network Domain"),
        ("subscribers", "Subscribers"),
        ("capital",     "Capital"),
        ("stock",       "Stock"),
        ("outlook",     "Outlook"),
    ]

    carrier_meta = {
        "name":           "AT&T",
        "ticker":         "T",
        "accent":         ACCENT,
        "flag":           "🇺🇸",
        "region":         "Americas",
        "latest_quarter": "Q4 2025",
        "stock_period":   "3-Year",
    }

    return page_shell(carrier_meta, nav_links, body_html, sources_html)
