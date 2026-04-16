"""
lib/carriers/tmobile.py — T-Mobile US (TMUS) carrier module
Sources: T-Mobile IR (investor.t-mobile.com), SEC EDGAR, Q4 2025 earnings
Latest:  Q4 2025 / FY2025 (fully reported)
Note:    Q2/Q3 2025 quarterly figures are estimates (FY2025 total minus Q1+Q4 reported)
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
ID     = "tmobile"
ACCENT = "#E20074"   # T-Mobile magenta

# ══════════════════════════════════════════════════════════════════════════════
#  DATA  (all $ billions unless stated; source: T-Mobile IR / SEC EDGAR)
# ══════════════════════════════════════════════════════════════════════════════

ANN = ['FY2022', 'FY2023', 'FY2024', 'FY2025']
A = dict(
    svc   = [61.3, 63.2, 66.2, 71.3],
    ebitda= [26.4, 29.1, 31.8, 33.9],
    ni    = [ 2.6,  8.3, 11.3, 11.0],
    capex = [14.0,  9.8,  8.8, 10.0],
    fcf   = [ 7.7, 13.6, 17.0, 18.0],
    opcf  = [16.8, 18.6, 22.3, 28.0],
    debt  = [72.1, 76.4, 79.0, 80.5],
    shr   = [ 7.7, 14.0, 14.4, None],
    adds  = [ 3.1,  3.1,  3.1,  3.3],    # M postpaid phone net adds (annual)
    conn  = [113.6, 119.7, 129.5, 142.4], # M total customer connections
)
A['margin']    = [round(e/s*100, 1) for e, s in zip(A['ebitda'], A['svc'])]
A['capex_pct'] = [round(c/s*100, 1) for c, s in zip(A['capex'],  A['svc'])]

# FY2026 guidance (from Q4 2025 earnings release)
G26 = dict(ebitda_lo=37.0, ebitda_hi=37.5, fcf_lo=18.0, fcf_hi=18.7, capex=10.0)

# Quarterly  (* = derived from FY2025 total minus Q1+Q4 reported)
QTRS = ["Q4'23", "Q1'24", "Q2'24", "Q3'24", "Q4'24", "Q1'25", "Q2'25*", "Q3'25*", "Q4'25"]
Q = dict(
    svc   = [16.0, 16.1, 16.4, 16.7, 16.9, 16.9, 17.7, 18.0, 18.7],
    ebitda= [ 7.2,  7.6,  8.0,  8.2,  7.9,  8.3,  8.6,  8.6,  8.4],
    ni    = [ 2.0,  2.4,  2.9,  3.1,  3.0,  3.0, 2.95, 2.95,  2.1],
    capex = [ 1.6,  2.6,  2.0,  2.0,  2.2,  2.5,  2.5,  2.5,  2.5],
    fcf   = [ 4.3,  3.3,  3.5,  5.2,  4.1,  4.4,  4.7,  4.7,  4.2],
    adds  = [  934,  532,  738,  865,  903,  495,  900,  943,  962],  # K
    churn = [ 0.96, 0.86, 0.86, 0.86, 0.92, 0.91, 0.90, 0.92, 1.02],
    bb    = [  4.7,  5.2,  5.6,  6.0,  6.4,  6.9,  7.5, 8.85,  9.4], # M broadband
    est   = [False, False, False, False, False, False, True, True, False],
)
Q['margin']    = [round(e/s*100, 1) for e, s in zip(Q['ebitda'], Q['svc'])]
Q['capex_pct'] = [round(c/s*100, 1) for c, s in zip(Q['capex'],  Q['svc'])]

MAG_DIM = hex_alpha(ACCENT, 0.40)
BAR_CLR = [ACCENT if not e else MAG_DIM for e in Q['est']]

KPI_DATA = [
    ("Service Revenue",     18.7, 16.9, "$B", "svc_rev"),
    ("Core Adj. EBITDA",     8.4,  7.9, "$B", "ebitda"),
    ("Net Income",           2.1,  3.0, "$B", "net_income"),
    ("Adj. Free Cash Flow",  4.2,  4.1, "$B", "fcf"),
    ("CapEx",                2.5,  2.2, "$B", "capex"),
    ("Phone Net Adds",       962,  903, "K",  "adds"),
    ("5G Broadband Cust.",   9.4,  6.4, "M",  "broadband"),
    ("Postpaid Churn",      1.02, 0.92, "%",  "churn"),
]

# ── 5G Coverage data ──────────────────────────────────────────────────────────
COVERAGE = dict(
    tiers  = ["LTE (4G)", "Extended Range 5G<br>(Low-band 600 MHz)",
              "Ultra Capacity 5G<br>(Mid-band 2.5 GHz)", "5G Advanced<br>(SA Core — US-only)",
              "mmWave 5G<br>(High-band)"],
    people = [325, 325, 300, 290, 50],
    pct    = [99,  99,  91,  88,  15],
    colors = [BLU, TEA, ACCENT, GRN, YLW],
)

# ── Fiber milestones ──────────────────────────────────────────────────────────
FIBER = dict(
    labels  = ["Q4'22\nStart", "Q4'23", "Q4'24", "Jun'25\nFiber launch",
               "Metronet\nclose (est.)", "2028\nTarget", "2030\nTarget"],
    homes_m = [2.6, 4.7, 6.4, 7.0, 9.5, 12.0, 13.5],
    is_proj = [False, False, False, False, True, True, True],
    notes   = ["2.6M FWA customers",
               "4.7M FWA customers",
               "6.4M FWA customers",
               "Fiber hard launch\n500K homes passed\nLumos acquired ($1.45B)",
               "Metronet pending\n~2M+ homes\n19 states",
               "12M broadband\ncustomers target",
               "12-15M fiber\nhouseholds passed\n~20% IRR target"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def get_summary():
    """Return KPI dict for the landing page carrier card."""
    return {
        "id":             ID,
        "svc_rev":        18.7,   # $B latest quarter
        "ebitda_margin":  44.9,   # % Q4 2025
        "fcf_annual":     18.0,   # $B FY2025
        "subscribers":    142.4,  # M total connections FY2025
        "coverage_5g":    99,     # % US pop (Extended Range)
        "latest_q":       "Q4 2025",
        "capex_pct":      14.0,   # FY2025 CapEx / svc rev %
    }


def generate(output_dir):
    """Build carriers/tmobile.html and write to output_dir."""
    print(f"  [T-Mobile] Building charts...")
    divs = {
        "revenue":      _chart_revenue(),
        "annual":       _chart_annual(),
        "capex":        _chart_capex(),
        "broadband":    _chart_broadband(),
        "subscribers":  _chart_subscribers(),
        "capital":      _chart_capital(),
        "stock":        _chart_stock(),
        "fcf_capex":    _chart_fcf_capex(),
        "5g_coverage":  _chart_5g_coverage(),
        "fiber_rollout": _chart_fiber_rollout(),
    }
    html = _build_html(divs)
    out_path = os.path.join(output_dir, "tmobile.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [T-Mobile] Written -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def _chart_revenue():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=QTRS, y=Q['svc'], name="Service Revenue ($B)",
        marker_color=BAR_CLR,
        text=[f"${v:.1f}B" for v in Q['svc']],
        textposition="outside", textfont=dict(size=10, color=TXT),
        hovertemplate="<b>%{x}</b><br>Service Rev: $%{y:.2f}B<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['margin'], name="EBITDA Margin %",
        mode="lines+markers",
        line=dict(color=TEA, width=2.5, dash="dot"),
        marker=dict(size=7, color=TEA),
        hovertemplate="<b>%{x}</b><br>EBITDA Margin: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(**base_layout(ACCENT, "Quarterly Service Revenue & EBITDA Margin"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$")
    fig.update_yaxes(title_text="EBITDA Margin %", secondary_y=True,
                     ticksuffix="%", range=[40, 55], showgrid=False)
    fig.add_vrect(x0="Q3'25*", x1="Q4'25", fillcolor=ACCENT, opacity=0.07, line_width=0)
    fig.add_annotation(x="Q4'25", y=max(Q['svc'])*1.08, text="◀ Latest Quarter",
                       showarrow=False, font=dict(color=ACCENT, size=10), xref="x", yref="y")
    return fig_to_div(fig, "tmus_chart_revenue")


def _chart_annual():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ANN, y=A['ebitda'], name="Core Adj. EBITDA",
                         marker_color=ACCENT,
                         text=[f"${v:.1f}B" for v in A['ebitda']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>EBITDA: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['ni'], name="Net Income",
                         marker_color=BLU,
                         text=[f"${v:.1f}B" for v in A['ni']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>Net Income: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['fcf'], name="Adj. Free Cash Flow",
                         marker_color=GRN,
                         text=[f"${v:.1f}B" for v in A['fcf']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>FCF: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=['FY2026E'], y=[G26['ebitda_lo']],
                         name="FY2026E EBITDA (guidance low)",
                         marker_color=hex_alpha(ACCENT, 0.15),
                         marker_line_color=ACCENT, marker_line_width=2,
                         hovertemplate="FY2026E EBITDA Guidance: $37.0-$37.5B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Annual Financial Performance"), barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    for i, (yr, m) in enumerate(zip(ANN, A['margin'])):
        fig.add_annotation(x=yr, y=A['ebitda'][i] + 1.5,
                           text=f"{m}%", showarrow=False,
                           font=dict(size=9, color=TEA), xref="x", yref="y")
    return fig_to_div(fig, "tmus_chart_annual")


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
        x=ANN, y=A['capex_pct'], name="CapEx % of Svc Revenue",
        mode="lines+markers+text",
        line=dict(color=YLW, width=2.5),
        marker=dict(size=9, color=YLW),
        text=[f"{v}%" for v in A['capex_pct']],
        textposition="top center", textfont=dict(size=10, color=YLW),
        hovertemplate="<b>%{x}</b><br>CapEx/Svc Rev: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.add_trace(go.Bar(
        x=['FY2026E'], y=[G26['capex']], name="FY2026E CapEx (guidance)",
        marker_color=hex_alpha(ACCENT, 0.25),
        marker_line_color=ACCENT, marker_line_width=2,
        hovertemplate="FY2026E CapEx Guidance: ~$10.0B<extra></extra>",
    ), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "Network CapEx - Annual Trend & Efficiency"))
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", secondary_y=False, tickprefix="$", range=[0, 18])
    fig.update_yaxes(title_text="CapEx as % of Service Revenue", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0, 30])
    annotations = [
        (0, 14.0, "Sprint integration<br>peak investment", ORG),
        (1,  9.8, "Network<br>normalization", TEA),
        (2,  8.8, "CapEx efficiency<br>record low", GRN),
        (3, 10.0, "5G Advanced<br>ramp-up", ACCENT),
    ]
    for i, yv, lbl, clr in annotations:
        fig.add_annotation(x=ANN[i], y=yv - 2.2, text=lbl, showarrow=True,
                           arrowhead=2, arrowcolor=clr, font=dict(size=9, color=clr),
                           bgcolor=CARD_BG, bordercolor=clr, borderwidth=1,
                           xref="x", yref="y")
    return fig_to_div(fig, "tmus_chart_capex")


def _chart_broadband():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=QTRS, y=Q['bb'], name="5G Broadband Customers (M)",
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=hex_alpha(TEA, 0.14),
        line=dict(color=TEA, width=3),
        marker=dict(size=8, color=[TEA if not e else YLW for e in Q['est']],
                    symbol=["circle" if not e else "diamond" for e in Q['est']]),
        text=[f"{v:.2f}M" for v in Q['bb']],
        textposition="top center", textfont=dict(size=9, color=TEA),
        hovertemplate="<b>%{x}</b><br>Broadband: %{y:.2f}M<extra></extra>",
    ), secondary_y=False)
    bb_adds = [Q['bb'][0]] + [Q['bb'][i] - Q['bb'][i-1] for i in range(1, len(Q['bb']))]
    bb_clr  = [TEA if not e else hex_alpha(YLW, 0.55) for e in Q['est']]
    fig.add_trace(go.Bar(
        x=QTRS, y=bb_adds, name="Net Adds per Quarter (M)",
        marker_color=bb_clr, opacity=0.7,
        hovertemplate="<b>%{x}</b><br>Net Adds: +%{y:.2f}M<extra></extra>",
    ), secondary_y=True)
    fig.add_hline(y=12, line_dash="dot", line_color=ACCENT, line_width=1.5,
                  annotation_text="12M target (2028)", annotation_position="right",
                  annotation_font=dict(color=ACCENT, size=10), secondary_y=False)
    fig.update_layout(**base_layout(ACCENT, "5G Broadband Customer Growth Trajectory"))
    apply_axes(fig)
    fig.update_yaxes(title_text="Total Customers (Millions)", secondary_y=False,
                     ticksuffix="M", range=[0, 14])
    fig.update_yaxes(title_text="Quarterly Net Adds (M)", secondary_y=True,
                     ticksuffix="M", showgrid=False, range=[0, 3])
    fig.add_annotation(x=8, y=9.8, text="9.4M total<br>(8.5M 5G BB)",
                       showarrow=True, arrowhead=2, arrowcolor=TEA,
                       font=dict(color=TEA, size=10), bgcolor=CARD_BG,
                       bordercolor=TEA, borderwidth=1, xref="x", yref="y")
    return fig_to_div(fig, "tmus_chart_broadband")


def _chart_subscribers():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    add_clr = [GRN if not e else hex_alpha(GRN, 0.40) for e in Q['est']]
    fig.add_trace(go.Bar(
        x=QTRS, y=Q['adds'], name="Postpaid Phone Net Adds (K)",
        marker_color=add_clr,
        text=[f"{v}K" for v in Q['adds']],
        textposition="outside", textfont=dict(size=9, color=TXT),
        hovertemplate="<b>%{x}</b><br>Phone Net Adds: %{y:,}K<extra></extra>",
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
    fig.update_yaxes(title_text="Phone Net Adds (Thousands)", secondary_y=False, range=[0, 1200])
    fig.update_yaxes(title_text="Postpaid Phone Churn %", secondary_y=True,
                     ticksuffix="%", showgrid=False, range=[0.7, 1.2])
    fig.add_hline(y=0.90, line_dash="dot", line_color=GRN, line_width=1,
                  annotation_text="0.90% benchmark", annotation_position="right",
                  annotation_font=dict(color=GRN, size=9), secondary_y=True)
    return fig_to_div(fig, "tmus_chart_subscribers")


def _chart_capital():
    shr_vals = [v if v is not None else 0 for v in A['shr']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ANN, y=A['fcf'], name="Adj. Free Cash Flow",
                         marker_color=GRN,
                         text=[f"${v:.1f}B" for v in A['fcf']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>FCF: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN, y=A['capex'], name="CapEx (Network Investment)",
                         marker_color=ORG,
                         text=[f"${v:.1f}B" for v in A['capex']],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>CapEx: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=ANN[:3], y=shr_vals[:3], name="Shareholder Returns",
                         marker_color=PRP,
                         text=[f"${v:.1f}B" for v in shr_vals[:3]],
                         textposition="outside", textfont=dict(size=10, color=TXT),
                         hovertemplate="<b>%{x}</b><br>Shareholder Returns: $%{y:.1f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=['FY2026E'], y=[(G26['fcf_lo'] + G26['fcf_hi'])/2],
                         name="FY2026E FCF (guidance mid)",
                         marker_color=hex_alpha(GRN, 0.25),
                         marker_line_color=GRN, marker_line_width=2,
                         hovertemplate="FY2026E FCF Guidance: $18.0-$18.7B<extra></extra>"))
    fig.update_layout(**base_layout(ACCENT, "Capital Allocation - FCF vs CapEx vs Shareholder Returns"),
                      barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    fig.add_annotation(x=1, y=18, text="$31.4B program-to-date<br>shareholder returns (thru Q4'24)",
                       showarrow=False, font=dict(size=9, color=PRP, style="italic"),
                       bgcolor=CARD_BG, bordercolor=PRP, borderwidth=1)
    return fig_to_div(fig, "tmus_chart_capital")


def _chart_stock():
    if not HAS_YF:
        return "<div class='chart-placeholder'>Stock chart unavailable - install yfinance</div>"

    print("    Fetching 3-year stock data (TMUS, T, VZ, IYZ)...")
    end   = date.today()
    start = date(end.year - 3, end.month, end.day)
    tickers = {"TMUS": (ACCENT, "T-Mobile (TMUS)"),
               "T":    (BLU,    "AT&T (T)"),
               "VZ":   (ORG,    "Verizon (VZ)"),
               "IYZ":  (PRP,    "Telecom ETF (IYZ)")}

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
                line=dict(color=clr, width=2.5 if tkr == "TMUS" else 1.8),
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
        ("2023-10-25", "Capital Markets Day<br>raised 2027 targets"),
        ("2024-01-29", "FY2023 earnings<br>record FCF"),
        ("2025-01-29", "FY2024 earnings<br>best-ever net income"),
        ("2025-04-28", "Q1 2025<br>best-ever Q1"),
        ("2026-01-28", "FY2025 earnings<br>broadband 9.4M"),
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
    return fig_to_div(fig, "tmus_chart_stock")


def _chart_fcf_capex():
    fig = go.Figure()
    fcf_clr   = [GRN if not e else hex_alpha(GRN, 0.40) for e in Q['est']]
    capex_clr = [ORG if not e else hex_alpha(ORG, 0.40) for e in Q['est']]
    fig.add_trace(go.Bar(x=QTRS, y=Q['fcf'], name="Adj. Free Cash Flow",
                         marker_color=fcf_clr,
                         hovertemplate="<b>%{x}</b><br>FCF: $%{y:.2f}B<extra></extra>"))
    fig.add_trace(go.Bar(x=QTRS, y=Q['capex'], name="CapEx",
                         marker_color=capex_clr,
                         hovertemplate="<b>%{x}</b><br>CapEx: $%{y:.2f}B<extra></extra>"))
    residual = [f - c for f, c in zip(Q['fcf'], Q['capex'])]
    fig.add_trace(go.Scatter(
        x=QTRS, y=residual, name="FCF - CapEx (cash after network spend)",
        mode="lines+markers",
        line=dict(color=TEA, width=2, dash="dot"),
        marker=dict(size=7, color=TEA),
        hovertemplate="<b>%{x}</b><br>FCF-CapEx: $%{y:.2f}B<extra></extra>",
    ))
    fig.update_layout(**base_layout(ACCENT, "Quarterly FCF vs CapEx"), barmode="group")
    apply_axes(fig)
    fig.update_yaxes(title_text="USD Billions", tickprefix="$")
    fig.add_vrect(x0="Q3'25*", x1="Q4'25", fillcolor=ACCENT, opacity=0.07, line_width=0)
    return fig_to_div(fig, "tmus_chart_fcf_capex")


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
    fig.update_layout(**base_layout(ACCENT, "T-Mobile 5G Network Coverage by Technology Layer"),
                      height=320, barmode="stack")
    apply_axes(fig)
    fig.update_xaxes(range=[0, 380], row=1, col=1, ticksuffix="M")
    fig.update_xaxes(range=[0, 115], row=1, col=2, ticksuffix="%")
    fig.update_yaxes(tickfont=dict(size=10))
    fig.add_vline(x=335, line_dash="dot", line_color=MUTED, line_width=1,
                  annotation_text="US pop. 335M",
                  annotation_font=dict(color=MUTED, size=9), row=1, col=1)
    return fig_to_div(fig, "tmus_chart_5g_coverage")


def _chart_fiber_rollout():
    fig = go.Figure()
    clr_act = [TEA if not p else hex_alpha(ACCENT, 0.45) for p in FIBER['is_proj']]
    fig.add_trace(go.Bar(
        x=FIBER['labels'], y=FIBER['homes_m'],
        name="Homes / Customers (M)",
        marker_color=clr_act,
        text=[f"{v:.1f}M" for v in FIBER['homes_m']],
        textposition="outside", textfont=dict(size=10, color=TXT),
        hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>",
        customdata=FIBER['notes'],
    ))
    fig.add_hline(y=12.0, line_dash="dot", line_color=ACCENT, line_width=1.5,
                  annotation_text="12M broadband target (2028)",
                  annotation_position="right",
                  annotation_font=dict(color=ACCENT, size=10))
    fig.add_hline(y=13.5, line_dash="dot", line_color=PRP, line_width=1.2,
                  annotation_text="12-15M fiber HH target (2030)",
                  annotation_position="right",
                  annotation_font=dict(color=PRP, size=10))
    fig.add_annotation(x="Jun'25\nFiber launch", y=8.5,
                       text="Fiber launch<br>Jun 5, 2025<br>5-yr price lock",
                       showarrow=True, arrowhead=2, arrowcolor=GRN,
                       font=dict(color=GRN, size=9), bgcolor=CARD_BG,
                       bordercolor=GRN, borderwidth=1)
    fig.update_layout(**base_layout(ACCENT, "Broadband & Fiber Rollout Roadmap"), height=400)
    apply_axes(fig)
    fig.update_yaxes(title_text="Millions of Homes / Customers", ticksuffix="M", range=[0, 16])
    fig.add_vline(x=3.5, line_dash="dash", line_color=MUTED, line_width=1,
                  annotation_text="  Projected ->",
                  annotation_position="top right",
                  annotation_font=dict(color=MUTED, size=9))
    return fig_to_div(fig, "tmus_chart_fiber_rollout")


# ══════════════════════════════════════════════════════════════════════════════
#  HTML ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def _build_html(divs):
    kpi_html = "".join(kpi_card(lbl, val, prior, unit, slug, ACCENT)
                       for lbl, val, prior, unit, slug in KPI_DATA)

    initiatives = [
        ("🧠", "AI-RAN Innovation Center", "Partners: NVIDIA · Ericsson · Nokia",
         ["Industry-first AI + RAN integration lab",
          "Brings AI inference to the Radio Access Network",
          "Targets real-time network optimization via AI",
          "Accelerates 5G Advanced performance gains"], ACCENT),
        ("🤝", "IntentCX — AI Customer Platform", "Partner: OpenAI",
         ["Predictive AI platform for customer engagement",
          "Target: 75% reduction in inbound care contacts",
          "Powered by OpenAI LLMs on T-Mobile network data",
          "Redefines Care operations across enterprise segment"], BLU),
        ("📡", "Customer Driven Coverage", "AI-driven network site prioritization",
         ["AI algorithmic model ranks tens of thousands of pending sites",
          "Prioritizes builds based on specific customer demand signals",
          "Enables higher ROI per network dollar spent",
          "Part of $9.5B FY2025 CapEx investment strategy"], TEA),
        ("🌐", "5G Advanced — Standalone Core", "Only US carrier with nationwide SA 5G core",
         ["US-first 5G Advanced broad deployment",
          "Record 6.3 Gbps downlink speeds achieved",
          "Voice over New Radio (VoNR) in production",
          "4-carrier aggregation + Massive MIMO rollout"], GRN),
        ("🛰️", "T-Satellite (Direct-to-Device)", "Satellite network on modern smartphones",
         ["Only US satellite service on most modern smartphones",
          "Over 1 million messages delivered",
          "Hundreds of thousands of active customers",
          "Eliminates dead zones without new hardware"], PRP),
        ("🏠", "Fiber & Fixed Wireless (5G Home)", "Fastest-growing broadband in the US",
         ["9.4M total broadband customers (Q4 2025)",
          "8.5M on 5G broadband specifically",
          "Target: 12M broadband by 2028",
          "Fiber: 12-15M households passed by 2030 (~20% IRR)"], ORG),
    ]
    init_html = "".join(initiative_card(*args) for args in initiatives)

    guide_data = [
        ("Core Adj. EBITDA", "$37.0-$37.5B", "+10% YoY", ACCENT),
        ("Adj. Free Cash Flow", "$18.0-$18.7B", "+3% YoY", GRN),
        ("CapEx", "~$10.0B", "5G Advanced ramp", ORG),
        ("Postpaid Net Adds", "TBD (2026)", "Based on Q1 2026 guidance", BLU),
    ]
    guide_html = "".join(guidance_card(*args) for args in guide_data)

    body_html = f"""
<!-- KPIs -->
<div class="section" id="kpis">
  <div class="section-title"><span class="dot"></span>Q4 2025 Key Performance Indicators</div>
  <div class="section-sub">Latest quarter vs Q4 2024 (1 year back). All values from T-Mobile IR press releases.</div>
  <div class="kpi-grid">{kpi_html}</div>
  <div class="est-note">
    <strong>Net Income note:</strong> Q4 2025 net income ($2.1B) declined vs Q4 2024 ($3.0B); FY2025 full-year $11.0B vs $11.3B (largely flat). EPS grew slightly YoY due to share buybacks.
    Q1 2026 earnings call: <strong>April 28, 2026</strong>.
  </div>
</div>

<!-- Revenue -->
<div class="section" id="revenue">
  <div class="section-title"><span class="dot"></span>Service Revenue & EBITDA Margin</div>
  <div class="section-sub">Quarterly service revenue trend Q4 2023 to Q4 2025. Bars with * are Q2/Q3 2025 estimates.</div>
  <div class="est-note">
    <strong>* Estimated quarters</strong> (Q2'25, Q3'25): Derived from FY2025 reported totals minus Q1+Q4 reported actuals. Labeled with lighter shading.
  </div>
  <div class="chart-wrap">
    {divs['revenue']}
    <div class="chart-note">Source: T-Mobile IR quarterly earnings press releases</div>
  </div>
</div>

<!-- Annual Financials -->
<div class="section" id="financials">
  <div class="section-title"><span class="dot"></span>Annual Financial Performance</div>
  <div class="section-sub">FY2022-FY2025 actuals. EBITDA margin annotated above bars. FY2026 EBITDA guidance shown for context.</div>
  <div class="chart-grid-2">
    <div class="chart-wrap">
      {divs['annual']}
      <div class="chart-note">FY2022 net income impacted by Sprint merger integration costs.</div>
    </div>
    <div class="chart-wrap">
      {divs['fcf_capex']}
      <div class="chart-note">FCF-CapEx line shows residual cash available after network investment.</div>
    </div>
  </div>
</div>

<!-- Network Domain -->
<div class="section" id="network">
  <div class="section-title"><span class="dot"></span>Network Domain — CapEx, 5G Broadband & AI Initiatives</div>
  <div class="section-sub">Primary lens: Network investment trends, 5G deployment, fixed wireless growth, and network AI/software strategy.</div>
  <div class="chart-grid-2" style="margin-bottom:16px">
    <div class="chart-wrap">
      {divs['capex']}
      <div class="chart-note">CapEx peaked at $14B in FY2022 (Sprint integration). Normalized to $8.8B in FY2024.</div>
    </div>
    <div class="chart-wrap">
      {divs['broadband']}
      <div class="chart-note">9.4M total broadband (8.5M on 5G broadband) as of Q4 2025. Target: 12M by 2028.</div>
    </div>
  </div>
  <div class="section-title" style="margin-bottom:12px; font-size:15px;"><span class="dot"></span>Network AI, Software & Technology Initiatives</div>
  <div class="init-grid">{init_html}</div>
</div>

<!-- 5G Coverage & Fiber -->
<div class="section" id="coverage">
  <div class="section-title"><span class="dot"></span>5G Coverage & Fiber Rollout Plans</div>
  <div class="section-sub">5G network reach by technology layer and broadband/fiber expansion roadmap through 2030.</div>
  <div class="chart-wrap" style="margin-bottom:16px">
    {divs['5g_coverage']}
    <div class="chart-note">Extended Range 5G: 325M (99%) · Ultra Capacity 5G: 300M (91%) · 5G Advanced: US-only nationwide SA core · mmWave: dense urban markets</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin-bottom:20px">
    <div class="kpi-card" style="border-top:3px solid {TEA}"><div class="kpi-label">Extended Range 5G</div><div class="kpi-value" style="color:{TEA}">325M</div><div class="kpi-delta" style="color:{MUTED}">99% US pop · Low-band 600 MHz</div></div>
    <div class="kpi-card" style="border-top:3px solid {ACCENT}"><div class="kpi-label">Ultra Capacity 5G</div><div class="kpi-value" style="color:{ACCENT}">300M</div><div class="kpi-delta" style="color:{MUTED}">91% US pop · Mid-band 2.5 GHz</div></div>
    <div class="kpi-card" style="border-top:3px solid {GRN}"><div class="kpi-label">5G Advanced (SA Core)</div><div class="kpi-value" style="color:{GRN}">Only US</div><div class="kpi-delta" style="color:{MUTED}">Nation's only nationwide SA 5G core</div></div>
    <div class="kpi-card" style="border-top:3px solid {YLW}"><div class="kpi-label">Peak 5G Speed</div><div class="kpi-value" style="color:{YLW}">6.3 Gbps</div><div class="kpi-delta" style="color:{MUTED}">Record downlink · 4-carrier aggregation</div></div>
    <div class="kpi-card" style="border-top:3px solid {BLU}"><div class="kpi-label">5G Cities Covered</div><div class="kpi-value" style="color:{BLU}">3,888</div><div class="kpi-delta" style="color:{MUTED}">Including rural via US Cellular (2025)</div></div>
    <div class="kpi-card" style="border-top:3px solid {PRP}"><div class="kpi-label">T-Satellite</div><div class="kpi-value" style="color:{PRP}">Live</div><div class="kpi-delta" style="color:{MUTED}">Direct-to-device · No dead zones</div></div>
  </div>
  <div class="chart-wrap" style="margin-bottom:16px">
    {divs['fiber_rollout']}
    <div class="chart-note">Fiber launch: Jun 5, 2025. Lumos acquired $1.45B (Apr 2025). Metronet pending (~2M+ homes, 19 states). Bars with lighter shade = projected.</div>
  </div>
</div>

<!-- Subscribers -->
<div class="section" id="subscribers">
  <div class="section-title"><span class="dot"></span>Subscriber Metrics</div>
  <div class="section-sub">Postpaid phone net additions and churn. Q4 2025: 962K net adds (+7% YoY). FY2025 total: 3.3M phone net adds (industry best).</div>
  <div class="chart-wrap">
    {divs['subscribers']}
    <div class="chart-note">Green = churn &le;0.90%; Yellow = 0.90-0.95%; Red = &gt;0.95%. FY2025 full-year churn: 0.93%.</div>
  </div>
</div>

<!-- Capital -->
<div class="section" id="capital">
  <div class="section-title"><span class="dot"></span>Capital Allocation & Leverage</div>
  <div class="section-sub">FCF vs network CapEx vs shareholder returns. FY2025: $18B FCF, $10B CapEx.</div>
  <div class="chart-wrap">
    {divs['capital']}
    <div class="chart-note">Program-to-date (Q3 2022 - Q4 2024): $31.4B returned. FY2026E FCF guidance: $18.0-$18.7B.</div>
  </div>
</div>

<!-- Stock -->
<div class="section" id="stock">
  <div class="section-title"><span class="dot"></span>Stock Performance — 3-Year vs Peers</div>
  <div class="section-sub">TMUS vs AT&amp;T (T), Verizon (VZ), and iShares US Telecom ETF (IYZ). Normalized to 100 at start.</div>
  <div class="chart-wrap">
    {divs['stock']}
    <div class="chart-note">Live data via Yahoo Finance. Q1 2026 earnings: April 28, 2026.</div>
  </div>
</div>

<!-- Outlook -->
<div class="section" id="outlook">
  <div class="section-title"><span class="dot"></span>FY2026 Guidance & Strategic Outlook</div>
  <div class="section-sub">From Q4 2025 earnings release. Q1 2026 results due April 28, 2026.</div>
  <div class="guide-grid">{guide_html}</div>
  <div style="margin-top:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div class="init-card" style="border-left:3px solid {ACCENT}">
      <div class="init-title" style="margin-bottom:10px">2027 Long-Range Targets</div>
      <ul class="init-bullets">
        <li>Service Revenue: <strong>$75-76B</strong> (~5% CAGR from FY2023)</li>
        <li>Core Adj. EBITDA: <strong>$38-39B</strong> (~7% CAGR)</li>
        <li>Adj. Free Cash Flow: <strong>$18-19B</strong></li>
        <li>Stockholder returns through 2027: <strong>~$50B program</strong></li>
      </ul>
    </div>
    <div class="init-card" style="border-left:3px solid {TEA}">
      <div class="init-title" style="margin-bottom:10px">Competitive Network Position</div>
      <ul class="init-bullets">
        <li>J.D. Power network quality sweep: 5 of 6 US regions (FY2025)</li>
        <li>Ookla Best Mobile Network: back-to-back years</li>
        <li>Opensignal Best Overall Experience: 4 consecutive years</li>
        <li>Only US carrier with nationwide standalone 5G core</li>
      </ul>
    </div>
  </div>
</div>
"""

    sources_html = """
<strong>Data Sources:</strong>
T-Mobile Investor Relations (investor.t-mobile.com) &middot;
T-Mobile Newsroom earnings press releases &middot;
SEC EDGAR 10-K / 10-Q filings &middot;
Yahoo Finance (stock data via yfinance) &middot;
T-Mobile 2024 Capital Markets Day presentation.<br>
<strong>Note:</strong> Q2 2025 and Q3 2025 quarterly figures marked with * are estimates derived from FY2025 reported totals minus Q1 and Q4 reported actuals.
All financial data in USD billions unless stated. Q1 2026 results not yet reported (earnings call April 28, 2026).<br>
"""

    nav_links = [
        ("kpis",        "KPIs"),
        ("revenue",     "Revenue"),
        ("financials",  "Financials"),
        ("network",     "Network Domain"),
        ("coverage",    "5G & Fiber"),
        ("subscribers", "Subscribers"),
        ("capital",     "Capital"),
        ("stock",       "Stock"),
        ("outlook",     "Outlook"),
    ]

    carrier_meta = {
        "name":           "T-Mobile US",
        "ticker":         "TMUS",
        "accent":         ACCENT,
        "flag":           "🇺🇸",
        "region":         "Americas",
        "latest_quarter": "Q4 2025",
        "stock_period":   "3-Year",
    }

    return page_shell(carrier_meta, nav_links, body_html, sources_html)
