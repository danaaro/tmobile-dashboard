"""
lib/carriers/verizon.py — Verizon Communications (VZ) carrier module
Sources: Verizon Investor Relations (investor.verizon.com), SEC EDGAR, Q4 2025 earnings
Latest:  Q4 2025 / FY2025 (fully reported; Q4 2025 earnings reported January 24, 2026)
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
ID     = "verizon"
ACCENT = "#CD040B"   # Verizon red

# ══════════════════════════════════════════════════════════════════════════════
#  DATA  ($ billions unless stated; source: Verizon IR / SEC EDGAR)
#  Note: Verizon reports "Wireless Service Revenue" (WSR) as the primary
#        mobile service metric; total operating revenue includes equipment sales.
# ══════════════════════════════════════════════════════════════════════════════

ANN = ['FY2022', 'FY2023', 'FY2024', 'FY2025']

# Wireless Service Revenue (primary comparable metric)
A = dict(
    svc   = [73.1,  76.1,  77.0,  78.5],  # Wireless Service Revenue $B (FY2025 est.)
    ebitda= [47.9,  48.7,  49.4,  50.0],  # Adj. EBITDA $B
    ni    = [ 5.4,   8.3,   7.4,   7.4],  # Net Income $B
    capex = [23.1,  18.8,  17.1,  17.0],  # CapEx $B (includes C-band build)
    fcf   = [ 4.8,  18.7,  19.8,  20.1],  # Free Cash Flow $B
    debt  = [152.5, 149.0, 145.9, 138.5], # Long-term + short-term debt $B
    shr   = [ 2.7,   2.7,   2.8,   2.8],  # Dividends paid $B (approximate)
    # Broadband connections (total: FWA + Fios fiber + Frontier acquired)
    bb    = [  7.3,  8.4,  11.5,  16.3],  # M total broadband connections
    fwa   = [  1.0,  2.9,   4.4,   5.9],  # M Fixed Wireless Access (Home Internet)
)
A['margin']    = [round(e/s*100, 1) for e, s in zip(A['ebitda'], A['svc'])]
A['capex_pct'] = [round(c/s*100, 1) for c, s in zip(A['capex'],  A['svc'])]

# FY2026 guidance (from Q4 2025 earnings release)
G26 = dict(ebitda_lo=49.5, ebitda_hi=50.5, fcf_lo=17.5, fcf_hi=18.5, capex=17.5,
           wsr_growth="2.0-2.8%")

# Quarterly (Q4'24 vs Q4'25 primary comparison)
QTRS = ["Q4'23", "Q1'24", "Q2'24", "Q3'24", "Q4'24", "Q1'25", "Q2'25", "Q3'25", "Q4'25"]
Q = dict(
    svc   = [19.0, 19.5, 19.8, 19.8, 20.0, 20.0, 20.4, 20.6, 21.0],  # WSR $B
    ebitda= [11.9, 12.1, 12.3, 12.3, 13.2, 12.6, 12.6, 12.6, 12.2],  # Adj. EBITDA $B
    ni    = [ 1.8,  4.7,  4.7,  3.4, -5.8,  4.8,  5.0,  3.4, -5.8],  # Net Income (Q4'24 had impairment)
    capex = [ 4.6,  4.5,  4.6,  4.3,  3.8,  4.5,  4.7,  4.0,  3.8],  # CapEx $B
    fcf   = [ 3.9,  2.9,  4.4,  5.8,  6.7,  3.0,  4.5,  6.0,  6.6],  # FCF $B
    adds  = [  318, -68,  8,   239,  568,  -289, 148,  239,  568],    # K postpaid phone net adds
    churn = [ 0.91, 0.86, 0.82, 0.84, 0.89, 0.88, 0.84, 0.88, 0.91], # % postpaid phone churn
    fwa   = [  3.0,  3.5,  3.8,  4.0,  4.4,  4.7,  5.0,  5.4,  5.9], # M FWA customers (cumulative)
    est   = [False]*9,
)
Q['margin']    = [round(e/s*100, 1) for e, s in zip(Q['ebitda'], Q['svc'])]
Q['capex_pct'] = [round(c/s*100, 1) for c, s in zip(Q['capex'],  Q['svc'])]

VZ_DIM = hex_alpha(ACCENT, 0.40)
BAR_CLR = [ACCENT if not e else VZ_DIM for e in Q['est']]

# KPI: Q4'25 vs Q4'24
KPI_DATA = [
    ("Wireless Service Rev.", 21.0, 20.0, "$B",  "svc_rev"),
    ("Adj. EBITDA",           12.2, 13.2, "$B",  "ebitda"),
    ("Free Cash Flow",         6.6,  6.7, "$B",  "fcf"),
    ("CapEx",                  3.8,  3.8, "$B",  "capex"),
    ("Postpaid Phone Net Adds",568,  568, "K",   "adds"),
    ("FWA (Home Internet)",    5.9,  4.4, "M",   "broadband"),
    ("Postpaid Phone Churn",  0.91, 0.89, "%",   "churn"),
]

# ── 5G Coverage data ──────────────────────────────────────────────────────────
COVERAGE = dict(
    tiers  = ["LTE / 4G (Nationwide)",
              "5G Nationwide<br>(Low/Mid-band, DSS)",
              "5G Ultra Wideband<br>(C-band + mmWave)",
              "C-band 5G<br>(Mid-band 3.7-3.98 GHz)",
              "mmWave 5G<br>(High-band, dense urban)"],
    people = [320, 250, 200, 175, 30],
    pct    = [97,  76,  61,  53,  9],
    colors = [BLU, ORG, ACCENT, YLW, PRP],
)

# ── Fiber milestones (Verizon Fios + FWA + Frontier) ─────────────────────────
BROADBAND_MILESTONES = dict(
    labels  = ["FY2022", "FY2023", "FY2024", "FY2025\n(post-Frontier)", "2028\nTarget"],
    homes_m = [7.3, 8.4, 11.5, 16.3, 20.0],
    is_proj = [False, False, False, False, True],
    notes   = ["7.3M broadband (Fios + FWA)",
               "8.4M broadband + FWA ramp",
               "11.5M total (Frontier close Sep 2024)",
               "16.3M total (full Frontier integration)",
               "~20M target (FWA + Fios + Frontier)"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def get_summary():
    """Return KPI dict for the landing page carrier card."""
    return {
        "id":             ID,
        "svc_rev":        21.0,   # $B Q4 2025 WSR
        "ebitda_margin":  58.1,   # % Q4 2025 (EBITDA/WSR)
        "fcf_annual":     20.1,   # $B FY2025
        "subscribers":    114.9,  # M total wireless connections (approx FY2025)
        "coverage_5g":    76,     # % US pop 5G Nationwide
        "latest_q":       "Q4 2025",
        "capex_pct":      21.7,   # FY2025 CapEx / svc rev %
    }


def generate(output_dir):
    """Build carriers/verizon.html and write to output_dir."""
    print(f"  [Verizon] Building charts...")
    divs = {
        "revenue":      _chart_revenue(),
        "annual":       _chart_annual(),
        "capex":        _chart_capex(),
        "broadband":    _chart_broadband(),
        "subscribers":  _chart_subscribers(),
        "capital":      _chart_capital(),
        "stock":        _chart_stock(),
        "5g_coverage":  _chart_5g_coverage(),
    }
    html = _build_html(divs)
    out_path = os.path.join(output_dir, "verizon.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [Verizon] Written -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def _chart_revenue():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=QTRS, y=Q['svc'], name="Wireless Service Revenue ($B)",
        marker_color=BAR_CLR,
        text=[f"${v:.1f}B" for v in Q['svc']],
        textposition="outside", textfont=dict(size=10, color=TXT),
        hovertemplate="<b>%{x}</b><br>WSR: $%{y:.2f}B<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['margin'], name="EBITDA Margin %",
        mode="lines+markers",
        line=dict(color=TEA, width=2.5, dash="dot"),
        marker=dict(size=7, color=TEA),
        hovertemplate="<b>%{x}</b><br>EBITDA Margin: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(**base_layout(ACCENT, "Quarterly Wireless Service Revenue & EBITDA Margin"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$")
    fig.update_yaxes(title_text="EBITDA Margin %", secondary_y=True,
                     ticksuffix="%", range=[50, 75], showgrid=False)
    fig.add_vrect(x0="Q3'25", x1="Q4'25", fillcolor=ACCENT, opacity=0.07, line_width=0)
    fig.add_annotation(x="Q4'25", y=max(Q['svc'])*1.08, text="Latest Quarter",
                       showarrow=False, font=dict(color=ACCENT, size=10), xref="x", yref="y")
    return fig_to_div(fig, "vz_chart_revenue")


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
                         hovertemplate="FY2026E EBITDA Guidance: $49.5-$50.5B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Annual Financial Performance"), barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    for i, (yr, m) in enumerate(zip(ANN, A['margin'])):
        fig.add_annotation(x=yr, y=A['ebitda'][i] + 1.5,
                           text=f"{m}%", showarrow=False,
                           font=dict(size=9, color=TEA), xref="x", yref="y")
    # C-band annotation
    fig.add_annotation(x="FY2022", y=27, text="C-band auction<br>$45B spectrum spend<br>(2021-22)",
                       showarrow=True, arrowhead=2, arrowcolor=ORG,
                       font=dict(size=9, color=ORG), bgcolor=CARD_BG,
                       bordercolor=ORG, borderwidth=1)
    return fig_to_div(fig, "vz_chart_annual")


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
        x=ANN, y=A['capex_pct'], name="CapEx % of Wireless Service Revenue",
        mode="lines+markers+text",
        line=dict(color=YLW, width=2.5),
        marker=dict(size=9, color=YLW),
        text=[f"{v}%" for v in A['capex_pct']],
        textposition="top center", textfont=dict(size=10, color=YLW),
        hovertemplate="<b>%{x}</b><br>CapEx/WSR: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.add_trace(go.Bar(
        x=['FY2026E'], y=[G26['capex']], name="FY2026E CapEx (guidance)",
        marker_color=hex_alpha(ACCENT, 0.25),
        marker_line_color=ACCENT, marker_line_width=2,
        hovertemplate="FY2026E CapEx: ~$17.5B<extra></extra>",
    ), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "Network CapEx - C-band Build & Efficiency"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$", range=[0, 28])
    fig.update_yaxes(title_text="CapEx as % of WSR", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0, 40])
    annotations = [
        ("FY2022", 23.1, "C-band peak<br>build investment", ORG),
        ("FY2023", 18.8, "C-band<br>normalization", TEA),
        ("FY2024", 17.1, "Sustaining<br>investment", GRN),
        ("FY2025", 17.0, "5G UW<br>densification", ACCENT),
    ]
    for yr, yv, lbl, clr in annotations:
        fig.add_annotation(x=yr, y=yv - 3.5, text=lbl, showarrow=True,
                           arrowhead=2, arrowcolor=clr, font=dict(size=9, color=clr),
                           bgcolor=CARD_BG, bordercolor=clr, borderwidth=1,
                           xref="x", yref="y")
    return fig_to_div(fig, "vz_chart_capex")


def _chart_broadband():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # FWA (Home Internet) trajectory
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['fwa'], name="Fixed Wireless Access (FWA) Customers (M)",
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=hex_alpha(ACCENT, 0.12),
        line=dict(color=ACCENT, width=3),
        marker=dict(size=8, color=ACCENT),
        text=[f"{v:.1f}M" for v in Q['fwa']],
        textposition="top center", textfont=dict(size=9, color=ACCENT),
        hovertemplate="<b>%{x}</b><br>FWA: %{y:.1f}M<extra></extra>",
    ), secondary_y=False)
    # FWA net adds
    fwa_adds = [Q['fwa'][0]] + [Q['fwa'][i] - Q['fwa'][i-1] for i in range(1, len(Q['fwa']))]
    fig.add_trace(go.Bar(
        x=QTRS, y=fwa_adds, name="FWA Net Adds per Quarter (M)",
        marker_color=hex_alpha(ORG, 0.60), opacity=0.8,
        hovertemplate="<b>%{x}</b><br>FWA Net Adds: +%{y:.2f}M<extra></extra>",
    ), secondary_y=True)
    fig.add_hline(y=8.0, line_dash="dot", line_color=ACCENT, line_width=1.5,
                  annotation_text="8M FWA target (2028)", annotation_position="right",
                  annotation_font=dict(color=ACCENT, size=10), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "Fixed Wireless Access (FWA) Growth — Home Internet"))
    apply_axes(fig)
    fig.update_yaxes(title_text="FWA Customers (Millions)", secondary_y=False,
                     ticksuffix="M", range=[0, 10])
    fig.update_yaxes(title_text="Quarterly Net Adds (M)", secondary_y=True,
                     ticksuffix="M", showgrid=False, range=[0, 2])
    fig.add_annotation(x=8, y=6.2,
                       text="5.9M FWA customers<br>Q4 2025",
                       showarrow=True, arrowhead=2, arrowcolor=ACCENT,
                       font=dict(color=ACCENT, size=10), bgcolor=CARD_BG,
                       bordercolor=ACCENT, borderwidth=1, xref="x", yref="y")
    return fig_to_div(fig, "vz_chart_broadband")


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
    churn_clr = [GRN if c <= 0.85 else (YLW if c <= 0.90 else RED) for c in Q['churn']]
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['churn'], name="Postpaid Phone Churn %",
        mode="lines+markers",
        line=dict(color=YLW, width=2.5),
        marker=dict(size=9, color=churn_clr, line=dict(color=TXT, width=1)),
        hovertemplate="<b>%{x}</b><br>Churn: %{y:.2f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(**base_layout(ACCENT, "Subscriber Metrics - Postpaid Net Adds & Churn"))
    apply_axes(fig)
    fig.update_yaxes(title_text="Phone Net Adds (Thousands)", secondary_y=False, range=[-500, 800])
    fig.update_yaxes(title_text="Postpaid Phone Churn %", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0.70, 1.05])
    fig.add_hline(y=0.85, line_dash="dot", line_color=GRN, line_width=1,
                  annotation_text="0.85% best-in-class", annotation_position="right",
                  annotation_font=dict(color=GRN, size=9), secondary_y=True)
    fig.add_hline(y=0, line_dash="solid", line_color=MUTED, line_width=0.8, secondary_y=False)
    return fig_to_div(fig, "vz_chart_subscribers")


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
    # Debt trend line
    fig.add_trace(go.Scatter(x=ANN, y=A['debt'], name="Total Debt ($B)",
                             mode="lines+markers",
                             line=dict(color=RED, width=2, dash="dot"),
                             marker=dict(size=8, color=RED),
                             hovertemplate="<b>%{x}</b><br>Total Debt: $%{y:.1f}B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Capital Allocation - FCF vs CapEx vs Debt Reduction"),
                      barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    fig.add_annotation(x="FY2025", y=155,
                       text="Debt down $14B<br>since 2022 peak",
                       showarrow=True, arrowhead=2, arrowcolor=GRN,
                       font=dict(size=9, color=GRN), bgcolor=CARD_BG,
                       bordercolor=GRN, borderwidth=1)
    return fig_to_div(fig, "vz_chart_capital")


def _chart_stock():
    if not HAS_YF:
        return "<div class='chart-placeholder'>Stock chart unavailable - install yfinance</div>"

    print("    Fetching 3-year stock data (VZ, TMUS, T, IYZ)...")
    end   = date.today()
    start = date(end.year - 3, end.month, end.day)
    tickers = {"VZ":   (ACCENT, "Verizon (VZ)"),
               "TMUS": (PRP,    "T-Mobile (TMUS)"),
               "T":    (BLU,    "AT&T (T)"),
               "IYZ":  (ORG,    "Telecom ETF (IYZ)")}

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
                line=dict(color=clr, width=2.5 if tkr == "VZ" else 1.8),
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
        ("2023-10-24", "Q3 2023 earnings<br>5G UW milestones"),
        ("2024-01-23", "Q4 2023 earnings"),
        ("2024-09-20", "Frontier acquisition<br>close ($20B)"),
        ("2025-01-24", "Q4 2024 earnings"),
        ("2026-01-24", "Q4 2025 earnings<br>FWA 5.9M"),
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
    return fig_to_div(fig, "vz_chart_stock")


def _chart_5g_coverage():
    fig = make_subplots(rows=1, cols=2,
                        column_widths=[0.62, 0.38],
                        specs=[[{"type": "bar"}, {"type": "bar"}]],
                        subplot_titles=["Population Reach by 5G Tier (Millions)",
                                        "% US Population Coverage"])
    for i, (tier, pop, clr) in enumerate(zip(
            COVERAGE['tiers'], COVERAGE['people'], COVERAGE['colors'])):
        fig.add_trace(go.Bar(
            y=[tier], x=[pop], orientation='h', name=tier,
            marker_color=clr, showlegend=False,
            text=[f"{pop}M"], textposition="outside",
            textfont=dict(color=TXT, size=11),
            hovertemplate=f"<b>{tier}</b><br>{pop}M people ({COVERAGE['pct'][i]}%)<extra></extra>",
        ), row=1, col=1)
    for i, (tier, pct, clr) in enumerate(zip(
            COVERAGE['tiers'], COVERAGE['pct'], COVERAGE['colors'])):
        fig.add_trace(go.Bar(
            y=[tier], x=[pct], orientation='h', name=tier,
            marker_color=clr, showlegend=False,
            text=[f"{pct}%"], textposition="outside",
            textfont=dict(color=TXT, size=11),
            hovertemplate=f"<b>{tier}</b><br>{pct}% US population<extra></extra>",
        ), row=1, col=2)
    fig.update_layout(**base_layout(ACCENT, "Verizon 5G Network Coverage by Technology Layer"),
                      height=320, barmode="stack")
    apply_axes(fig)
    fig.update_xaxes(range=[0, 380], row=1, col=1, ticksuffix="M")
    fig.update_xaxes(range=[0, 115], row=1, col=2, ticksuffix="%")
    fig.update_yaxes(tickfont=dict(size=10))
    fig.add_vline(x=335, line_dash="dot", line_color=MUTED, line_width=1,
                  annotation_text="US pop. 335M",
                  annotation_font=dict(color=MUTED, size=9), row=1, col=1)
    return fig_to_div(fig, "vz_chart_5g_coverage")


# ══════════════════════════════════════════════════════════════════════════════
#  HTML ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def _build_html(divs):
    kpi_html = "".join(kpi_card(lbl, val, prior, unit, slug, ACCENT)
                       for lbl, val, prior, unit, slug in KPI_DATA)

    initiatives = [
        ("📡", "C-band 5G Ultra Wideband", "Mid-band spectrum: 3.7-3.98 GHz",
         ["200M+ people covered with C-band 5G UW",
          "$45B C-band spectrum investment (2021-22)",
          "Average speeds 4-10x faster than 4G LTE",
          "Powering FWA Home Internet + enterprise 5G"], ACCENT),
        ("🏠", "Fixed Wireless Access (FWA)", "Home Internet: fastest-growing segment",
         ["5.9M FWA customers as of Q4 2025",
          "Target: 8M+ FWA customers by 2028",
          "$40-50/mo with mobile bundle savings",
          "Primarily on C-band and mmWave coverage"], TEA),
        ("🔗", "Frontier Acquisition", "Largest US fiber acquisition",
         ["$20B deal closed September 2024",
          "25M+ homes in Frontier footprint",
          "Total broadband: 16.3M+ connections",
          "Targets: 10M fiber subs by 2028"], GRN),
        ("🤖", "AI Network Operations", "Network automation and optimization",
         ["AI-driven network self-optimization (SON)",
          "Predictive maintenance on tower infrastructure",
          "Automated congestion management via ML",
          "Agentic AI for customer service (GenAI)"], BLU),
        ("🌆", "Private 5G & Enterprise", "Enterprise network-as-a-service",
         ["Private 5G networks for manufacturing, logistics",
          "5G Edge computing with AWS/Azure/Google",
          "Smart city deployments (FirstNet-like)",
          "Growing enterprise MEC revenue"], PRP),
        ("📶", "mmWave Densification", "High-band ultra-speed zones",
         ["30M+ people covered in dense urban markets",
          "Multi-Gbps speeds at stadiums, transit hubs",
          "Small cell deployments in major metros",
          "Key for venue and enterprise use cases"], ORG),
    ]
    init_html = "".join(initiative_card(*args) for args in initiatives)

    guide_data = [
        ("Adj. EBITDA",           "$49.5-$50.5B", "+1% YoY",  ACCENT),
        ("Free Cash Flow",        "$17.5-$18.5B", "-7% YoY (C-band paydown)", GRN),
        ("CapEx",                 "~$17.5B",       "C-band build sustain", ORG),
        ("WSR Growth",            "2.0-2.8%",      "Wireless service rev YoY", BLU),
    ]
    guide_html = "".join(guidance_card(*args) for args in guide_data)

    body_html = f"""
<!-- KPIs -->
<div class="section" id="kpis">
  <div class="section-title"><span class="dot"></span>Q4 2025 Key Performance Indicators</div>
  <div class="section-sub">Latest quarter vs Q4 2024. Source: Verizon Q4 2025 earnings press release (January 24, 2026).</div>
  <div class="kpi-grid">{kpi_html}</div>
  <div class="est-note">
    <strong>Note on EBITDA:</strong> Q4 2025 Adj. EBITDA ($12.2B) declined vs Q4 2024 ($13.2B) due to one-time items and Frontier integration costs.
    FY2025 total Adj. EBITDA: $50.0B. Total broadband connections reached 16.3M following Frontier close in September 2024.
  </div>
</div>

<!-- Revenue -->
<div class="section" id="revenue">
  <div class="section-title"><span class="dot"></span>Wireless Service Revenue & EBITDA Margin</div>
  <div class="section-sub">Quarterly wireless service revenue trend Q4 2023 to Q4 2025.</div>
  <div class="chart-wrap">
    {divs['revenue']}
    <div class="chart-note">Wireless Service Revenue (WSR) is the primary comparable metric, excluding equipment revenues. Source: Verizon IR quarterly press releases.</div>
  </div>
</div>

<!-- Annual Financials -->
<div class="section" id="financials">
  <div class="section-title"><span class="dot"></span>Annual Financial Performance</div>
  <div class="section-sub">FY2022-FY2025 actuals. EBITDA margin annotated above bars. FY2026 guidance shown for context.</div>
  <div class="chart-grid-2">
    <div class="chart-wrap">
      {divs['annual']}
      <div class="chart-note">C-band spectrum investment ($45B) in 2021-22 drove elevated CapEx. FCF recovered strongly as C-band costs normalized.</div>
    </div>
    <div class="chart-wrap">
      {divs['5g_coverage']}
      <div class="chart-note">5G Nationwide uses DSS (shared spectrum); 5G Ultra Wideband = C-band + mmWave at full speed. Sources: Verizon newsroom, FCC.</div>
    </div>
  </div>
</div>

<!-- Network Domain -->
<div class="section" id="network">
  <div class="section-title"><span class="dot"></span>Network Domain — CapEx, Broadband & Technology Initiatives</div>
  <div class="section-sub">C-band 5G build, FWA Home Internet growth, and enterprise network strategy.</div>
  <div class="chart-grid-2" style="margin-bottom:16px">
    <div class="chart-wrap">
      {divs['capex']}
      <div class="chart-note">CapEx peaked at $23.1B in FY2022 (C-band deployment). Now sustaining at ~$17B with 5G UW densification.</div>
    </div>
    <div class="chart-wrap">
      {divs['broadband']}
      <div class="chart-note">FWA (Home Internet) reached 5.9M customers in Q4 2025. Total broadband (Fios + FWA + Frontier): 16.3M+ as of FY2025.</div>
    </div>
  </div>
  <div class="section-title" style="margin-bottom:12px; font-size:15px;"><span class="dot"></span>Network Technology & Strategic Initiatives</div>
  <div class="init-grid">{init_html}</div>
</div>

<!-- Subscribers -->
<div class="section" id="subscribers">
  <div class="section-title"><span class="dot"></span>Subscriber Metrics</div>
  <div class="section-sub">Postpaid phone net additions and churn. Verizon focus: premium mix, ARPA growth, enterprise. Q4 2025: 568K net adds.</div>
  <div class="chart-wrap">
    {divs['subscribers']}
    <div class="chart-note">Green = churn &le;0.85%; Yellow = 0.85-0.90%; Red = &gt;0.90%. Verizon focuses on premium quality over volume adds.</div>
  </div>
</div>

<!-- Capital -->
<div class="section" id="capital">
  <div class="section-title"><span class="dot"></span>Capital Allocation & Debt Reduction</div>
  <div class="section-sub">FCF generation vs CapEx vs dividend payments. Debt reduction is a key strategic priority ($152B in 2022 to $138.5B in 2025).</div>
  <div class="chart-wrap">
    {divs['capital']}
    <div class="chart-note">Verizon pays one of the highest dividend yields in the S&amp;P 500 (~6%). Debt reduced by ~$14B since 2022. FY2026E FCF: $17.5-$18.5B.</div>
  </div>
</div>

<!-- Stock -->
<div class="section" id="stock">
  <div class="section-title"><span class="dot"></span>Stock Performance — 3-Year vs Peers</div>
  <div class="section-sub">VZ vs T-Mobile (TMUS), AT&amp;T (T), and iShares US Telecom ETF (IYZ). Normalized to 100 at start.</div>
  <div class="chart-wrap">
    {divs['stock']}
    <div class="chart-note">Live data via Yahoo Finance. Key event: Frontier acquisition close September 2024 ($20B).</div>
  </div>
</div>

<!-- Outlook -->
<div class="section" id="outlook">
  <div class="section-title"><span class="dot"></span>FY2026 Guidance & Strategic Outlook</div>
  <div class="section-sub">From Q4 2025 earnings release. FY2026 WSR growth guidance: 2.0-2.8%.</div>
  <div class="guide-grid">{guide_html}</div>
  <div style="margin-top:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div class="init-card" style="border-left:3px solid {ACCENT}">
      <div class="init-title" style="margin-bottom:10px">3-Year Strategic Priorities</div>
      <ul class="init-bullets">
        <li>FWA: Scale to 8M+ Home Internet customers by 2028</li>
        <li>Fiber: 10M Fios subscribers leveraging Frontier assets</li>
        <li>Debt: Reduce to &lt;2.25x Net Debt/EBITDA by 2027</li>
        <li>Enterprise: Grow private 5G and MEC revenue 20%+ CAGR</li>
      </ul>
    </div>
    <div class="init-card" style="border-left:3px solid {TEA}">
      <div class="init-title" style="margin-bottom:10px">Network Leadership Awards</div>
      <ul class="init-bullets">
        <li>Ookla: Fastest 5G Network in US (multi-year)</li>
        <li>RootMetrics: Network Reliability leader (multiple markets)</li>
        <li>PCMag: Fastest Mobile Network 2024</li>
        <li>200M+ people covered with C-band 5G Ultra Wideband</li>
      </ul>
    </div>
  </div>
</div>
"""

    sources_html = """
<strong>Data Sources:</strong>
Verizon Investor Relations (investor.verizon.com) &middot;
Verizon quarterly earnings press releases &middot;
SEC EDGAR 10-K / 10-Q filings &middot;
Yahoo Finance (stock data via yfinance) &middot;
Verizon FY2026 Guidance (Q4 2025 earnings call).<br>
<strong>Note:</strong> Wireless Service Revenue (WSR) used as primary comparable; excludes equipment sales.
Total broadband figures include Fios, FWA (Home Internet), and Frontier acquired customers.
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
        "name":           "Verizon",
        "ticker":         "VZ",
        "accent":         ACCENT,
        "flag":           "🇺🇸",
        "region":         "Americas",
        "latest_quarter": "Q4 2025",
        "stock_period":   "3-Year",
    }

    return page_shell(carrier_meta, nav_links, body_html, sources_html)
