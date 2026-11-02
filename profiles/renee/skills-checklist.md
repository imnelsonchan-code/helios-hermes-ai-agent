# Renee — Hermes refined draft (H-W1)
> Not Helios prompts · Not live Hermes host · Scrubbed for review

**Agent:** `renee` · **Process:** **P-TM**  
**Source map:** shared `hermes/skills/` (trading + T&M-related investment / reporting / communication / investigation) + **profile skills** under `profiles/renee/skills/*/SKILL.md` (P0: `tm-session-report` / `tm-signal-funnel` / `tm-e5-firewall`).  
**Purpose:** Checklist for Hermes refine / later OSS — not executable skill bodies (except profile `SKILL.md` drafts in this tree).

| Field | Value |
|-------|-------|
| **Profile** | `renee` |
| **Git source of truth** | `SOUL.md` + this checklist + `profiles/renee/skills/*/SKILL.md` |
| **Inventory date** | 2026-09-22 (P0 profile skills) |

Status legend: **Keep** · **Optional** · **Archive-ref** · **Out** (not Renee-owned)

---

## 0. Profile skills (P0 · 3 + regime narrate + position comment)

| Skill (folder) | Purpose | Status |
|----------------|---------|--------|
| `tm-session-report` | Daily + weekly T&M trunk: Header → `## Session summary` → `## Market insight` → News/Market → Lenses → optional funnel → ranking (live pack) → key notes; portal revise; reviser=`renee`; no score rewrite; no desk Risk-on/off; daily Option G OK / weekly NO Option G; candidate/watchlist language; Not investment advice | **Keep** |
| `tm-signal-funnel` | § T&M signal funnel cite from `scoring-eval/*-daily-eval.json`; N/A if missing; null ADX → N/A; monotonic theo≥after_G≥after_vol; three labels; demotions do not change `tm_score`; Sat Mon–Fri roll-up; never invent; never Book V / `value_hit_rate` | **Keep** |
| `tm-e5-firewall` | Never blend with `valuation_score`; every BUY/WATCH needs `tm_score`+`score_breakdown`; no bare score; overlap WARN only; Alice cites Market insight (priority) + Session summary; callback anti-mix | **Keep** |
| `tm-regime-exposure` | Narrate only: regime → size/threshold → sentence. Cites pack SPY ADX. Choppy = generator already wrote no-trade (ADX < 25). Does not change `tm_score` or the cutoff. Weekly no Option G. Held-back list is score ≥60 | **Keep** |
| `position-plan-trend` | If assigned, write trend comment and analysis in that day's `## Position comments` even when same-day T&M has no row. Insight / Direction / SL / TP / Target / On hold. No `valuation_score`. Not the daily T&M load. | **Keep** |

**Load order (narrative):**  
`tm-e5-firewall` (always) → `tm-session-report` (trunk) → `tm-regime-exposure` (narrate only) → `tm-signal-funnel` (when daily-eval exists; else N/A) + shared `trading/*` Keep skills.

**Apply ops:** `scripts/apply-to-hermes.sh` includes `RENEE_SKILLS` (mirrors `ELIZA_SKILLS`). Do not apply until owner runs the script.

---

## 1. Core trading skills

| Skill path | Status | Hermes role for Renee | Scrub / refine notes |
|------------|--------|----------------------|----------------------|
| `trading/technical-analysis` | **Keep** | 5-indicator scoring, bilingual T&M report sections, entry/SL/TP narration | Keep methodology + section language rules. Strip host paths, Telegram delivery ops, live pipeline IDs. Prefer pack truth over inventing levels. |
| `trading/stock-screener` | **Keep** | Universe screen + ranked picks with `score_breakdown` | Equities only; no ETFs. Soften hard-coded universe size to “T&M universe / Stage-2 tm pack”; no personal holdings. |
| `trading/market-regime` | **Keep** | Trending / ranging / choppy / volatile → threshold & size adjust | Keep regime logic summary. Scrub script host paths. Align daily Option G note with Helios (weekly = no Option G). |
| `trading/macro-filter` | **Keep** | Alice macro → confidence / size overlay (not hard gate) | Keep overlay semantics. No knowledge-base host paths or chat IDs. |
| `trading/risk-management` | **Keep** | Kelly / bracket sizing / drawdown caps / SL discipline | Keep rule tables as research guidance. Strip account numbers, live portfolio facts, broker links. |
| `trading/trade-journal` | **Keep** | Weekly bracket WR vs backtest; suggestion review | Scrub live CSV paths, share counts, GBP/USD fill examples, personal P&amp;L. Keep review *shape* only. |
| `trading/chart-generator` | **Optional** | Annotated charts for reports / Zoe verify | Scrub workspace absolute paths; keep chart types + dark-theme defaults as style notes. |
| `trading/breakout-scan-rules` | **Optional** | Stage-1 breakout / consolidation filter (Hermes pipeline) | Keep rule intent. Scrub ticker-count ops trivia; no holdings. Mark as Hermes-pipeline heritage — Helios Stage-1 may differ. |
| `trading/trade-journal-maintenance` | **Archive-ref** | Journal integrity / phantom SELL hygiene | **Do not** copy cron/job IDs, `<hermes-home>/...` paths, or sample fills into drafts. Ops-only; not narrative identity. |

---

## 2. Scoring / T&amp;M investment skills

| Skill path | Status | Hermes role for Renee | Scrub / refine notes |
|------------|--------|----------------------|----------------------|
| `investment/scoring-engine-v4.4` | **Keep** | Engine contract: continuous scores, DMI, regime ADX filter, Option 6 weights | Document as Renee scoring SSOT *for Hermes*. No host paths, cache file locations, or personal test runs. |
| `investment/scoring-engine-v4.2` | **Archive-ref** | Historical scoring notes | Prefer v4.4+; keep only if needed for WR citation lineage. |
| `investment/investment-indicator-optimization` | **Optional** | Tune indicator mappings via micro-sim | Methodology only; no live sweep job IDs. |
| `investment/backtest-methodology` | **Keep** | Walk-forward / bracket validation language | Keep how to cite WR correctly. Scrub home-dir plan paths and personal sweep schedules. |
| `investment/technical-screener` | **Optional** | Batch TA helpers (shared; often Alice-tagged) | Use only when supporting T&amp;M screens — not valuation. Scrub Alice workspace paths. |
| `investment/scoring-engine-audit-checklist` | **Out** | Zoe audit methodology | Renee responds to audits; does not own this skill. |
| `investment/request-eliza-valuation` | **Keep** (boundary) | Mid-session ask Eliza for DCF context | Keep “request pattern” without kanban env IDs / task UUIDs. Reminder: value pack stays separate; **E5 WARN** if overlap. |
| Host eval scripts (`scripts/host/`: `sleeve_paper_book`, `prediction_settler`, `tm_snapshot_verify`, `tm_variant`, `tm_volume_gate`, `vol_corr_size`, `pit_checklist`) | **Optional** | P0/P1 T&M eval overlays — Paper Book T, prediction settle, snapshot verify, variant shadow, volume gate, vol×corr size, PIT checklist | Documentation only; not a skills tree. Overlays are eval/narrative gates — do not change Option 6 weights or blend sleeves (**E5**). |

---

## 3. Support skills

| Skill path | Status | Hermes role for Renee | Scrub / refine notes |
|------------|--------|----------------------|----------------------|
| `investigation/moa-investigation` | **Optional** | MOA presets for trade-event / RCA panels | MOA infra ≠ Renee-owned; use when invited. No provider tokens. |

---

## 4. Archived Renee-tagged skills / `.archive` (reference only — not live identity)

| Archive skill | Status | Note |
|---------------|--------|------|
| `.archive/tm-exit-rules` | **Archive-ref** + **D-X8 align** | Historical T&amp;M exit *rules* prose. Helios alignment: Renee **proposes tm exit overlay** (D-X8) — **documentation only** in H-W1; not Hermes code change; daily fire remains script (D-X8b). |
| `.archive/renee-weekly-watchlist-gen` | **Archive-ref** | Legacy watchlist Track naming heritage. Scrub script paths. **≠** Eliza width **report Track A/B** chapters (Large+Mid vs Small Cap). Helios may treat watchlist as later car — do not invent Track tables. |
| `.archive/renee-atr14-entry-sl-tp` | **Archive-ref** | ATR14 entry/SL/TP formulas — methodology still useful when pack supplies `atr14` / levels. |
| `.archive/renee-data-integrity-hash` | **Out** / ops | Integrity hashing — scrub entirely from public drafts. |

---

## 5. Explicitly out of Renee ownership

| Area | Owner | Rule |
|------|-------|------|
| Valuation width / DCF / SEC / A-08 | Eliza · **P-VAL** | Never narrate as T&amp;M ranking |
| Value exit overlay propose | Eliza · **D-X8** | Symmetric to Renee’s **tm** overlay propose |
| Macro / environment integrate | Alice | Consume as overlay context only |
| IC challenge JSON | Zoe | Renee revises **daily + weekly** T&amp;M when challenged |
| Desk overall / market-close / deep-dive revise · **Macro view** · desk Risk-on/off | Alice | Alice cites Renee `## Market insight` + `## Session summary`; does **not** revise T&amp;M |
| Blended “one top list” from tm+value | — | **Forbidden** · **E5 = WARN only** · no mixing scores or checks (T&M indicators ≠ Eliza F/Z / FV) |
| ETF trade universe · intraday · broker | — | Hard no |
| VCP / CANSLIM into `tm_score` | — | Forbidden |

---

## 6. Task ↔ skill map (refined)

| Task class | Primary skills |
|------------|----------------|
| Daily T&amp;M narrative + **revise** (reviser=`renee`) | **`tm-session-report`**, **`tm-signal-funnel`** (when daily-eval; else N/A), **`tm-e5-firewall`**, `trading/technical-analysis`, `trading/market-regime`, `trading/macro-filter` |
| Weekly T&amp;M narrative + revise | **`tm-session-report`**, **`tm-e5-firewall`**, `trading/technical-analysis`, `trading/trade-journal`, `investment/backtest-methodology` |
| Portal deliver | Daily `inbox/daily-trend-momentum/*-report-revised.md`; weekly `inbox/weekly-trend-momentum/*-trend-momentum-report-revised.md` |
| `## Session summary` + `## Market insight` + News/Market + Lenses | **`tm-session-report`** — required near top (daily + weekly); no score rewrite; no desk Risk-on/off |
| § T&amp;M signal funnel | **`tm-signal-funnel`** — own cite when `scoring-eval/*-daily-eval.json` exists; else N/A + pending |
| E5 never-blend / BUY-WATCH contract | **`tm-e5-firewall`** — `tm_score`+`score_breakdown`; overlap WARN; callback anti-mix |
| Market-close T&amp;M session | **`tm-session-report`**, `trading/technical-analysis`, `trading/market-regime` — desk-pack session, not Alice-arm-only |
| Saturday T&amp;M self-review | **`tm-signal-funnel`** (Mon–Fri roll-up), `trading/trade-journal`, scoring notes |
| Screen / rank support | `trading/stock-screener`, `investment/scoring-engine-v4.4` + **`tm-e5-firewall`** |
| Risk / sizing language | `trading/risk-management` |
| D-X8 tm overlay propose (doc align) | `.archive/tm-exit-rules` (ref) + Helios EXIT-PLAN concepts · **no Hermes code in H-W1** |

---

## 7. Scrub checklist applied

- [x] No host / home paths (`<hermes-home>/...`, LAN hosts)
- [x] No cron / kanban / job instance IDs
- [x] No API keys, tokens, `.env`
- [x] No Telegram / chat IDs
- [x] No broker / account numbers or personal holdings / fills
- [x] No live MEMORY durable facts
- [x] E5 never-blend + P-TM ownership stated
- [x] D-X8 tm exit overlay called out as **docs alignment only**
- [x] Phase-3: Daily T&amp;M revise = Renee (not Alice); `## Session summary` + top movers; funnel cite owned by Renee
- [x] P0 profile skills tree + `RENEE_SKILLS` in apply script (owner apply separately)
- [ ] Short interest/FTD cite-only overlay (FINRA + SEC official; as-of; miss OK; never mutate `tm_score`/brackets/Option 6/BUY·WATCH) — extend `tm-session-report`/`tm-e5-firewall`; no new skill folder

**Model:** not pinned. Select in Hermes setup / `hermes model`.
