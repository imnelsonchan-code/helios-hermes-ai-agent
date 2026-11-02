---
name: value-session
description: >-
  Eliza daily value-session: ## Session summary → ## Market insight → News/Market
  → Lenses → movers vs Sunday lock. Columns: Today spot, Sunday lock FV
  (verbatim fv_range), Display upside % vs today. Cite Sunday valuation_score;
  upside does not re-rank or change width_verdict; no invented FV. Portal
  inbox/value-session/YYYY-MM-DD-*-revised.md. Never emits tm_score; never desk
  Risk-on/off.
---

# Value session — Daily value session

**Owner:** Eliza · **Train:** formal (Draft → Zoe → Eliza revise) · Desk-pack #4  
**Load with:** `investment/yahoo-finance-data-fetch`, Sunday lock revised pack (prefer JSON), Alice macro brief when present  
**Not:** weekly width re-score · value-100 re-rank · inventing `valuation_score` · any `tm_score` · desk Risk-on/off final call · Alice-arm-only embed

Label "Not investment advice". Source grading: `📊 Data` / `📰 News` / `📊 Institutional` (public IR / SEC).

---

## When to use

- Daily T-CLOSE **value-session**: data snapshot + value movers vs **Sunday lock**  
- Own portal session — **not** Alice market-close arm-only  
- **Not** Sunday width runner; **not** A-08 re-score; **not** post-print (use `earnings-analysis`)

---

## Free data only

Yahoo Finance · Finviz · public IR · FRED · published Sunday lock revised pack  
**Banned:** FactSet / Bloomberg terminal / LSEG · invented movers · invented Sunday scores · holdings / entry prices

---

## Cite Sunday lock only

- Movers / Candidates notes **must cite** published Sunday lock `valuation_score` (revised pack / JSON)  
- Movers table **MUST** include numeric Sunday `valuation_score` (verbatim) or skip + Sources `attempted + miss`. Empty "cite Sunday lock" prose without a number is not enough.
- **Sunday lock FV:** verbatim cite from published Sunday revised JSON field `fv_range` (or the pack's already-published FV string). Missing → cell `attempted + miss`. **Never** compute a new FV; **never** invent FV.
- **Today spot / %:** Yahoo or Finviz only. Missing → `attempted + miss`.
- **Display upside %** = cited FV / today spot − 1. If `fv_range` is a band, label the cited point in the cell (e.g. `reasonable $50.00`). If either input is miss, upside cell is `attempted + miss`. Display only — do not re-score.
- Display upside does **NOT** change `valuation_score`, `width_verdict`, five-factor weights, or weekly ranks. A tape cross of +15% or −10% is Note only: `tape vs Sunday lock`.
- **Never** re-rank or reshuffle weekly value-100  
- Missing Sunday numeric score → skip that name for score citation; do not invent or carry forward `N/A` selected row  
- **Never** change `width_verdict`; **never** emit `tm_score`

---

## Output shape (markdown)

### Header

- Session date · TZ · `as_of` (required)  
- Optional provenance: `generated_at`, `data_delay` (when pack / fetch provides)  
- Hard line: this session **does not change** `valuation_score`, five-factor weights, or weekly width ranks

### 1. `## Session summary` (REQUIRED)

Place **immediately after Header**. Zoe **REJECT** if missing.

```markdown
## Session summary
- … 5–8 bullets (owner voice; not a table dump)
- Valuation stance (e.g. cheap / fair / rich vs Sunday lock; Candidate/Watch/Avoid tilt)
- Material movers / Candidates note (cite Sunday `valuation_score` AND Sunday lock FV; show display upside vs today — no invented FV)
- **Alice pull:** THIS file `## Market insight` — 1–2 sentence pointer (do not paste full text). Forbidden: `No formal market-insight brief today` when the section exists. Alice macro brief miss → Lenses Macro (`No brief.` / `miss`), NOT Alice pull.
```

### 2. `## Market insight` (REQUIRED)

Valuation domain: cheap-rich vs tape, Candidate tilt, earnings/multiples narrative. Alice overall **cite first** this section.

```markdown
## Market insight
- … 3–6 bullets: what the market is saying (valuation lens)
- ❌ do not write desk Risk-on/off final call; ❌ do not claim desk-wide Macro view (→ Alice · Zoe Z-MI-02)
```

Zoe: **missing this section → REJECT (Z-MI-01)**.

### 3. `## News/Market check` (REQUIRED · Eliza-topic)

Allowlist: earnings / multiples / sector valuation tape / cheap vs rich dispersion.  
Denylist: T&M BUY list primary narrative (Renee); full rates ladder (christina); commodity inventory / COT (emily).

```markdown
## News/Market check (Eliza-topic)
- 📰 News: ≥1 sentence (Daily URL≤5) · outlet/URL/as-of · or `News: miss`
- 📊 Market tape: value vs growth / cheap-rich one sentence
```

### 4. `## Lenses` (REQUIRED)

```markdown
## Lenses
- Macro: cite Alice brief if present · valuation-domain overlay one sentence (do not set desk Risk-on/off). Alice macro brief miss → `No brief.` / `miss` **here** (Lenses Macro), NOT in Alice pull
- Micro: Sunday lock / movers structure
- Market: tape / dispersion one sentence · Conf effect
- Dominant: macro-led | micro-led | market-led | mixed
```

### 5. Data snapshot

- Coverage / data quality notes; misses → `attempted + miss`  
- Tape context may cite Alice brief — **do not** replace this file's Market insight / Lenses

### 6. Value movers vs Sunday lock

| Ticker | Today spot / % | Sunday lock FV | Display upside % | Sunday `valuation_score` | `width_verdict` | Note |
|--------|----------------|----------------|------------------|--------------------------|-----------------|------|
| … | … | … | … | … | … | … |

### 7. Sources

```markdown
## Sources
- 📊 Data: <outlet> · <date> · <URL or pack id basename>
- 📰 News: <outlet · URL · as-of> or News: miss
- Sunday lock: <revised pack basename> · as_of …
- Misses: <item>: attempted + miss
```

---

## Save / deliver

- Draft: workspace + shared OK  
- User-facing: **`inbox/value-session/YYYY-MM-DD-*-revised.md`** (3-layer; do not write to shared only)  
- **Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`  
- Reviser = **Eliza** (not Alice)  
- Alice overall cites: `## Market insight` (first) + `## Session summary`

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`
- **Never** blend with / overwrite `valuation_score` or five-factor weights
- **Never** re-rank value-100 or change weekly width verdict from this session alone
- ❌ Desk Risk-on/off / desk-wide Macro view final call (Alice only)
- Invented Sunday scores / invented FV / missing Market insight → **Zoe REJECT** territory

---

## Banned

- Excel / Office JS automation  
- Auto-updating Sunday pack or width runner  
- Alice-arm-only embed without own `value-session` portal file  
- FactSet/Bloomberg/LSEG language or paywalled scrape without public URL  
- Headlines-only with empty Session summary / Market insight  
- Desk Risk-on/off final-call sentence
