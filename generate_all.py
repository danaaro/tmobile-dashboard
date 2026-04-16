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

import sys, os, importlib
from datetime import datetime

# Force UTF-8 so emoji/Unicode in print() works on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CARRIERS_DIR = os.path.join(SCRIPT_DIR, "carriers")
GENERATED    = datetime.now().strftime("%B %d, %Y  %H:%M")

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

        kpi_html = f"""
        <div class="lc-kpis">
          <div class="lc-kpi"><div class="lc-kpi-label">Svc Rev (Q)</div><div class="lc-kpi-val">${svc_rev:.1f}B</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">EBITDA Margin</div><div class="lc-kpi-val">{margin:.1f}%</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">FCF (Annual)</div><div class="lc-kpi-val">${fcf:.1f}B</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">Subscribers</div><div class="lc-kpi-val">{subs:.0f}M</div></div>
          <div class="lc-kpi"><div class="lc-kpi-label">5G Coverage</div><div class="lc-kpi-val">{cov5g}%</div></div>
        </div>
        <a href="{out_file}" class="lc-btn" style="background:{accent}">View Dashboard &rarr;</a>"""
        status_badge = f'<span class="lc-badge" style="background:{GRN}">Live</span>'
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
        status_badge = f'<span class="lc-badge" style="background:{pcol}">Phase {phase}</span>'
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
    svc_rev = [d['summary'].get('svc_rev', 0) for d in active_carriers_data]
    margins = [d['summary'].get('ebitda_margin', 0) for d in active_carriers_data]
    fcf     = [d['summary'].get('fcf_annual', 0) for d in active_carriers_data]
    cov5g   = [d['summary'].get('coverage_5g', 0) for d in active_carriers_data]

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=4,
                        subplot_titles=["Service Rev (Q, $B)", "EBITDA Margin %",
                                        "FCF Annual ($B)", "5G Coverage %"])

    for i, (nm, clr, v) in enumerate(zip(names, accents, svc_rev)):
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr, showlegend=(i == 0),
                             text=[f"${v:.1f}B"], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>Svc Rev: ${v:.1f}B<extra></extra>"),
                      row=1, col=1)
    for i, (nm, clr, v) in enumerate(zip(names, accents, margins)):
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr, showlegend=False,
                             text=[f"{v:.1f}%"], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>EBITDA Margin: {v:.1f}%<extra></extra>"),
                      row=1, col=2)
    for i, (nm, clr, v) in enumerate(zip(names, accents, fcf)):
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr, showlegend=False,
                             text=[f"${v:.1f}B"], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>FCF: ${v:.1f}B<extra></extra>"),
                      row=1, col=3)
    for i, (nm, clr, v) in enumerate(zip(names, accents, cov5g)):
        fig.add_trace(go.Bar(x=[nm], y=[v], name=nm, marker_color=clr, showlegend=False,
                             text=[f"{v}%"], textposition="outside",
                             textfont=dict(color=TXT, size=10),
                             hovertemplate=f"<b>{nm}</b><br>5G Coverage: {v}%<extra></extra>"),
                      row=1, col=4)

    fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font=dict(color=TXT, family="'Inter','Segoe UI',Arial,sans-serif", size=11),
        margin=dict(l=30, r=30, t=40, b=30), height=280,
        showlegend=False,
        hoverlabel=dict(bgcolor="#1e293b", font_size=11),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
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

    # Build carrier cards
    all_cards = ""
    for entry in active_data + planned_data:
        all_cards += carrier_card(entry["meta"], entry["summary"])

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
/* CARRIER CARDS GRID */
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;padding:24px}}
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
    document.querySelectorAll('.lc-card').forEach(card => {
      card.style.display = (region === 'all' || card.dataset.region === region) ? '' : 'none';
    });
  });
});
</script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Carrier Intelligence Hub — Executive Dashboard</title>
<script src="https://cdn.plot.ly/plotly-3.0.0.min.js"></script>
{css}
</head>
<body>

<nav>
  <span class="nav-brand">Carrier <span>Intelligence</span> Hub</span>
  <span class="nav-muted">Multi-Carrier Executive Financial Dashboard</span>
</nav>

<div class="hero">
  <div class="hero-badge">Executive Strategy Brief</div>
  <h1>Global Carrier <span>Intelligence</span> Hub</h1>
  <div class="hero-sub">
    Executive financial dashboards for Tier-1/Tier-2 CSPs — Network Domain focus: 5G, Fiber, AI/Software, Venues.
    Built for Network Software & Services strategy and account management.
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

<div class="cards-grid">{all_cards}</div>

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
    print("Multi-Carrier Executive Dashboard Generator")
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
