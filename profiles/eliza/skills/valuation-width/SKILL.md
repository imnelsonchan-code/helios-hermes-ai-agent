---
name: valuation-width
description: >-
  Eliza weekly valuation-width revise: ## Session summary → ## Market insight →
  News/Market → Lenses → Track A/B. Selected tables cite Spot (as_of), FV Range,
  Upside % from pack JSON plus valuation_score and width_verdict. Candidate
  ≥+15% + quality; Omissions; e5_overlap WARN. Never rewrite runner arithmetic;
  never invent FV; never claim full DCF; never tm_score; never desk Risk-on/off.
---

# Valuation width — Weekly width revise

**Owner:** Eliza · **Train:** formal (Draft → Zoe → Eliza revise)  
**Load with:** `investment/valuation-screener`, `investment/finviz-screener`, `investment/yahoo-finance-data-fetch`, `investment/financial-health` (quality overlay)  
**Not:** full 12-method DCF · rewriting runner arithmetic · any `tm_score` · desk Risk-on/off final call · host `render_weekly_value` swap

Label "Not investment advice". Source grading: `📊 Data` / `📊 Institutional` (SEC / IR).

---

## When to use

- Weekly value pack narrative + **width revise** after Zoe challenge  
- Saturday / Sunday width artifacts audit + revise mapping  
- **Not** daily value-session; **not** A-08 Monday follow-up; **not** single-name full DCF

---

## Free data only

Yahoo Finance · Finviz · SEC EDGAR · public IR · FRED · live width runner output (basename only)  
**Banned:** FactSet / Bloomberg / LSEG · invented percentiles · invented `valuation_score` · T&M indicators in quality overlay

---

## Track A / Track B

| Name | Meaning |
|------|---------|
| **Track A** | Large + Mid Cap **report chapter** (≥$5B) |
| **Track B** | Small Cap **report chapter** (<$5B; intended floor $300M–<$5B when cap known) |

Width scan runner must cover **both** tracks (default / omit `--track`). ❌ `--track A` / `--track B` partial runs — revise must not invent "0 Finviz hits" when JSON has `screened: false` / `partial_run`.

Missing market cap → fail closed: omit from selected + **Omissions**.  
≠ Option A/B (cache / DCF v3).

---

## Score mapping (revise only — no new arithmetic)

Live runner may still emit `composite_score`, `adjusted_composite`, Markdown `Score` / `Adj`. Eliza revise **maps only**:

| From | To |
|------|----|
| `composite_score` (0–1) | `valuation_composite` (keep 0–1) |
| same | `valuation_score = round(composite_score × 100)` |
| `adjusted_composite` | `quality_adjusted_score`: ≤1.5 → treat as 0–1 ×100; >1.5 → already 0–100 |
| — | set `quality_adjusted` boolean |
| columns `Score` / `Adj` | rename → **Valuation Score** / **Quality-Adjusted Score** |

- **Never** write quality-adjusted into `valuation_score`  
- **Never** rewrite runner ranking arithmetic  
- Five-factor weights truth: **33 / 28 / 19 / 15 / 5** (`pe` / `ev_ebitda` / `pb` / `fcf_yield` / `rev_growth`)

### Candidate / Omissions

- **Candidate** floor: FV upside **≥+15%** + quality gates OK (no 🚨, no EQ-F, no F-Score ≤3 trap)  
- **+30%** → optional `strong_candidate: true` only — **not** a second admission floor  
- Unscorable / no numeric five-factor score → **Omissions** (ticker + reason); **never** publish selected `N/A`  
- `e5_overlap`: same ticker in T&M pack → **WARN only**; do not change ranks / scores

---

## Output shape

### Header

- Week id (`YYYY-WW`) · `as_of` (required) · optional `generated_at` / `data_delay`  
- `fv_engine` stamp (e.g. `pe_band_screen`) — do not claim full DCF coverage

### 1. `## Session summary` (REQUIRED)

Place **immediately after Header**. Zoe **REJECT** if missing.

```markdown
## Session summary
- … 5–8 bullets (owner voice; not a table dump)
- Valuation stance (Candidate/Watch/Avoid tilt)
- Material Candidates / Omissions note
- **Alice pull:** Market insight — 1–2 sentence pointer (do not paste full text)
```

### 2. `## Market insight` (REQUIRED)

Weekly depth: width tilt, cheap-rich vs tape, Track A/B tension. Alice overall **cite first** this section.

```markdown
## Market insight
- … 3–8 bullets: what the market is saying this week (valuation lens)
- ❌ do not write desk Risk-on/off final call; ❌ do not claim desk-wide Macro view (→ Alice · Zoe Z-MI-02)
```

Zoe: **missing this section → REJECT (Z-MI-01)**.

### 3. `## News/Market check` (REQUIRED · Eliza-topic)

```markdown
## News/Market check (Eliza-topic)
- 📰 News: 2–3 sentences (URL≤12) · earnings/multiples/sector valuation · outlet/URL/as-of · or `News: miss`
- 📊 Market tape: value vs growth / cheap-rich dispersion one sentence
```

### 4. `## Lenses` (REQUIRED)

```markdown
## Lenses
- Macro: … · Micro: … · Market: … · Dominant: macro-led | micro-led | market-led | mixed
```

Weekly: three-lens stub + Dominant **required complete**.

### 5. Body skeleton

Zoe challenge responses → methodology → **Track A** → **Track B** → WoW / conclusion.  
Each selected row: numeric `valuation_score` + breakdown keys when published.  
JSON must-have: `valuation_score`, `valuation_score_breakdown`, `valuation_composite`, `quality_adjusted`, `quality_adjusted_score`, `width_verdict`, `e5_overlap`, `as_of`, `fv_range`.

Each selected Track A / Track B table **must** use this exact header (`FV Range` text is locked so host `width_publish_guard` can parse it):

```markdown
| Ticker | Spot (as_of) | FV Range | Upside % | Valuation Score | Quality-Adjusted Score | `valuation_score` | `width_verdict` | Note |
```

- **Spot (as_of)** / **FV Range** / **Upside %**: copy from scan JSON / revise overlay (`fv_range`, spot/price, upside vs chosen band). Never invent. Never rewrite runner percentile arithmetic. `pe_band` formula is not in this repo — cite pack fields only.
- FV Range header text must be exactly `FV Range`.
- If JSON has a numeric `$` `fv_range` or `+%` verdict, the FV Range cell must **not** be a lone `?`.
- Missing FV → do not publish a fake number; cell `attempted + miss` or move unscorable names to **Omissions** per existing rules.
- **Upside %** is display of pack upside vs the chosen band. It does **not** replace `valuation_score` (five-factor 0–100). Highest score ≠ strongest `width_verdict`.
- Stamp `fv_engine` (e.g. `pe_band_screen`). Never describe the weekly pack as full DCF.

### 6. Sources

```markdown
## Sources
- 📊 Data: runner / Finviz / Yahoo · as_of …
- 📰 News: <outlet · URL · as-of> or News: miss
- Omissions: <ticker>: <reason>
```

---

## Save / deliver

- User-facing: **`inbox/valuation-width/YYYY-WW-valuation-width-revised.md`** (3-layer)  
- Draft `*-report.md` stays workspace + shared  
- If revise gates FV / verdict vs scan JSON → write same overlay into `*_revise` / `*-revised.json`  
- **Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`  
- Alice overall cites: `## Market insight` (first) + `## Session summary`

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`  
- **Never** load `scoring-engine-v4.*`  
- **Never** blend T&M weights / indicators into `valuation_composite` / `valuation_score` / quality overlay  
- **Never** leave bare `Score` / `Adj` columns on revised tables  
- ❌ Desk Risk-on/off / desk-wide Macro view final call (Alice only)  
- Invented scores / silent pass on missing quality / missing Market insight → **Zoe REJECT** territory

---

## Banned

- Rewriting runner percentile / composite arithmetic  
- Dual-running conflicting profile-local `trading/*` weights  
- FactSet/Bloomberg/LSEG as sole source without public URL  
- Treating weekly width as full DCF coverage  
- Folding eval overlays (Paper Book V / IC / veto scripts) into `valuation_score`  
- Desk Risk-on/off final-call sentence
