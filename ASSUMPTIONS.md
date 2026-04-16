# Dashboard Project — Assumptions & Design Decisions

> **Last updated:** April 2026  
> **Project:** Multi-Carrier Executive Financial Dashboard  
> **Owner:** danaaro  
> **Purpose:** Executive management & strategy analysis for a Network Software & Services company serving Global Tier-1/Tier-2 CSPs (fixed + mobile). Covers network modernization, automation, and AI-driven transformation.

---

## 1. Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Dashboard format | **Modular registry pattern** | Landing page (all carriers) + individual deep-dive pages per carrier |
| Code structure | `lib/base.py` (shared) + `lib/carriers/<name>.py` (per carrier) | Adding a carrier = one new file, no base code changes |
| Output | Static self-contained HTML files | No server required; shareable via email / SharePoint / GitHub Pages |
| Master runner | `generate_all.py` | Regenerates all carrier pages + landing page in one command |
| Hosting | GitHub Pages (`danaaro.github.io/tmobile-dashboard`) | Free, public, no infrastructure |

---

## 2. Landing Page

- Shows all available carriers as cards
- Each card displays **5 KPIs**: Service Revenue (latest quarter), EBITDA Margin, FCF, Total Subscribers, 5G Coverage %
- Includes a **comparison chart** showing all carriers' key financials side-by-side
- Cards are filterable by region: Americas · Europe · APAC
- Clicking a card opens the carrier's deep-dive page

---

## 3. Carriers — Build Phases

### Phase 1 (US — current + next)
| Carrier | Ticker | Currency | Status |
|---|---|---|---|
| T-Mobile US | TMUS (NASDAQ) | USD | ✅ Done |
| Verizon | VZ (NYSE) | USD | 🔜 Next |
| AT&T | T (NYSE) | USD | 🔜 Next |

### Phase 2 (Europe)
| Carrier | Ticker | Currency (native) | Status |
|---|---|---|---|
| VMO2 (Virgin Media O2, UK) | Private JV — no listing | GBP | 🔜 Planned |
| ODIDO (Netherlands) | ODID (Euronext Amsterdam) | EUR | 🔜 Planned |
| VF Germany (Vodafone Germany) | Subsidiary of VOD (LSE/NASDAQ) | EUR | 🔜 Planned |

### Phase 3 (APAC)
| Carrier | Ticker | Currency (native) | Status |
|---|---|---|---|
| Globe Telecom (Philippines) | GLO (PSE) | PHP | 🔜 Planned |

---

## 4. Currency

| Decision | Choice |
|---|---|
| Display currency | **USD (all carriers converted)** |
| Conversion method | Live FX rates via `yfinance` (e.g., `GBPUSD=X`, `EURUSD=X`, `PHPUSD=X`) at time of generation |
| FX rate display | Dashboard footer shows conversion rates used and generation date |
| Historical data | Converted at approximate period-average FX rate (noted in dashboard) |

---

## 5. Stock Analysis

| Carrier | Stock treatment |
|---|---|
| T-Mobile (TMUS) | ✅ Direct — TMUS on NASDAQ |
| Verizon (VZ) | ✅ Direct — VZ on NYSE |
| AT&T (T) | ✅ Direct — T on NYSE |
| ODIDO | ✅ Direct — ODID on Euronext Amsterdam |
| VF Germany | ⚠ Use parent **Vodafone Group (VOD)** on LSE/NASDAQ; clearly labeled as parent co. |
| VMO2 | ⚠ Private JV (Liberty Global + Telefónica). Stock section replaced with parent company context card (LBTYA, TEF). |
| Globe Telecom | ✅ GLO on Philippine Stock Exchange — note: lower liquidity / data availability |
- 3-year lookback period for all carriers (from generation date)
- Peer benchmark for each carrier uses regional telecom ETF + direct sector peers

---

## 6. Reporting Cadence & Data

| Decision | Choice |
|---|---|
| Primary data source | Carrier IR websites + SEC EDGAR (US) / equivalents (EU/APAC) |
| Latest period focus | Most recent fully reported quarter vs. 1 year prior |
| European carriers | Semi-annual reporting is acceptable; noted in dashboard |
| Estimated quarters | Derived from annual totals minus known quarters; labeled with `*` |
| Data hardcoded | Yes — from verified IR sources; updated manually per earnings release |
| Network domain focus | Primary lens: Network CapEx, 5G, Fiber, AI/Software, Venues |

---

## 7. Metrics Standardization

Because carriers use different terminology, the following standardization applies:

| Standard Label | T-Mobile equiv. | Verizon equiv. | AT&T equiv. | EU/Other |
|---|---|---|---|---|
| Service Revenue | Service Revenue | Total Operating Revenue | Service Revenue | Service Revenue / Turnover |
| EBITDA | Core Adjusted EBITDA | Adjusted EBITDA | EBITDA | OIBDA / Adjusted EBITDA |
| Free Cash Flow | Adjusted Free Cash Flow | Free Cash Flow | Free Cash Flow | FCF (post-lease or pre-lease noted) |
| Subscribers | Postpaid Phone customers | Retail Postpaid | Postpaid subscribers | Mobile subscribers |
| Broadband | High Speed Internet / 5G Broadband | Home Internet | AT&T Internet / Fiber | FWA / Broadband |

- All deviations from standard labels are documented in each carrier's module
- EBITDA vs OIBDA differences noted where applicable

---

## 8. 5G & Coverage

| Decision | Choice |
|---|---|
| Coverage metric | % population coverage where available; geographic coverage as secondary |
| Technology tiers | Low-band / Mid-band / mmWave / SA Core — carrier-specific labeling mapped to standard |
| Fiber | Homes passed (where reported) or broadband customers as proxy |
| Venues | Small cell / venue deployment data where publicly disclosed |

---

## 9. Design & UX

| Decision | Choice |
|---|---|
| Theme | Dark executive (carrier-specific accent color per brand) |
| Interactivity | Plotly — zoom, pan, hover, download PNG |
| Download | `window.print()` → PDF from browser |
| Self-contained | Single `.html` file per carrier (Plotly via CDN — requires internet) |
| Navigation | Sticky nav with section anchors; landing page links to individual pages |

---

## 10. Carrier Brand Colors

| Carrier | Primary Accent |
|---|---|
| T-Mobile | `#E20074` (Magenta) |
| Verizon | `#CD040B` (Red) |
| AT&T | `#00A8E0` (Blue) |
| VMO2 | `#D0021B` (Virgin Red) |
| ODIDO | `#FF6B00` (Orange) |
| VF Germany | `#E60000` (Vodafone Red) |
| Globe Telecom | `#0066CC` (Blue) |

---

## 11. Resolved Decisions

| Question | Decision |
|---|---|
| VMO2 data source | Liberty Global IR segment data (acceptable) |
| VF Germany data source | Vodafone Group segment data (Germany segment) |
| Landing page comparison metrics | Service Revenue · EBITDA Margin · CapEx/Revenue % · 5G Population Coverage % |
| Migration approach | Migrate T-Mobile into new modular structure first, then add Verizon + AT&T (Phase 1) |
| FX rates | Live spot rate via `yfinance` at generation time; period-average noted in footer |

## 12. Remaining TBD

- [ ] Globe GLO: confirm PHP→USD conversion method (quarterly average vs. spot)
- [ ] VMO2 standalone reports availability (Liberty Global IR as fallback)
