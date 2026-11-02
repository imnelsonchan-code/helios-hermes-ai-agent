---
name: tm-session-report
description: >-
  Renee daily + weekly T&M trunk: Header → ## Session summary → ## Market insight
  → News/Market check → Lenses → optional funnel → ranking (live pack) → key notes; portal revise;
  reviser=renee; no score rewrite; daily Option G OK / weekly NO Option G;
  candidate/watchlist language; Not investment advice. Never blends valuation_score; never desk Risk-on/off.
---

# T&M session report — daily/weekly T&M trunk

**Owner:** Renee · **Process:** **P-TM** · **Train:** formal (Draft → Zoe → Renee revise)  
**Load with:** `skills/tm-e5-firewall` (always), `skills/tm-signal-funnel` (when daily-eval exists), Alice macro brief when present, shared `trading/technical-analysis`, `trading/market-regime`, `trading/macro-filter`  
**Not:** score rewrite · invent funnel counts · weekly Option G suppress · blend `valuation_score` · desk Risk-on/off final call · Alice-arm-only embed

Mark "Not investment advice". Research language: candidates / watchlist — **not** broker tickets.

---

## When to use

- **Daily T&M** narrative + revise → `inbox/daily-trend-momentum/YYYY-MM-DD-*-report-revised.md`
- **Weekly T&M** narrative + revise → `inbox/weekly-trend-momentum/YYYY-WW-*-trend-momentum-report-revised.md`
- Market-close T&M session (desk-pack #3) — own portal file, **not** Alice-arm-only
- **Not** value width / A-08 · **not** Book V / `value_hit_rate`

---

## Free data / pack truth only

Live Stage-2 **tm** pack · Yahoo / Finviz public tape · scoring-eval JSON when present  
**Optional cite-only (no score change):** FINRA [Equity Short Interest](https://www.finra.org/finra-data/browse-catalog/equity-short-interest/data) · SEC [Fails-to-Deliver](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data) — selected tickers / Notes only; as-of required; missing → `miss`. ChartExchange secondary navigation at most.  
**Banned:** FactSet / Bloomberg / LSEG · invented `tm_score` · invented demotions · holdings / fills · using short/FTD to change brackets

---

## Cadence rules

| Cadence | Option G | Insight depth | Ranking |
|---------|----------|---------------|---------|
| **Daily** | OK — SPY ADX &lt;25 may suppress effective BUY while showing theoretical scores | Market insight compact; News≥1; URL≤5 | Live pack brackets only |
| **Weekly** | **NO Option G** — do **not** suppress weekly BUY counts for ADX &lt;25 | Deeper Market insight; News 2–3; URL≤12 | Keep generator tables; enrich notes with pack evidence only |

---

## Output shape (markdown)

### Header

- Session date / week id · TZ · regime / SPY ADX / VIX  
- Daily: Option G banner when applicable  
- Weekly: **no** Option G banner  
- Optional **dual-score notes** = raw Score ≥60 vs DMI-gated net BUY when both matter — **≠** blending with Eliza `valuation_score` (E5)  
- Hard line: **no score rewrite** — `tm_score` / brackets from live pack only  
- Not investment advice

### 1. `## Session summary` (REQUIRED)

Place **immediately after Header**. Zoe **REJECT** if missing.

```markdown
## Session summary
- … 5–8 bullets (owner voice; not a table dump)
- T&M regime tag (trending / ranging / choppy / volatile + SPY ADX / Option G note when daily)
- Top movers: 2–5 tickers with direction + `tm_score` (pack truth only; no invented prices)
- **Alice pull:** THIS file `## Market insight` — 1–2 line pointer (do not paste full section). Forbidden: `No formal market-insight brief today` when the section exists. Alice macro brief miss → Lenses Macro (`No brief.` / `miss`), NOT Alice pull.
```

### 2. `## Market insight` (REQUIRED)

T&M / price-action domain: regime mechanism, breadth/leadership, key technical narrative. Alice overall **prioritizes citing** this section (compact).

```markdown
## Market insight
- … 3–6 bullets: what the market is saying (T&M lens)
- One line on breadth / leadership / regime mechanism
- ❌ Do not write desk Risk-on/off final call; ❌ do not claim desk-wide Macro view (→ Alice · Zoe Z-MI-02)
```

Zoe: **missing this section → REJECT (Z-MI-01)**.

### 3. `## News/Market check` (REQUIRED · Renee-topic)

Allowlist: indices / sectors / vol / breadth / leadership tape.  
Denylist: valuation / DCF / F-Score main narrative (Eliza); commodity inventory / COT long copy (emily); full rates curve ladder (christina).

```markdown
## News/Market check (Renee-topic)
- 📰 News: ≥1 sentence (Daily URL≤5) or Weekly 2–3 sentences (URL≤12) · outlet/URL/as-of · or `News: miss`
- 📊 Market tape: one line on volume / 20d range / leadership
```

### 4. `## Lenses` (REQUIRED)

```markdown
## Lenses
- Macro: cite Alice brief if present · one line regime/index context (overlay; do not set desk Risk-on/off). Alice macro brief miss → `No brief.` / `miss` **here** (Lenses Macro), NOT in Alice pull
- Micro: one line pack/ticker structure
- Market: one line volume/range/narrative · Conf effect
- Dominant: macro-led | micro-led | market-led | mixed
```

Daily compact OK; Weekly: three-lens stub + Dominant required.

### 5. Optional § T&M signal funnel

When `scoring-eval/*-daily-eval.json` exists → cite via `skills/tm-signal-funnel` (after Lenses / before ranking).  
**3-layer eval lookup:** prefer `shared/reports/renee/scoring-eval/`, then workspace sibling; cite basename `scoring-eval/*-daily-eval.json`.  
Missing → **N/A + pending**; do **not** invent.

### 6. Ranking (live pack only)

| Ticker | `tm_score` | Bracket | Note |
|--------|------------|---------|------|
| … | pack truth | BUY / WATCH / … | … |

- Every BUY/WATCH needs `tm_score` + `score_breakdown` (see `tm-e5-firewall`)  
- ❌ **Never** blend / sort / gate with Eliza `valuation_score`  
- ❌ **Never** bare unlabeled `score`  
- ❌ **No score rewrite** on revise

### 7. Key ticker notes · risk / omissions · Response Tracker

ATR entry/SL/TP when pack supplies; misses → `attempted + miss`.  
Zoe items → Response Tracker (confirmed / partially confirmed / not confirmed + evidence).

**Optional Notes/Market overlay — short interest/FTD (cite-only):** for **selected names only** (budget: few tickers). Prefer official FINRA Equity Short Interest + SEC Fails-to-Deliver over ChartExchange; cite URL + as-of, or `attempted + miss`. ❌ never mutate `tm_score` / brackets / Option 6 / BUY·WATCH. Rate notes optional (brief): FINRA async ≤20/min; SEC ≤10/s + User-Agent.

- FINRA: https://www.finra.org/finra-data/browse-catalog/equity-short-interest/data
- SEC FTD: https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data

### 8. Sources

```markdown
## Sources
- 📊 Data: live tm pack · <basename> · as_of …
- 📰 News: <outlet · URL · as-of> or News: miss
- Short/FTD (optional): FINRA/SEC · URL · as-of · or attempted + miss
- Eval: scoring-eval/<date>-daily-eval.json · or N/A + pending
- Misses: <item>: attempted + miss
```

---

## Save / deliver

- Draft: workspace + shared OK  
- User-facing revised: **3-layer** portal paths above  
- **Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`  
- Reviser = **`renee`** (not Alice)  
- Alice overall cites: `## Market insight` (priority) + `## Session summary`

---

## Hard rules

- Required **`## Session summary`** + **`## Market insight`** + News/Market + Lenses (daily + weekly)
- Before finalizing ranking, News/Market must pass. Ranking without a News section and without explicit `News: miss` → Zoe **REJECT**
- **No score rewrite** — never recompute / reshuffle `tm_score` from narrative (including short/FTD)
- **Weekly: no Option G** suppress language as if applied
- **E5:** never blend `valuation_score` into T&M ranking (`tm-e5-firewall`)
- Funnel missing → **N/A** (`tm-signal-funnel`)
- ❌ Desk Risk-on/off / desk-wide Macro view final call (Alice only; Zoe Z-MI-02)
- Invented scores / missing Session summary / Market insight → **Zoe REJECT** territory
- **Fail-closed G1:** Revise MUST insert the four headings if generator omitted them. Forbidden to write “this report has no ## Market insight” or treat Tracker as substitute. Zoe M1 wrong-day tape → rewrite today’s 3–6 bullets, do not delete the section.

---

## Banned

- Headlines-only with empty Session summary / Market insight
- Weekly Option G BUY suppress  
- Blended tm+value leaderboard / bare `score`  
- Alice revising T&M scores on callback  
- Broker / account / fill language  
- Excel / Office JS automation of pack ranks  
- Desk Risk-on/off final-call sentences
