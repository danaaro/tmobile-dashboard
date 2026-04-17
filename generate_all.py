#!/usr/bin/env python3
"""
generate_all.py — Master runner for the multi-carrier executive dashboard
─────────────────────────────────────────────────────────────────────────
Run:   python generate_all.py
Out:   carriers/tmobile.html
       carriers/verizon.html
       carriers/att.html
       index.html  (landing page)

Add a new carrier:
  1. Add entry to lib/registry.py
  2. Create lib/carriers/<id>.py with get_summary() + generate()
  3. Re-run this script
"""

import sys, os, importlib, base64, io
from datetime import datetime

# Force UTF-8 so emoji/Unicode in print() works on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CARRIERS_DIR = os.path.join(SCRIPT_DIR, "carriers")
LOGOS_DIR    = os.path.join(SCRIPT_DIR, "Logos")
GENERATED    = datetime.now().strftime("%B %d, %Y  %H:%M")

# ── Logo file mapping ─────────────────────────────────────────────────────────
LOGO_FILES = {
    "tmobile":    "TMUS_original.png",
    "verizon":    "Verizon_2024.svg",
    "att":        "AT&T_logo_2016.svg.png",
    "vmo2":       "VIRGIN_MEDIA_O2_LOGO_SECONDARY_COLOUR_RGB-300x170-1.png",
    "odido":      "Odido_2023_Logo.png",
    "vf_germany": "Vodafone new.png",
    "comcast":    "Comcast_logo_2000.svg",
    "globe":      "Globe-logo.png",
}
_logo_uri_cache = {}


def _logo_data_uri(carrier_id):
    """Return a base64 data URI for the carrier's logo, resizing PNGs to max 200×60."""
    if carrier_id in _logo_uri_cache:
        return _logo_uri_cache[carrier_id]

    fname = LOGO_FILES.get(carrier_id)
    if not fname:
        _logo_uri_cache[carrier_id] = None
        return None

    fpath = os.path.join(LOGOS_DIR, fname)
    if not os.path.exists(fpath):
        _logo_uri_cache[carrier_id] = None
        return None

    # SVG: read as-is, embed as svg+xml
    if fname.lower().endswith(".svg"):
        with open(fpath, "rb") as f:
            data = f.read()
        b64  = base64.b64encode(data).decode("ascii")
        uri  = f"data:image/svg+xml;base64,{b64}"
        _logo_uri_cache[carrier_id] = uri
        return uri

    # PNG (including .svg.png and .wine.png): auto-crop then resize
    try:
        from PIL import Image
        img = Image.open(fpath).convert("RGBA")

        # Auto-crop: use alpha channel to find actual logo content.
        # Many logos sit on a large transparent canvas; cropping removes dead space.
        r, g, b, a = img.split()
        bbox = a.point(lambda x: 255 if x > 20 else 0).getbbox()
        if bbox:
            pad = 6  # small padding so logo doesn't touch edge
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(img.width,  bbox[2] + pad)
            y1 = min(img.height, bbox[3] + pad)
            img = img.crop((x0, y0, x1, y1))

        img.thumbnail((200, 60), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64  = base64.b64encode(buf.getvalue()).decode("ascii")
        uri  = f"data:image/png;base64,{b64}"
        _logo_uri_cache[carrier_id] = uri
        return uri
    except Exception:
        pass

    _logo_uri_cache[carrier_id] = None
    return None

# Ensure carriers/ output dir exists
os.makedirs(CARRIERS_DIR, exist_ok=True)

# ── Shared palette (mirrors lib/base.py) ──────────────────────────────────────
DARK_BG = "#0a0e1a"
CARD_BG = "#111827"
TXT     = "#f1f5f9"
MUTED   = "#94a3b8"
GRID    = "#1e2940"
GRN     = "#22c55e"
RED     = "#ef4444"
YLW     = "#f59e0b"
BLU     = "#3b82f6"
PRP     = "#8b5cf6"
TEA     = "#14b8a6"
ORG     = "#f97316"


# ══════════════════════════════════════════════════════════════════════════════
#  LANDING PAGE  (index.html)
# ══════════════════════════════════════════════════════════════════════════════

def hex_alpha(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def logo_chip(meta):
    """Return carrier logo img tag (base64 embedded) or fallback text chip."""
    accent     = meta["accent"]
    short      = meta.get("short", meta["id"].upper())
    carrier_id = meta["id"]

    uri = _logo_data_uri(carrier_id)
    if uri:
        # Subtle pill wrapper so logo is visible on the dark card background
        return (f'<div style="background:rgba(255,255,255,0.07);border-radius:6px;'
                f'padding:5px 10px;display:inline-flex;align-items:center;'
                f'border:1px solid rgba(255,255,255,0.10)">'
                f'<img src="{uri}" alt="{meta["name"]}" '
                f'style="height:28px;max-width:100px;object-fit:contain;display:block">'
                f'</div>')

    # Fallback: accent-colored text chip
    r, g, b = [int(accent.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    bg  = f"rgba({r},{g},{b},0.12)"
    bdr = f"rgba({r},{g},{b},0.55)"
    return (f'<div style="background:{bg};border:1px solid {bdr};color:{accent};'
            f'border-radius:6px;padding:4px 10px;font-size:11px;font-weight:800;'
            f'letter-spacing:0.5px;white-space:nowrap;font-family:Inter,sans-serif">'
            f'{short}</div>')


def carrier_card(meta, summary):
    """Render a carrier card for the landing page."""
    accent  = meta["accent"]
    name    = meta["name"]
    flag    = meta["flag"]
    region  = meta["region"]
    status  = meta["status"]
    phase   = meta["phase"]
    ticker  = meta.get("ticker") or "Private"
    exchange= meta.get("exchange", "")
    out_file= meta.get("out_file", f"carriers/{meta['id']}.html")

    if status == "active" and summary:
        svc_rev  = summary.get("svc_rev", "—")
        margin   = summary.get("ebitda_margin", "—")
        fcf      = summary.get("fcf_annual", "—")
        subs     = summary.get("subscribers", "—")
        cov5g    = summary.get("coverage_5g", "—")
        latest_q = summary.get("latest_q", meta.get("latest_q", ""))

        svc_rev_str = f"${svc_rev:.1f}B" if isinstance(svc_rev, (int, float)) else "—"
        margin_str  = f"{margin:.1f}%"   if isinstance(margin,  (int, float)) else "—"
        fcf_str     = f"${fcf:.1f}B"     if isinstance(fcf,     (int, float)) else "N/A"
        subs_str    = f"{subs:.0f}M"     if isinstance(subs,    (int, float)) else "—"
        cov5g_str   = f"{cov5g}%"        if isinstance(cov5g, (int, float)) else "N/A"
        kpi_html = f"""
        <div class="lc-kpis">
          <div class="lc-kpi"><div class="lc-kpi-label">Svc Rev (Q)</div><div class="lc-kpi-val">{svc_rev_str}</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">EBITDA Margin</div><div class="lc-kpi-val">{margin_str}</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">FCF (Annual)</div><div class="lc-kpi-val">{fcf_str}</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">Subscribers</div><div class="lc-kpi-val">{subs_str}</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">5G Coverage</div><div class="lc-kpi-val">{cov5g_str}</div></div>
        </div>
        <a href="{out_file}" class="lc-btn" style="background:{accent}">View Dashboard &rarr;</a>"""
        status_badge = logo_chip(meta)
        footer_note  = f'<span>Latest: {latest_q}</span>'
    else:
        phase_colors = {2: YLW, 3: ORG}
        pcol = phase_colors.get(phase, MUTED)
        kpi_html = f"""
        <div class="lc-coming">
          <div style="font-size:32px;margin-bottom:8px">{flag}</div>
          <div style="font-size:13px;font-weight:600;color:{TXT}">Phase {phase} — Coming Soon</div>
          <div style="font-size:11px;color:{MUTED};margin-top:4px">{meta.get('latest_q','')}</div>
        </div>"""
        status_badge = logo_chip(meta)
        footer_note  = f'<span>Planned · {region}</span>'

    return f"""
<div class="lc-card" data-region="{region}" style="border-top:3px solid {accent}">
  <div class="lc-card-header">
    <div>
      <div class="lc-name">{flag} {name}</div>
      <div class="lc-ticker">{ticker} &middot; {exchange}</div>
    </div>
    {status_badge}
  </div>
  {kpi_html}
  <div class="lc-footer">
    {footer_note}
    <span style="color:{MUTED}">{region}</span>
  </div>
</div>"""


def comparison_chart_div(active_carriers_data):
    """Build a comparison bar chart for all active carriers."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        return "<div class='chart-placeholder'>plotly not installed</div>"

    names   = [d['meta']['short'] for d in active_carriers_data]
    accents = [d['meta']['accent'] for d in active_carriers_data]
    svc_rev = [d['summary'].get('svc_rev') or 0 for d in active_carriers_data]
    margins = [d['summary'].get('ebitda_margin') or 0 for d in active_carriers_data]
    fcf_raw = [d['summary'].get('fcf_annual') for d in active_carriers_data]
    fcf     = [v if v is not None else 0 for v in fcf_raw]
    cov5g_raw = [d['summary'].get('coverage_5g') for d in active_carriers_data]
    cov5g     = [v if v is not None else 0 for v in cov5g_raw]

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=4,
                        subplot_titles=["Service Rev (Q, $B)", "EBITDA Margin %",
                                        "FCF Annual ($B)", "5G Coverage %"])

    def _bar(nm, clr, v, fmt, tip, col, first=False):
        return go.Bar(x=[nm], y=[v], name=nm, marker_color=clr,
                      showlegend=False, cliponaxis=False,
                      text=[fmt.format(v)], textposition="outside",
                      textfont=dict(color=TXT, size=10),
                      hovertemplate=f"<b>{nm}</b><br>{tip}<extra></extra>")

    for i, (nm, clr, v) in enumerate(zip(names, accents, svc_rev)):
        fig.add_trace(_bar(nm, clr, v, "${:.1f}B", f"Svc Rev: ${v:.1f}B", 1), row=1, col=1)
    for i, (nm, clr, v) in enumerate(zip(names, accents, margins)):
        fig.add_trace(_bar(nm, clr, v, "{:.1f}%", f"EBITDA Margin: {v:.1f}%", 2), row=1, col=2)
    for i, (nm, clr, v, vr) in enumerate(zip(names, accents, fcf, fcf_raw)):
        lbl = "N/A" if vr is None else f"${v:.1f}B"
        tip = "FCF: N/A (private)" if vr is None else f"FCF: ${v:.1f}B"
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr,
                             showlegend=False, cliponaxis=False,
                             text=[lbl], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>{tip}<extra></extra>"),
                      row=1, col=3)
    for i, (nm, clr, v, vr) in enumerate(zip(names, accents, cov5g, cov5g_raw)):
        lbl = "N/A" if vr is None else f"{v}%"
        tip = "5G Coverage: N/A (MVNO)" if vr is None else f"5G Coverage: {v}%"
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr,
                             showlegend=False, cliponaxis=False,
                             text=[lbl], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>{tip}<extra></extra>"),
                      row=1, col=4)

    # Add 25% headroom above each subgraph max so outside labels aren't clipped
    def _ymax(vals): return max(vals) * 1.25 if vals else 100
    fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font=dict(color=TXT, family="'Inter','Segoe UI',Arial,sans-serif", size=11),
        margin=dict(l=30, r=30, t=55, b=30), height=320,
        showlegend=False,
        hoverlabel=dict(bgcolor="#1e293b", font_size=11),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(range=[0, _ymax(svc_rev)],  row=1, col=1)
    fig.update_yaxes(range=[0, _ymax(margins)],  row=1, col=2)
    fig.update_yaxes(range=[0, _ymax(fcf)],      row=1, col=3)
    fig.update_yaxes(range=[0, _ymax(cov5g)],    row=1, col=4)
    return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                       div_id="comparison_chart",
                       config={"displayModeBar": False, "responsive": True})


def build_landing_page(registry, summaries):
    """Build the index.html landing page."""
    from lib.registry import CARRIERS

    # Separate active vs planned
    active_data  = []
    planned_data = []
    for cid, meta in CARRIERS.items():
        entry = {"meta": meta, "summary": summaries.get(cid, {})}
        if meta["status"] == "active":
            active_data.append(entry)
        else:
            planned_data.append(entry)

    # Build comparison chart from active carriers
    comp_div = comparison_chart_div(active_data)

    # Build carrier cards grouped by region
    REGION_ORDER = [
        ("Americas", "🌎"),
        ("Europe",   "🌍"),
        ("APAC",     "🌏"),
    ]

    def _cards_for_region(region, entries):
        cards = [carrier_card(e["meta"], e["summary"])
                 for e in entries if e["meta"]["region"] == region]
        return "".join(cards)

    all_entries = active_data + planned_data
    region_blocks = ""
    for region_name, region_flag in REGION_ORDER:
        region_entries = [e for e in all_entries if e["meta"]["region"] == region_name]
        if not region_entries:
            continue
        n_active  = sum(1 for e in region_entries if e["meta"]["status"] == "active")
        n_total   = len(region_entries)
        count_str = f"{n_active} active" + (f" · {n_total-n_active} planned" if n_total > n_active else "")
        cards_html = _cards_for_region(region_name, region_entries)
        region_blocks += f"""
<div class="region-section" data-region="{region_name}">
  <div class="region-header">
    <span class="rh-dot"></span>
    <span>{region_flag} {region_name}</span>
    <span class="rh-count">{count_str}</span>
  </div>
  <div class="cards-grid">{cards_html}</div>
</div>"""

    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:{DARK_BG};--card:{CARD_BG};--text:{TXT};--muted:{MUTED};--grid:{GRID};--grn:{GRN};--ylw:{YLW}}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter','Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.5}}
/* NAV */
nav{{position:sticky;top:0;z-index:100;background:rgba(10,14,26,0.97);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--grid);display:flex;align-items:center;padding:0 24px;height:52px;gap:16px}}
.nav-brand{{font-size:15px;font-weight:700;color:var(--text);letter-spacing:-0.3px}}
.nav-brand span{{color:{GRN}}}
.nav-muted{{font-size:11px;color:var(--muted)}}
/* HERO */
.hero{{background:linear-gradient(135deg,{CARD_BG} 0%,#0d1a2e 60%,{DARK_BG} 100%);
  border-bottom:1px solid var(--grid);padding:40px 32px 32px}}
.hero-badge{{display:inline-block;background:{BLU};color:white;font-size:10px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:12px}}
.hero h1{{font-size:30px;font-weight:700;letter-spacing:-0.5px;margin-bottom:8px}}
.hero h1 span{{color:{BLU}}}
.hero-sub{{color:var(--muted);font-size:13px;max-width:640px;line-height:1.6}}
.hero-meta{{margin-top:12px;color:var(--muted);font-size:12px;display:flex;gap:24px;flex-wrap:wrap}}
.hero-meta strong{{color:var(--text)}}
/* FILTER BAR */
.filter-bar{{padding:16px 24px;border-bottom:1px solid var(--grid);display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.filter-label{{font-size:11px;color:var(--muted);margin-right:4px}}
.filter-btn{{padding:5px 14px;border-radius:6px;border:1px solid var(--grid);
  background:transparent;color:var(--muted);font-size:12px;cursor:pointer;transition:all .2s;font-family:inherit}}
.filter-btn.active,.filter-btn:hover{{background:{CARD_BG};color:var(--text);border-color:{BLU}}}
/* COMPARISON CHART */
.section{{padding:28px 24px;border-bottom:1px solid var(--grid)}}
.section-title{{font-size:16px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:10px}}
.section-title .dot{{width:4px;height:18px;background:{BLU};border-radius:2px}}
.section-sub{{font-size:12px;color:var(--muted);margin-bottom:14px}}
.chart-wrap{{background:var(--card);border:1px solid var(--grid);border-radius:12px;padding:4px;overflow:hidden}}
/* REGIONAL GROUPS */
.region-section{{padding:0 24px 8px}}
.region-header{{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:700;
  color:var(--text);padding:20px 0 12px;border-bottom:1px solid var(--grid);margin-bottom:16px}}
.region-header .rh-dot{{width:4px;height:18px;background:{BLU};border-radius:2px}}
.region-header .rh-count{{font-size:11px;font-weight:500;color:var(--muted);
  background:var(--card);border:1px solid var(--grid);border-radius:12px;padding:2px 8px;margin-left:4px}}
/* CARRIER CARDS GRID */
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin-bottom:24px}}
/* CARRIER CARD */
.lc-card{{background:var(--card);border:1px solid var(--grid);border-radius:12px;
  padding:20px;transition:border-color .25s,transform .2s;cursor:default}}
.lc-card:hover{{border-color:rgba(59,130,246,0.5);transform:translateY(-2px)}}
.lc-card-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}}
.lc-name{{font-size:16px;font-weight:700}}
.lc-ticker{{font-size:11px;color:var(--muted);margin-top:3px}}
.lc-badge{{padding:3px 10px;border-radius:4px;font-size:10px;font-weight:700;color:white;
  letter-spacing:0.5px;text-transform:uppercase}}
.lc-kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:14px}}
.lc-kpi{{text-align:center}}
.lc-kpi-label{{font-size:9px;color:var(--muted);font-weight:500;margin-bottom:3px;line-height:1.2}}
.lc-kpi-val{{font-size:14px;font-weight:700}}
.lc-btn{{display:block;text-align:center;padding:9px 0;border-radius:8px;color:white;
  font-weight:600;font-size:13px;text-decoration:none;margin-bottom:12px;transition:opacity .2s}}
.lc-btn:hover{{opacity:0.85}}
.lc-footer{{display:flex;justify-content:space-between;font-size:11px;color:var(--muted)}}
.lc-coming{{text-align:center;padding:20px 0 14px}}
/* FOOTER */
footer{{padding:24px 32px;border-top:1px solid var(--grid);color:var(--muted);font-size:11px;line-height:1.7}}
footer a{{color:{BLU};text-decoration:none}}
footer a:hover{{text-decoration:underline}}
@media(max-width:700px){{
  .lc-kpis{{grid-template-columns:repeat(3,1fr)}}
  .lc-kpi:nth-child(n+4){{display:none}}
}}
@media print{{body{{background:white;color:#111}}nav{{display:none}}}}
</style>"""

    filter_script = """
<script>
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const region = btn.dataset.region;
    document.querySelectorAll('.region-section').forEach(sec => {
      sec.style.display = (region === 'all' || sec.dataset.region === region) ? '' : 'none';
    });
  });
});
</script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Key Telco Dashboard — Executive Financial Intelligence</title>
<script src="https://cdn.plot.ly/plotly-3.0.0.min.js"></script>
{css}
</head>
<body>

<nav>
  <span class="nav-brand">Key <span>Telco</span> Dashboard</span>
  <span class="nav-muted">Executive Financial Intelligence</span>
</nav>

<div class="hero">
  <div class="hero-badge">Executive Strategy Brief</div>
  <h1>Key <span>Telco</span> Dashboard</h1>
  <div class="hero-sub">
    Executive financial dashboards for Tier-1/Tier-2 CSPs — Network Domain focus: 5G, Fiber, AI/Software, Venues.
    Built for Network Software &amp; Services strategy and account management.
  </div>
  <div class="hero-meta">
    <span><strong>Active Carriers:</strong> {len(active_data)}</span>
    <span><strong>Planned:</strong> {len(planned_data)}</span>
    <span><strong>Regions:</strong> Americas · Europe · APAC</span>
    <span><strong>Lens:</strong> Network CapEx · 5G · Broadband · AI</span>
    <span><strong>Generated:</strong> {GENERATED}</span>
  </div>
</div>

<div class="filter-bar">
  <span class="filter-label">Filter by region:</span>
  <button class="filter-btn active" data-region="all">All Carriers</button>
  <button class="filter-btn" data-region="Americas">Americas</button>
  <button class="filter-btn" data-region="Europe">Europe</button>
  <button class="filter-btn" data-region="APAC">APAC</button>
</div>

<div class="section">
  <div class="section-title"><span class="dot"></span>Active Carrier Comparison — Q4 2025</div>
  <div class="section-sub">Service Revenue (latest quarter), EBITDA Margin, Annual FCF, and 5G Coverage % side-by-side.</div>
  <div class="chart-wrap">{comp_div}</div>
</div>

{region_blocks}

<footer>
  <strong>Data Sources:</strong>
  T-Mobile IR (investor.t-mobile.com) &middot;
  Verizon IR (investor.verizon.com) &middot;
  AT&T IR (investors.att.com) &middot;
  SEC EDGAR 10-K/10-Q filings &middot;
  Yahoo Finance (stock data) &middot;
  FCC coverage filings.<br>
  <strong>Note:</strong> All financial data in USD. FX conversion at live rates for non-USD carriers.
  Q2/Q3 2025 T-Mobile quarterly figures marked * are estimates.
  Phase 2-3 carriers (Europe, APAC) coming in future releases.<br>
  <strong>Generated:</strong> {GENERATED}
</footer>

{filter_script}
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Key Telco Dashboard — Generator")
    print("=" * 50)

    # Import registry
    sys.path.insert(0, SCRIPT_DIR)
    from lib.registry import CARRIERS, active_carriers

    active = active_carriers()
    print(f"  Active carriers: {', '.join(active.keys())}")
    print(f"  Planned carriers: {sum(1 for v in CARRIERS.values() if v['status'] == 'planned')}")
    print()

    summaries = {}

    # Generate each active carrier's deep-dive page
    for cid, meta in active.items():
        print(f"  [{cid.upper()}] Generating deep-dive page...")
        try:
            module = importlib.import_module(meta["module"])
            summaries[cid] = module.get_summary()
            module.generate(CARRIERS_DIR)
            print()
        except Exception as e:
            print(f"  ERROR generating {cid}: {e}")
            import traceback
            traceback.print_exc()
            print()

    # Build landing page
    print("  Building landing page (index.html)...")
    landing_html = build_landing_page(CARRIERS, summaries)
    out_path = os.path.join(SCRIPT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(landing_html)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"  Landing page -> {out_path}  ({size_kb:.0f} KB)")
    print()

    # Summary
    print("=" * 50)
    print("Done!")
    print(f"  Landing page : index.html")
    for cid in active:
        print(f"  {cid:<12}: carriers/{cid}.html")
    print()
    print("  Open index.html in any browser — no server required.")
    print("  Use 'Print / Save PDF' on any page for static report.")


if __name__ == "__main__":
    main()
