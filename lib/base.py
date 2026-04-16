"""
lib/base.py — Shared utilities, chart helpers, HTML template
All carrier dashboards import from here.
"""
import os
from datetime import datetime

# ── Shared dark-theme palette (carriers override ACCENT) ─────────────────────
DARK_BG  = "#0a0e1a"
CARD_BG  = "#111827"
TXT      = "#f1f5f9"
MUTED    = "#94a3b8"
GRID     = "#1e2940"
GRN      = "#22c55e"
RED      = "#ef4444"
YLW      = "#f59e0b"
BLU      = "#3b82f6"
PRP      = "#8b5cf6"
TEA      = "#14b8a6"
ORG      = "#f97316"

GENERATED = datetime.now().strftime("%B %d, %Y  %H:%M")


def hex_alpha(hex_color, alpha):
    """Convert #RRGGBB + alpha float → rgba() string (Plotly 6.x compatible)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def base_layout(accent, title="", **kw):
    """Return a Plotly layout dict using the carrier's accent color."""
    d = dict(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font=dict(color=TXT, family="'Inter','Segoe UI',Arial,sans-serif", size=12),
        title=dict(text=title, font=dict(size=14, color=TXT), x=0.01, xanchor="left"),
        margin=dict(l=65, r=50, t=55, b=50),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GRID,
                    borderwidth=1, font=dict(size=11)),
        hoverlabel=dict(bgcolor="#1e293b", font_size=12,
                        font_family="'Inter',Arial,sans-serif"),
    )
    d.update(kw)
    return d


def apply_axes(fig, accent=None):
    """Apply standard dark-theme axis styling."""
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))


def fig_to_div(fig, div_id):
    try:
        import plotly.io as pio
    except ImportError:
        return f"<div class='chart-placeholder'>plotly not installed</div>"
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, div_id=div_id,
        config={"displayModeBar": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                "responsive": True}
    )


# ── HTML Components ───────────────────────────────────────────────────────────

def kpi_card(label, val, prior, unit, slug, accent):
    pct   = (val - prior) / prior * 100
    arrow = "▲" if pct > 0 else "▼"
    good_up = slug not in ("churn", "capex")
    color   = GRN if (pct > 0) == good_up else RED
    if unit == "$B":
        v_str = f"${val:.1f}B"
    elif unit == "K":
        v_str = f"{val:,.0f}K"
    elif unit == "M":
        v_str = f"{val:.1f}M"
    else:
        v_str = f"{val:.2f}%"
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{v_str}</div>
      <div class="kpi-delta" style="color:{color}">
        {arrow} {abs(pct):.1f}% vs prior year Q
      </div>
    </div>"""


def initiative_card(icon, title, subtitle, bullets, color):
    b_html = "".join(f"<li>{b}</li>" for b in bullets)
    return f"""
    <div class="init-card" style="border-left:3px solid {color}">
      <div class="init-header">
        <span class="init-icon" style="color:{color}">{icon}</span>
        <div>
          <div class="init-title">{title}</div>
          <div class="init-subtitle">{subtitle}</div>
        </div>
      </div>
      <ul class="init-bullets">{b_html}</ul>
    </div>"""


def guidance_card(label, val, note, color):
    return f"""
    <div class="guide-card" style="border-top:3px solid {color}">
      <div class="guide-label">{label}</div>
      <div class="guide-value" style="color:{color}">{val}</div>
      <div class="guide-note">{note}</div>
    </div>"""


# ── Shared CSS ────────────────────────────────────────────────────────────────

def shared_css(accent):
    a2 = hex_alpha(accent, 0.15)
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:{DARK_BG};--card:{CARD_BG};--accent:{accent};
  --text:{TXT};--muted:{MUTED};--grid:{GRID};
  --grn:{GRN};--red:{RED};--ylw:{YLW};--blu:{BLU};--tea:{TEA};
}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter','Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;font-size:14px}}
nav{{position:sticky;top:0;z-index:100;background:rgba(10,14,26,0.95);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--grid);display:flex;align-items:center;
  padding:0 24px;height:52px;gap:4px;overflow-x:auto}}
.nav-brand{{font-weight:700;font-size:15px;color:var(--accent);margin-right:16px;white-space:nowrap;letter-spacing:-0.3px}}
.nav-home{{color:var(--muted);text-decoration:none;font-size:11px;padding:4px 8px;border-radius:5px;white-space:nowrap}}
.nav-home:hover{{color:var(--text);background:var(--grid)}}
nav a{{color:var(--muted);text-decoration:none;font-size:12px;font-weight:500;
  padding:6px 12px;border-radius:6px;white-space:nowrap;transition:all .2s}}
nav a:hover{{color:var(--text);background:var(--grid)}}
.nav-print{{margin-left:auto;background:var(--accent);color:white;border:none;
  padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;
  white-space:nowrap;transition:opacity .2s}}
.nav-print:hover{{opacity:0.85}}
.hero{{background:linear-gradient(135deg,{CARD_BG} 0%,#1a0a14 60%,{DARK_BG} 100%);
  border-bottom:1px solid var(--grid);padding:36px 32px 28px}}
.hero-badge{{display:inline-block;background:var(--accent);color:white;font-size:10px;
  font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:3px 10px;
  border-radius:4px;margin-bottom:12px}}
.hero h1{{font-size:28px;font-weight:700;letter-spacing:-0.5px}}
.hero h1 span{{color:var(--accent)}}
.hero-meta{{margin-top:8px;color:var(--muted);font-size:12px;display:flex;gap:24px;flex-wrap:wrap}}
.hero-meta strong{{color:var(--text)}}
.section{{padding:32px 24px;border-bottom:1px solid var(--grid)}}
.section-title{{font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px;
  display:flex;align-items:center;gap:10px}}
.section-title .dot{{width:4px;height:20px;background:var(--accent);border-radius:2px}}
.section-sub{{color:var(--muted);font-size:12px;margin-bottom:20px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:12px;margin-bottom:8px}}
.kpi-card{{background:var(--card);border:1px solid var(--grid);border-radius:10px;
  padding:16px;transition:border-color .2s}}
.kpi-card:hover{{border-color:var(--accent)}}
.kpi-label{{font-size:11px;color:var(--muted);font-weight:500;margin-bottom:6px}}
.kpi-value{{font-size:22px;font-weight:700;letter-spacing:-0.5px}}
.kpi-delta{{font-size:11px;font-weight:600;margin-top:4px}}
.chart-wrap{{background:var(--card);border:1px solid var(--grid);border-radius:12px;
  padding:4px;overflow:hidden;margin-bottom:16px}}
.chart-wrap .chart-note{{padding:6px 16px 10px;font-size:10px;color:var(--muted);font-style:italic}}
.chart-grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:860px){{.chart-grid-2{{grid-template-columns:1fr}}}}
.chart-placeholder{{background:var(--card);border:1px dashed var(--grid);border-radius:12px;
  padding:32px;color:var(--muted);text-align:center;font-size:13px}}
.init-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.init-card{{background:var(--card);border-radius:10px;padding:18px;border:1px solid var(--grid);transition:border-color .2s}}
.init-card:hover{{border-color:var(--accent)}}
.init-header{{display:flex;gap:12px;align-items:flex-start;margin-bottom:12px}}
.init-icon{{font-size:24px;line-height:1;flex-shrink:0}}
.init-title{{font-size:14px;font-weight:700}}
.init-subtitle{{font-size:11px;color:var(--muted);margin-top:2px}}
.init-bullets{{font-size:12px;color:var(--muted);padding-left:18px}}
.init-bullets li{{margin-bottom:4px}}
.guide-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
.guide-card{{background:var(--card);border-radius:10px;padding:18px;border:1px solid var(--grid)}}
.guide-label{{font-size:11px;color:var(--muted);font-weight:500;margin-bottom:8px}}
.guide-value{{font-size:20px;font-weight:700;letter-spacing:-0.5px}}
.guide-note{{font-size:11px;color:var(--muted);margin-top:6px}}
.est-note{{background:var(--card);border:1px solid rgba(245,158,11,0.25);border-radius:8px;
  padding:10px 16px;font-size:11px;color:var(--muted);margin-bottom:16px}}
.est-note strong{{color:{YLW}}}
footer{{padding:24px 32px;color:var(--muted);font-size:11px;border-top:1px solid var(--grid);line-height:1.7}}
footer a{{color:var(--accent);text-decoration:none}}
footer a:hover{{text-decoration:underline}}
@media print{{
  body{{background:white;color:#111}}
  nav,.nav-print{{display:none!important}}
  .hero{{background:#f8f8f8;border-bottom:2px solid var(--accent)}}
  .kpi-card,.init-card,.guide-card,.chart-wrap{{background:white;border-color:#ddd;break-inside:avoid}}
  .section{{break-inside:avoid}}
}}
</style>"""


def page_shell(carrier_meta, nav_links, body_html, sources_html, extra_head=""):
    """
    Wrap carrier content in the standard page shell.
    carrier_meta: dict with keys name, ticker, accent, flag, region, quarter, generated
    nav_links: list of (anchor, label) tuples
    """
    accent  = carrier_meta["accent"]
    name    = carrier_meta["name"]
    ticker  = carrier_meta.get("ticker", "")
    flag    = carrier_meta.get("flag", "")
    quarter = carrier_meta.get("latest_quarter", "")
    stock_p = carrier_meta.get("stock_period", "3-Year")
    gen     = carrier_meta.get("generated", GENERATED)

    nav_items = "".join(f'<a href="#{a}">{l}</a>' for a, l in nav_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{name} — Executive Financial Dashboard</title>
<script src="https://cdn.plot.ly/plotly-3.0.0.min.js"></script>
{shared_css(accent)}
{extra_head}
</head>
<body>
<nav>
  <span class="nav-brand">{flag} {name}</span>
  <a class="nav-home" href="../index.html">⟵ All Carriers</a>
  {nav_items}
  <button class="nav-print" onclick="window.print()">⬇ Print / Save PDF</button>
</nav>
<div class="hero">
  <div class="hero-badge">Executive Strategy Brief</div>
  <h1>{name} <span>({ticker})</span> — Financial Dashboard</h1>
  <div class="hero-meta">
    <span><strong>Latest Quarter:</strong> {quarter}</span>
    <span><strong>Stock Period:</strong> {stock_p}</span>
    <span><strong>Lens:</strong> Network Domain · 5G · Broadband · AI/Software</span>
    <span><strong>Generated:</strong> {gen}</span>
    <span><strong>Sources:</strong> {name} IR · SEC EDGAR · Yahoo Finance</span>
  </div>
</div>
{body_html}
<footer>
  {sources_html}
  <strong>Note:</strong> Quarters marked * are estimates derived from annual totals minus known quarters.
  All financial data in USD unless stated. Dashboard generated: {gen}
</footer>
</body>
</html>"""
