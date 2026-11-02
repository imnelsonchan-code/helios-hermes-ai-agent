# Eliza — Hermes refined draft (H-W1)
> Not Helios prompts · Not live Hermes host · Scrubbed for review

**Skills checklist** — mapped from the shared Hermes investment-skill inventory and historical Eliza profile snapshots.

For **this Git refine tree**, Eliza's source of truth is `SOUL.md` plus this checklist. **Profile skills** live under `profiles/eliza/skills/*/SKILL.md` (earnings-preview / earnings-analysis / comps-analysis / value-session / valuation-width / a08-followup). Shared host skills remain `investment/*` on the live Hermes host. Historically, shared `hermes/skills/investment/*` resolved for Eliza, often through a profile `skills/investment` link. Restore snapshots also retain profile-local `trading/*` copies of `earnings-quality`, `accounting-red-flags`, `capital-structure`, and `stock-valuation`. Prefer shared `investment/valuation-screener` plus shared `investment/stock-valuation` for width and DCF. Treat profile-local `trading/*` as compatibility/legacy until its unique checks are folded; do not dual-run conflicting weights.

| Field | Value |
|-------|-------|
| **Profile** | `eliza` |
| **Process** | **P-VAL** |
| **Inventory date** | 2026-09-22 (P0 value-session / valuation-width / a08-followup) |
| **Git source of truth** | `SOUL.md` + this checklist + `profiles/eliza/skills/*/SKILL.md` |

**Scrub:** no host paths, API keys, cron/job IDs, MEMORY, or holdings. Script entrypoints named by basename only.

---

## 1. How to use this checklist

- **Keep** = load for Eliza valuation / width / SEC work.  
- **Inbound** = other agents call Eliza (not Eliza’s primary skill set).  
- **Exclude** = T&M / Alice-only / Zoe-only / ops — do not treat as Eliza core.  
- **Legacy name** = mentioned in old SOUL; not found as a top-level shared skill folder in focused archive — confirm before OSS pack.

Helios `app/agents/prompts/eliza.md` tasks are **reference only**; this file does not change Helios.

### Skill resolution

| Class | Resolution |
|-------|------------|
| Shared **Keep** | Expected to resolve through shared `investment/*` skills. |
| Legacy profile-local | Still present in restore snapshots under `profiles/eliza/skills/trading/`; fold unique checks at OSS/apply, and do not dual-run conflicting weights. |

---

## 2. Core valuation & width

| Skill (folder) | Category | Purpose | Status |
|----------------|----------|---------|--------|
| `investment/stock-valuation` | valuation | Single-name / deep-dive multi-method DCF + multiples; sensitivity; report synthesis. Not required on Sunday width pack. | **Keep** |
| `investment/valuation-screener` | width | Weekly width: percentiles + quality overlay + P/E-band (or applicable multiple) FV; informational reverse DCF; **Track A/B** universes. For every published selected ticker, emit numeric five-factor-only `valuation_score` (0–100) + `width_verdict`, never `tm_score`; if scoring fails, omit the ticker from selected rows and record it under Omissions. This is not a full 12-method DCF. | **Keep** |
| `investment/dcf-sensitivity` | valuation | Single-name / deep-dive WACC×g (and related) sensitivity matrices; not required on Sunday width pack | **Keep** |
| `investment/probabilistic-valuation` | valuation | Single-name / deep-dive Monte Carlo / distributional FV; not required on Sunday width pack | **Keep** |
| `investment/reverse-dcf` | valuation | Informational on width; assumption check on single-name / deep-dive work | **Keep** |
| `investment/sotp-valuation` | valuation | Sum-of-the-parts when segments warrant | **Keep** |
| `investment/financial-analysis` | statements | P&L / BS / CFS + ratios | **Keep** |
| `investment/financial-health` | quality | Solvency / health flags for veto & verdict gates | **Keep** |
| `investment/solvency-verification` | quality | Debt / coverage sanity | **Keep** |
| `investment/peer-comparison` | relative | Multi-factor peer context | **Keep** |
| `investment/segment-analysis` | build-up | Segment-level build-up for DCF inputs | **Keep** |
| `investment/dividend-analysis` | income | Dividend / payout when applicable | **Keep** |
| `valuation/eliza-valuation-moa-pipeline` | QA | Valuation + MOA review workflow (FRED / SEC / MC notes) | **Keep** |
| `mlops/eliza-dcf-unified-core` | toolchain | Maintain valuation script pipeline (ops-adjacent; methodology only in drafts) | **Keep** (doc) |

### Track A/B vs Option A/B (checklist note)

- Screener / width reports use Hermes **Track A** (Large+Mid) and **Track B** (Small Cap) as **report chapters / screen universes**.  
- That is **≠** Helios Eliza enhancement **Option A/B** (cache / DCF v3).  
- H-W1 documents format expectation only — **no** Helios `render_weekly_value` swap.

### Scoring namespace

- Every published selected Eliza ticker uses a numeric `valuation_score` on a **0–100** scale representing the five factors only; a rank or selected `N/A` row does not satisfy the contract. If Eliza cannot calculate it, put the ticker and reason under **Omissions**, not in the selected table.
- Every selected value stock includes `valuation_score_breakdown` with keys `pe`, `ev_ebitda`, `pb`, `fcf_yield`, and `rev_growth` for the live pack's **33/28/19/15/5** factors. Those pack weights are truth; older **30/25/20/25** and **27/22/18/22/11** variants are obsolete documentation and must not be narrated as current.
- Pack/runner mapping: live `composite_score` is preserved as 0–1 `valuation_composite`, and `round(composite_score × 100)` becomes published `valuation_score`. Map `adjusted_composite` to `quality_adjusted_score`: values ≤1.5 are treated as 0–1 and multiplied by 100; values >1.5 are already 0–100. Until the runner renames its fields, Eliza revise must apply this mapping, set `quality_adjusted`, and rename generic **Score / Adj** columns to **Valuation Score / Quality-Adjusted Score**; never write the adjusted value into `valuation_score`.
- Width JSON must include `valuation_score`, `valuation_score_breakdown` (`pe` / `ev_ebitda` / `pb` / `fcf_yield` / `rev_growth`), `valuation_composite`, `quality_adjusted`, `quality_adjusted_score`, `width_verdict`, and `e5_overlap`.
- The canonical Candidate floor is FV upside **≥+15%** subject to quality gates. **+30%** sets `strong_candidate: true`; it is not the Candidate admission floor.
- Renee owns `tm_score` on a 0–100 scale, with `score_breakdown`, for selected T&M names. Eliza must never load `scoring-engine-v4.*`.
- Eliza's quality overlay is limited to F-score, Z-score, earnings-quality, accounting, and sector checks; do not import T&M indicators.
- **Known host gap:** quality checks may still run only on the Top 20 before re-sorting. This checklist discloses that behavior; it does not claim to fix it.

### Host eval scripts (P0/P1)

| Reference | Category | Purpose | Status |
|-----------|----------|---------|--------|
| Host eval scripts (`scripts/host/`: `sleeve_paper_book`, `value_ic_tracker`, `prediction_settler`, `value_veto`, `fcf_fv_bands`, `pit_checklist`) | doc | P0/P1 value eval overlays — Paper Book V, IC tracker, prediction settle (`value_hit_rate`), extra vetoes, FCF FV bands, PIT checklist | **Optional** |

Documentation only; not a skills tree. Vetoes via `value_veto.py` do not fold into `valuation_score`; optional `fv_engine: fcf_band_10_15_20` beside `pe_band`; Candidate still ≥+15% vs chosen band.

---

## 3. Research quality & SEC

| Skill (folder) | Category | Purpose | Status |
|----------------|----------|---------|--------|
| `investment/company-research` | qualitative | Business model, catalysts, industry context | **Keep** |
| `investment/moat-assessment` | qualitative | Moat score + evidence + erosion | **Keep** |
| `investment/risk-analysis` | qualitative | Quantified risk matrix | **Keep** |
| `investment/management-quality` | qualitative | Capital allocation / governance signals | **Keep** |
| `investment/insider-signals` | qualitative | Insider / buyback context | **Keep** |
| `investment/sector-specific-distress` | quality | Sector-aware distress (e.g. bank interest-coverage pitfalls) | **Keep** |
| `investment/sec-edgar-data-fetch` | SEC | Filings metadata / structured pulls | **Keep** |
| `investment/sec-edgar-document-retrieval` | SEC | Document retrieval for primary numbers | **Keep** |
| `investment/sec-edgar-filing-monitor` | SEC | Filing watch / alerts (research use). Daily SEC cron is paused (2026-09-08); competence kept. Adhoc/manual still writes dated `sec-monitor/YYYY-MM-DD_sec-monitor.md` on all 3 layers, including quiet days. | **Keep** |
| `investment/yahoo-finance-data-fetch` | data | Market / fundamentals fetch | **Keep** |
| `investment/finviz-screener` | data | Screen source for width Tier-1 | **Keep** |
| `investment/stock-deep-dive` | deep | Sunday / ad-hoc deep car style analysis | **Keep** |
| `investment/single-stock-check` | deep | Single-ticker validation gates | **Keep** |
| `investment/earnings-calendar` | calendar | Earnings timing context (not T&M scores) | **Keep** (optional) |
| `skills/earnings-preview` | calendar | Profile skill: pre-earnings one-pager (consensus/miss, watch list, bull/base/bear); free data; **does not** change `valuation_score` | **Keep** (profile) |
| `skills/earnings-analysis` | calendar | Profile skill: post-print ~1–3 page note (beat/miss, Sources); may flag model-update later; never auto-touch width runner | **Keep** (profile) |
| `skills/comps-analysis` | relative | Profile skill: peer table contract (as-of, multiples, sources) on top of `peer-comparison`; informs FV context only; never overwrite `valuation_score` | **Keep** (profile) |
| `investment/data-quality-audit` | QA | Data freshness / coverage checks | **Keep** (optional) |

### Profile skills (P0 — `profiles/eliza/skills/*/SKILL.md`)

| Skill (folder) | Category | Purpose | Status |
|----------------|----------|---------|--------|
| `skills/value-session` | session | Daily value-session: `## Session summary` → `## Market insight` → News/Market → Lenses → movers vs Sunday lock; Today spot / Sunday lock FV / Display upside % columns; cite Sunday `valuation_score` only; no value-100 re-rank; no desk Risk-on/off; Draft → Zoe → Eliza revise → `inbox/value-session/YYYY-MM-DD-*-revised.md`. Never `tm_score`. | **Keep** (profile) |
| `skills/valuation-width` | width | Weekly width revise: `## Market insight` + News/Market + Lenses + Track A/B; Spot (as_of) / FV Range / Upside % display columns from pack JSON; `composite_score` → `valuation_score`; Candidate ≥+15% + quality; Omissions; `e5_overlap` WARN. Never rewrite runner arithmetic; never `tm_score`; never desk Risk-on/off; display upside does not re-rank. | **Keep** (profile) |
| `skills/a08-followup` | follow-up | Monday A-08: no re-score/re-rank; skip 🔴 and missing numeric Sunday scores; Today spot / Sunday lock FV / Display upside % (cite only); repeat `valuation_score` verbatim; no invented prices/FV. Never `tm_score`. | **Keep** (profile) |
| `skills/position-plan-value` | position | If assigned, write value comment and analysis in that day's `## Position comments` even when Sunday width has no row. Insight / Direction / SL / TP / Target / On hold. Never `tm_score`. Never a new official `valuation_score`. | **Keep** (profile) |

**Provenance note:** profile session / width / A-08 outputs stamp required `as_of`; optional `generated_at` / `data_delay` when pack or fetch provides them.

---

## 4. Reporting & collaboration

| Skill (folder) | Category | Purpose | Status |
|----------------|----------|---------|--------|
| `investment/request-eliza-valuation` | inbound | Alice/Renee pattern to request Eliza valuation | **Inbound** |
| `investment/investment-profile-architecture` (+ `references/eliza-micro-analyst.md`) | architecture | Role boundary reference | **Keep** (reference) |

### Helios-aligned task labels (skills-layer mapping · no code)

| Helios-aligned label | Skills / checklist focus |
|----------------------|--------------------------|
| Width narrative + revise | `skills/valuation-width` + `valuation-screener` + `finviz-screener` + `yahoo-finance-data-fetch` + `financial-health`; Zoe items → Response Tracker; `## Session summary` + `## Market insight` + News/Market + Lenses; inbox `valuation-width/*-revised.md` |
| Daily **value-session** | `skills/value-session` — Desk-pack #4: Market insight + News/Market + Lenses + movers vs Sunday lock; Zoe → eliza revise → `inbox/value-session/*-revised.md`; **not** Alice-arm-only; required `## Session summary` + `## Market insight`; provenance `as_of` |
| **A-08** follow-up | `skills/a08-followup` — Follow up top value names without re-scoring; repeat the numeric Sunday `valuation_score` only and skip names that do not have one |
| Saturday value artifacts | Check runner/revise field mapping, numeric `valuation_score` on every selected name, coverage, omissions, JSON/Markdown artifacts, and the E5 exclusion list |
| **D-X8** value overlay propose | Narrative/propose responsibility in SOUL; **no** `tm-exit` skills or T&M scoring skills |

---

## 5. Explicit exclusions (not Eliza core)

| Skill / area | Why |
|--------------|-----|
| `investment/scoring-engine-v4.*` / `scoring-engine-audit-checklist` | **E5 hard exclusion:** P-TM / Renee scoring only. Never load for Eliza, never emit `tm_score`, and never mix T&M weights or indicators into `valuation_composite`, `valuation_score`, or Eliza quality checks. |
| `trading/stock-screener` | Renee T&M universe screen — not Eliza width |
| `skills/market-close-report-format` | **Alice** daily ten-heading trunk (§4) |
| `investment/zoe-challenge-*` | **Zoe** owns challenge rubrics / enforcement |
| `trading/*` technical / breakout / journal | Renee / trading sleeve — not P-VAL core |
| `skills/alice-weekly-report` | Alice Sunday deep-dive (same ten headings) |
| Devops / kanban / cron / auth / WAF skills | Ops — not investment-agent refine |
| `.archive/eliza-dcf-unified-methodology` | Archived; prefer live `eliza-dcf-unified-core` + valuation skills |

---

## 6. Legacy SOUL names (confirm)

Old Eliza SOUL listed these as loaded skills. Some are not shared top-level folders, but unique checks still exist in profile-local `trading/*` skills on restore snapshots:

| Legacy name | Likely coverage today |
|-------------|------------------------|
| `earnings-quality` | Unique checks remain in the profile-local trading skill; shared `financial-health` does not implement all of them. **TODO:** fold at OSS/apply. |
| `forecast-model` | Fold into `stock-valuation` / segment build-up |
| `capital-structure` | Unique checks remain in the profile-local trading skill; shared health/solvency/dividend skills are not a complete replacement. **TODO:** fold at OSS/apply. |
| `accounting-red-flags` | Unique checks remain in the profile-local trading skill; shared `financial-health` and `sector-specific-distress` do not implement all of them. **TODO:** fold at OSS/apply. |
| `valuation-reference` | Format/spec — superseded by Track A/B notes in SOUL + deferred H-W-path |

These checks are **not yet folded**. Do **not** invent MEMORY or copy live skill bodies into Git; reconcile and fold them at OSS / Hermes apply time.

---

## 7. Toolchain note (scrubbed)

- The historical width runner basename is `valuation_width_scan`. Restore/collect may miss profile scripts; that is a restore/host gap, not tooling shipped by this checklist.
- `m7_detailed` / Emily M7 is outside Hermes refine and must not be treated as an Eliza width runner.
- Deep valuation scripts may orchestrate DCF, sensitivity, peer, moat, reverse DCF, SOTP, Monte Carlo, SEC, insider, and red-flag helpers; that full stack is not the Sunday width contract.
- Tertiary data providers may need env keys on the **host** — never commit keys; document “required env var name only” if needed later.  
- Composite / IC validation for width is methodology under `valuation-screener` — omit live IC numbers, cron IDs, and portfolio pilot results from drafts.

---

## 8. Model

Not pinned in this draft. Select in Hermes setup / `hermes model`. MOA (if used) is a Hermes config preset.

---

## 9. Checklist sign-off (H-W1)

- [x] Inventory from shared `hermes/skills/` (valuation-related)  
- [x] Scrub paths / secrets / IDs / MEMORY / holdings  
- [x] P-VAL boundaries; E5 never blend with T&M  
- [x] Track A/B report chapters ≠ Helios Option A/B  
- [x] A-08 + daily value-session (+ valuation-width) **profile skills landed**; D-X8 value overlay still Helios-aligned **docs only**  

- [x] Phase-3: daily `value-session/` portal path; `## Session summary` + valuation stance; not Alice-arm-only
- [x] Git source-of-truth separated from historical shared/link/profile-local resolution
- [x] Width contract separated from single-name / deep-dive valuation
- [x] Raw `valuation_composite`, published `valuation_score`, and 33/28/19/15/5 `valuation_score_breakdown` documented
- [x] Every selected ticker requires per-ticker `valuation_score` (0–100)
- [x] Runner `composite_score` / `adjusted_composite` mapping and Score / Adj column renames documented
- [x] Unscorable names move to Omissions; selected rows cannot publish `N/A`
- [x] Width JSON must-have scoring, quality, verdict, and E5 fields documented
- [x] Candidate floor fixed at +15%; +30% is `strong_candidate` only
- [x] A-08 repeats numeric Sunday scores only; Saturday audits mapping and selected-name scores
- [x] E5 / `scoring-engine-v4.*` / `tm_score` hard exclusion strengthened
- [x] Legacy quality checks disclosed as not yet folded; OSS/apply TODO recorded
- [x] Historical width-runner and restore/host gaps documented by basename only
- [x] Profile skills P0: `value-session` / `valuation-width` / `a08-followup` SKILL.md + checklist / SOUL pointers
- [x] Provenance: required `as_of`; optional `generated_at` / `data_delay` noted for session / width / A-08
- [ ] Owner accept on wording  
