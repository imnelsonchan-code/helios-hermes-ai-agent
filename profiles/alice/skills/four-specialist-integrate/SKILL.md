---
name: four-specialist-integrate
description: >-
  Alice overall desk-pack (#5): news/social plus four specialist Market insights
  + Session summaries (emily · christina · renee · eliza), required Macro view,
  Relationships/cross-links, desk Risk-on/off, gaps/callbacks. Daily market-close
  and weekly deep-dive. Load with market-close-news-social. Daily callback ≤1 +
  material_gap; weekly ≤4. E5++ no blend. Alice alone owns Macro view + desk regime.
---

# Four-specialist integrate — desk overall (#5)

**Owner:** Alice · **Train:** daily market-close overall · weekly deep-dive overall · Sat performance overall (S1)  
**Load with:** `skills/market-close-news-social` (news/social blocks) + `skills/market-close-report-format` (daily ten-heading trunk) or `skills/alice-weekly-report` (weekly, same ten headings). Retired shared paths `investment/market-close-report-format` / `research/alice-weekly-report` are not the trunk.  
**Not:** sixth Jobs light · replace four session main files · daily T&M revise (→ Renee) · invent counterpart scores/FV/`B_*`/`FX_*`/`C_*`

Mark "Not investment advice". Source grading: `📊 Institutional` / `📰 News` / `📊 Data` / `⚠️ Social`.

---

## 1. Modes

| Mode | When | Depth |
|------|------|-------|
| `daily` | Mon–Fri desk pack Leg 5 / market-close overall | Alice-owned Session summary + News/social + four Market insights + Session summaries + **Macro view (required)** + Relationships + desk Risk-on/off + Gaps / callbacks |
| `weekly` | Sunday deep-dive Leg 5 | same ten headings; Macro view ≈1 page; GICS/crash-indicator inside Macro view |
| `sat-overall` | Saturday Leg 6 (S1 portal) | Alice-owned Session summary + cite prior Sunday 5-pack (or miss) + scoring-eval hit rates; process retrospective |
| `adhoc` | Gap-only Kanban | Same schema; mark `material_gap` |

**Forbidden modes:** social-watcher path (`*-snapshot.md`) · pure T&M revise · paste four full sessions into one file as substitute for portal lights.

---

## 2. Merge map (5-pack)

| # | Report | Reviser | Inbox (cite) |
|---|--------|---------|--------------|
| 1 | Commodities session | emily | `inbox/commodities-session/*-revised.md` |
| 2 | Rates/FX session | christina | `inbox/rates-session/*-revised.md` |
| 3 | T&M/technical | renee | daily `inbox/daily-trend-momentum/*-revised.md` · weekly `inbox/weekly-trend-momentum/*-revised.md` |
| 4 | Value/valuation | eliza | daily `inbox/value-session/*-revised.md` · weekly `inbox/valuation-width/*-revised.md` |
| 5 | **Overall (this skill)** | **alice** | daily `inbox/market-close/` (+ `daily-social/` companion) · weekly `inbox/weekly-deep-dive/` · Sat `inbox/weekly-performance/` |

**Barrier:** No Alice overall draft until all four `*-revised.md` exist **or** each missing leg is explicit `miss`. Overall still ships with gaps. Four-path may be `pending-rechallenge` (Zoe ran ≠ PASS)— still ship, do **not** mark `ok`.

**Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`.

**emily/christina:** own portal Jobs lights (P3); Alice **cites** their revised Market insight + Session summaries — no second Jobs light ban.

---

## 3. Input cite table (freshness/miss/compact)

| Specialist | Read (prefer → fallback) | Alice does not |
|------------|---------------------------|----------------|
| emily | `inbox/commodities-session/*-revised.md` (**`## Market insight` prefer** + `## Session summary`) → else `shared/reports/emily/…` | write second ten-column/`C_*` essay |
| christina | `inbox/rates-session/*-revised.md` (**Market insight prefer** + Session summary) → else `shared/reports/christina/…` | write second curve/`B_*`/`FX_*`/DXY table |
| renee | `inbox/daily-trend-momentum|weekly-trend-momentum/*-revised.md` (**Market insight prefer** + Session summary) | reshuffle/change `tm_score` |
| eliza | `inbox/value-session|valuation-width/*-revised.md` (**Market insight prefer** + Session summary) | invent FV/`valuation_score` |
| social feed | same-day `social-watch/*-snapshot.md` | re-crawl Top-20/Reddit/StockTwits |

Missing → that leg one line `miss`/`attempted + miss`; **do not** fill with another sleeve score/Signal.  
**One leg miss still ships overall** (mark gap). Compact cite: each insight **3–5 bullets** only when same-day inbox `*-revised.md` **and** Zoe PASS/no re-challenge; summary may add 2–4 bullets; do not full-paste session body.  
Freshness: prefer same session date/ISO week. **Stale/unre-challenged/T-1 lock** specialist insight → that leg `miss` or `as-of T-1 + gap` — **do not** treat as live 3–5 bullets.  
**Barrier (§2):** prefer **Zoe-revised inbox** when present; shared/reports is draft/miss fallback only.

**DXY/USD depth:** cite christina path or `miss`; Alice ≤1 sentence desk USD pointer — ❌ second DXY/`FX_*` forecast table.

---

## 4. Required section order (overall #5 · hard)

Paste in **this order** — do not invent a parallel top-level skeleton:

```markdown
# … overall title …
Not investment advice · Alice · status: draft | revised (Zoe)

## Header
As-of · cadence · Zoe status · four-path status (`ok` | `miss` | `pending-rechallenge`)
※ four-path: **`ok`** = same-day inbox revised **AND** Zoe PASS/no re-challenge required. **`pending-rechallenge`** = Zoe ran ≠ PASS, revise pending, or unre-challenged/T-1 fuel. **`miss`** = same-day revised absent (reason). ❌ `✅` ≠ Zoe PASS. ❌ owner self-claim **5/5 revision stands**/PASS — Zoe re-votes.

## Session summary
Alice **owned** overall block (after Header; 5–8 bullets): four-path, desk regime pointer, largest agree/tension/miss.
❌ paste four summaries here. Four cites stay under `## Four Session summaries`.
Missing this section → Zoe **REJECT** (`desk-artifact-contracts` ART-SESSION-SUMMARY).

## News / social / macro
(`market-close-news-social` A+B: ledger + themes/bull-bear + news vs social)
※ §B = Alice **owned** news/social lens — **does not** replace four Market insights

## Four Market insights
### emily · commodities
cite `## Market insight` — bullets or `miss`
### christina · rates
cite `## Market insight` — bullets or `miss`
### renee · T&M
cite `## Market insight` — bullets or `miss`
### eliza · value
cite `## Market insight` — bullets or `miss`

## Four Session summaries
### emily · commodities
cite Session summary — bullets or `miss`
### christina · rates
…
### renee · T&M
…
### eliza · value
…

## Macro view
(**daily + weekly required**)
Review four Market insights → agree/tension/miss → desk-wide macro relationship narrative.
Daily ≈ 8–15 lines; Weekly ≈ 1 page (equities + rates + FX + commodities + valuation tension).
Source grading; four paths labeled separately; ❌ single leaderboard; shadow `rates_*`/`commodity_*` not comparable sleeve scores in Jobs.
(may keep subtitle Full market summary; SSOT heading = `## Macro view`)

## Relationships
(see §5; daily = ≤2–4 **SENTENCES** — daily MUST NOT use weekly-style table; table >4 rows = self-check fail; weekly ≤6–8 rows)
implication **must anchor** Market insight cite path + owner

## Desk Risk-on/off
Risk-on | Neutral | Risk-off | Crisis + one-line rationale (institutional/price; ❌ social heat alone)
**Only** Alice finalizes (Zoe Z-MI-02: specialist boundary → REJECT)

## Gaps / callbacks
(see §7–8)

## Sources
(`market-close-news-social` **D** + session paths + Market insight cites + misses)
```

Ten headings = list above (Header → Session summary → News/social/macro → Four Market insights → Four Session summaries → Macro view → Relationships → Desk Risk-on/off → Gaps/callbacks → Sources). Weekly uses `skills/alice-weekly-report`: **same ten headings**, no parallel top-level skeleton. P-TM/P-VAL week cites inside renee/eliza Four Session summaries; Sat eval two lines in Session summary or Gaps. GICS 11 and crash-indicator inside `## Macro view`.

---

## 5. Relationships / cross-link schema

| Column | Content |
|--------|---------|
| `drivers` | What links two+ domains (prefer from Market insights) |
| `agree/tension/miss` | Stance |
| `implication` | **Narrative/watch/gap only** — ❌ change Signal/score/rank/Obs |
| `cite path` | Session revised path + **Market insight** section or `miss` |
| `owner` | emily|christina|renee|eliza |
| `regime_field?` | `desk`|`rates_regime`|`commodity_regime` |
| `as-of` | Date/week |

**Budgets:** weekly ≤6–8 rows; daily ≤2–4 **SENTENCES** — **daily MUST NOT** use weekly-style table (any table >4 rows = self-check fail).  
**Allowlisted edge examples:** rates↔equity · FX↔commodity · credit(HYG)↔risk-assets · value↔tm overlap (E5 WARN only) · rates↔gold (via christina cite).  
HYG/credit: credit-spread language only — ❌ map to desk Risk-on.  
❌ Relationships from news/social heat alone without four insight anchors.

---

## 6. Implication grammar

Allowed: narrative tension · near-term watch · gap/callback pointer · Not investment advice.  
Forbidden: score/rank/bracket rewrite · new `C_*`/`B_*`/`FX_*`/Obs TP · blended leaderboard.

---

## 7. Callback card schema

```text
target: emily|christina|renee|eliza|(discuss: a+b)
link_id: <short>
requested_fields: …
material_gap: true|false
retry: 0|1
```

Alice may (a) request missing fields (incl. missing Market insight), or (b) ask two+ owners to **discuss and return a joint sum-up** (adhoc; owner-authored; Alice cites).  
Discuss notes live under `shared/reports/…` or session changelog — **not** a 6th Jobs light.

**Hard:** **Callback changes lock** `tm_score`/`valuation_score`/`C_*`/Obs (unless normal Zoe→owner revise).  
**Daily target (hard):** the ≤1 daily card **must** target the train-blocking `material_gap` (unre-challenged/T-1 lock/missing same-day Wave1)— ❌ a 5bp side issue if a P0 gap exists.

---

## 8. Budgets

| Cadence | Callback cards |
|---------|----------------|
| Daily overall #5 | **≤1** total; must `material_gap: true` **and** target = train-blocking gap (unre-challenged/T-1 lock/missing same-day Wave1) |
| Weekly/Sunday deep-dive/weekly integrate | **≤4** total (≤1–2 each; discuss cards count) |
| Per gap | ≤1 retry |
| Adhoc gap-only | `material_gap: true` required |

---

## 9. Desk regime (three-field rules)

| Field | Owner | Values |
|-------|-------|--------|
| Desk Risk-on/Neutral/Risk-off/Crisis | **Alice** | these four only |
| `## Macro view` | **Alice** | desk-wide macro relationships; review four insights |
| `rates_regime` | christina (cite) | `easing`/`tightening`/`mixed`/`unclear` — ❌ not desk Risk-on/off |
| `commodity_regime` | emily (cite) | commodity vocabulary |

❌ use rates/commodity regime/social heat/HYG **alone** to set desk Risk-on/off.  
❌ Specialist finalizes desk Risk-on/off or “desk-wide Macro view” (Zoe Z-MI-02).

---

## 10. E5++ anti-blend

- Show `tm_score` and `valuation_score` with separate labels; never average/blended leaderboard/bare `score`
- ❌ mix `shadow_rates_score`/`rates_signal`/`B_*`/`FX_*`/`C_*`/commodity shadow with sleeve scores as comparable ranks
- Juxtapose only; Jobs does not treat shadow rates/commodity as a third sleeve

---

## 11. Stub coexistence

Commodity depth and rates depth cite rows **coexist** in overall; each path + `miss` rules independent.  
USD/DXY **depth** → cite christina; Alice at most **one** desk USD pointer sentence.

---

## 12. Zoe handoff

1. Alice draft overall (this skill order) → “Pending Zoe challenge”  
2. Zoe IC gate (REJECT: missing Alice-owned `## Session summary`; missing four Market insight cites or `miss`; missing `## Macro view`; missing four summary cites; headlines-only news; **Market-close social claims** without snapshot cite; blend; Alice self-writes counterpart depth; Z-MI-03/Z-MI-04)  
3. Alice revise → inbox `*-revised.md` (3-layer)  
4. **Reviser = Alice only** for #5 — do not route revise to christina/emily/renee/eliza  
5. ❌ Alice/owner self-claim **5/5 revision stands**/PASS — **Zoe re-votes**. Four-path `ok` only when same-day revised **AND** Zoe PASS/no re-challenge

---

## 13. Daily / Sunday deep-dive / Sat S1 (desk-pack P3a lock)

| Cadence | Alice overall |
|---------|---------------|
| **Daily #5** | Alice-owned `## Session summary` (after Header) + News/social + **Four Market insights** + four Session summaries **or miss** + **Macro view (8–15 lines required)** + Relationships (≤2–4 SENTENCES; ❌ weekly-style table) + desk regime + `## Gaps / callbacks`; four-path `ok`|`miss`|`pending-rechallenge`; callback ≤1 + `material_gap` **targeting train-blocking gap**; ❌ paste FX/bond/ten-column depth |
| **Sunday deep-dive #5** | same ten headings, incl. Alice-owned `## Session summary` + **Macro view (≈1 page)**; GICS/crash-indicator inside Macro view; embed specialists via cite/callback — ❌ second full specialist session paste |
| **Saturday S1** | One portal light `weekly-performance/`; cite prior 5-pack + process/eval notes — ❌ second full weekly overall |
| **Weekly integrate** | **One** draft; merge-map §2; keep P-TM/P-VAL/data integrity/Sat eval cite |

> Cadence note: desk-pack locks Daily=#5 overall (not legacy “daily 3-arm only”). Sat S1 = performance cite-back; full four-way depth main stage = Sunday deep-dive/weekly integrate.

---

## 14. Contract smoke (heading strings)

Assert strings for tests/self-check:

- `Market insight`
- `Four Market insights`
- `Macro view`
- `Session summary`
- `Risk-on`
- `commodities-session` **or** `rates-session`
- `Relationships`
- `callback`/`≤4`/`material_gap`
- `four-specialist-integrate`
- `shared/reports/christina` **or** `shared/reports/emily`
- `Not investment advice`
- one-leg `miss` still ships

---

## Integrate checklist

1. Soft-wait four revised|miss|pending-rechallenge + social snapshot|miss; honest four-path  
2. Write sections in **§4 order**  
3. Load `market-close-news-social` for news/social/Sources  
4. Cite **Four Market insights** (prefer) + Four Session summaries — stale/T-1/unre-challenged → miss or `as-of T-1 + gap`  
5. Write **Macro view** (daily + weekly required)  
6. Relationships (daily ≤2–4 SENTENCES — ❌ weekly-style table); desk Risk-on/off; callbacks per §8 (daily ≤1 targets train-blocking gap)  
7. Zoe → Alice revise → dual inbox (daily) or weekly-deep-dive/weekly-performance — ❌ self-claim **5/5 revision stands**/PASS  
