#!/usr/bin/env python3
"""Desk Pack weekly session prompts.

Sunday 12:00 UTC — **single** MAIN cron `desk-pack-weekly`, five portal cars:
  christina -> emily -> weekly T&M -> Eliza width -> Alice overall.

Aligns with daily W-D1 (rates before commodities so emily can cite same-day FX/rates).
Do **not** create separate 11:00 / 11:20 clocks (deleted 2026-09-20).
Width `valuation-width-weekly` and Alice `alice-weekly-deepdive` are paused once absorbed.
Does not touch live cron by itself — see patch_desk_pack_weekly_train.py.
"""
from __future__ import annotations

# Canonical desk-pack portal root (filesystem). Never ~/.hermes/shared/inbox/.
INBOX_ROOT = "$REPORTS_INBOX"

TRAIN_ID = "desk-pack-weekly"
# Historical split clocks — deleted from MAIN; do not recreate.
DELETED_COMMODITIES_ID = "commodities-weekly-legacy"
DELETED_RATES_ID = "rates-weekly-legacy"
# Back-compat aliases for older patcher/tests.
LEFTOVER_COMMODITIES_ID = DELETED_COMMODITIES_ID
LEFTOVER_RATES_ID = DELETED_RATES_ID

TRAIN_MARKER = "Sunday weekly Desk Pack train @ 12:00 UTC"
TRAIN_NAME = "Sarah: Sunday full Desk Pack (christina->emily->T&M->width->Alice)"
TRAIN_SCHEDULE = "0 12 * * 0"
WIDTH_ID = "valuation-width-weekly"
ALICE_ID = "alice-weekly-deepdive"
CAR4_HEAD = "## Car 4 — eliza valuation width"
CAR5_HEAD = "## Car 5 — Alice weekly overall"
PAUSE_REASON = (
    "absorbed into desk-pack-weekly full Desk Pack train; do not resume"
)

# Bump when Cars 1–2 contract text must refresh on already-reordered trains
# (rates DQ/FedWatch path AND/OR emily Keep-8 load AND/OR FX on all 8 weekly rows).
RATES_CONTRACT_MARKER = "christina-rates-contract:v6"
# Bump when Market insight/Macro view contract must refresh Car 3+ / FULL_TAIL.
MI_CONTRACT_MARKER = "market-insight-macro:v2"

MERCURY_DECIDE_ZOE_HOOK = (
 "**Mercury Decide( challenge )**: terminal "
    "`python3 ~/.hermes/scripts/mercury_decide.py --scope zoe --mode enforce "
    "--profile zoe --artifact ~/.hermes/shared/reports/zoe/<category>/<file> --telegram`"
 "(`--artifact` ** absolute** `~/.hermes/shared/reports/zoe/...` ; Telegram ). "
 "**ENFORCE · escalate-only**: Zoe Decide ****; ❌ REJECT. "
 "**Fail-open**: `DECIDE_UNAVAILABLE`/`MERCURY_DECIDE_MODE=off` -> Zoe . "
    "Ledger: `~/.hermes/shared/reports/mercury/zoe/<date>-<category>-<stem>.decide.json`. "
 "❌ `*-revised.md`. artifact `kanban_complete`. "
 "**Owner revise(parents=[zoe])**: Decide ledger `final_verdict`/`action`; "
 " `escalate->CONDITIONAL|REJECT` Zoe -> verdict revise; Fail-open/OFF -> Zoe. "
)

RATES_WEEKLY = f"""You are Sarah — Hermes desk operator. Desk Pack weekly — christina rates (depth). 
Not investment advice · observation only. Display "christina · rates". 
ISO week: `date -u +%G-W%V`( 2026-W38). 
({RATES_CONTRACT_MARKER})

1) kanban_create(christina). Mode=weekly depth. 
2) Load skills: curve-watch -> real-rates -> fedwatch-consume -> bond-etf-tape -> fx-us-uk-bridge -> rates-session-report(trunk). 
3) FedWatch: CONSUME-ONLY cron fedwatch-daily. Prefer `~/.hermes/shared/reports/alice/fedwatch/latest.json` then same-day `YYYY-MM-DD-fedwatch.json`. Cite-or-miss. ❌ hermes cron-run · ❌ invent probs. 
4) Pre-publish: DQ(Ccy/proxy≠cash/FX polarity/as-of)+ calendar fail-closed(miss ≠'')+ Est-after-FX(bond Est/Obs FX handoff). 
5) Draft: shared/reports/christina/YYYY-Www-rates-session.md. 
6) REQUIRED after Header: ## Session summary(5–8 bullets; rates_regime; Alice pull -> Market insight). rates_regime ≠ desk Risk-on/off. 
6b) REQUIRED: ## Market insight(; ❌ desk Risk-on/off ). 
7) Weekly: Gov+Other Est/Obs( miss ); FX (low–high miss); DXY+EURUSD+GBPUSD+USDJPY ; Obs FX_LONG/FX_SHORT(❌ HOLD TP); Session summary FX bullet; News/Market 2–3; Lenses + Dominant; Miss ledger. 
8) Zoe IC -> **christina** revise(owner only). B_*/FX_*. ❌ bare BUY/tm_score · ❌ C_*↔B_*↔FX_*. 
{MERCURY_DECIDE_ZOE_HOOK}
9) 3-layer final: workspace + shared + {INBOX_ROOT}/rates-session/YYYY-Www-rates-session-revised.md. ❌ `inbox/YYYY-Www-rates-session-revised.md`(inbox root). 
10) Hard fail miss/attempted , Alice overall miss. 
 task IDs. 
"""

COMMODITIES_WEEKLY = f"""You are Sarah — Hermes desk operator. Desk Pack weekly — emily commodities (depth). 
Not investment advice · observation only. Display "emily · commodities"(≠ broker Emily). 
ISO week: `date -u +%G-W%V`( 2026-W38). 

1) kanban_create(emily). Mode=weekly depth. 
2) Load: commodity-sources-crawl -> world-to-commodity -> commodity-insight -> commodity-direction -> commodity-forecast -> commodity-signal-table -> commodity-puzzle -> commodity-session-report(trunk). 
3) Draft: shared/reports/emily/YYYY-Www-commodities-session.md. 
4) REQUIRED after Header: ## Session summary(5–8 bullets + commodity_regime; Alice pull -> Market insight). commodity_regime ≠ desk Risk-on/off. 
4b) REQUIRED: ## Market insight(cite commodity-insight; ❌ desk Risk-on/off ). 
5) Weekly: News/Market check( Scenario/levels ): 2–3 Emily-topic + calendar(URL ≤12) `News: miss`; Lenses stub + Dominant(Macro/Micro/Market); Insight; Direction DIR_* ; Forecast Scenario±Est ****; History 1M/3M/1Y cite Forecast bull/base/bear(History ); Trade map C_* ; Basis cite Forecast+history finalize + Dominant tag(macro-led|micro-led|market-led|mixed); Obs levels; ; ≥3. Obs Obs TP cite Est band ; Est value band miss; ❌ History/trunk Scenario. Basis lean: base|bull|bear|two-way; DIR_* Conf↓ C_WAIT; Forecast. TP cite Est band -> levels miss C_WAIT/NO_SETUP. +Oil fuel footnotes(Soy/Wheat/Corn/Oil)cite-or-miss, miss. 
6) ❌ C_* Direction · ❌ DIR_* Signal · ❌ bare BUY · ❌ invent inventory/ARIMA Scenario. 
7) FX/rates: Car 1 rates -> cite Car1/ FX/rates; Car 1 miss -> miss OK. ❌ FX Est/B_*/Rate Δbp. 
8) Zoe -> **emily** revise(owner only). ❌ C_*↔B_*↔FX_* · ❌ bare BUY/tm_score. 
{MERCURY_DECIDE_ZOE_HOOK}
9) 3-layer: workspace + shared + {INBOX_ROOT}/commodities-session/YYYY-Www-*-revised.md. 
10) Hard fail miss/attempted, Alice overall miss. 
 task IDs. 
"""

TRAIN_PREFIX = f"""You are Sarah — Hermes desk operator. {TRAIN_MARKER}(serial cars). 
Not investment advice · observation only. Hard fail of one car -> miss/attempted, continue next car. E5: do not blend `tm_score`/`valuation_score`/`B_*`/`FX_*`/`C_*`. 
ISO week: `date -u +%G-W%V`. Sarah only kanban_create — analysis. 

## Car 1 — christina weekly rates
{RATES_WEEKLY.strip()}

Soft-wait `rates-session` at `{INBOX_ROOT}/rates-session/YYYY-Www-*-revised.md` **or** write miss/attempted. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. Then Car 2. Width=Car 4, Alice=Car 5. 

## Car 2 — emily weekly commodities
{COMMODITIES_WEEKLY.strip()}

Soft-wait `commodities-session` at `{INBOX_ROOT}/commodities-session/YYYY-Www-*-revised.md` **or** write miss/attempted. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. Then Car 3.
"""

# Injected into Car 3 (Renee weekly T&M) when MI contract missing — keep live weekly_report_gen body.
CAR3_MI_REQUIREMENTS = f"""
({MI_CONTRACT_MARKER} · Car 3)
REQUIRED after Header: ## Session summary(5–8 bullets; Alice pull -> Market insight). 
REQUIRED: ## Market insight + News/Market check + Lenses(T&M domain; ❌ desk Risk-on/off/Option G as-applied). 
"""

# Appended after Car 3. Width text matches the live 13:00 contract.
# Alice overall cites the four revised files; it does not re-open specialist cards.
FULL_TAIL = f"""Wait for inbox `weekly-trend-momentum` at `{INBOX_ROOT}/weekly-trend-momentum/YYYY-WW-*-revised.md` **or** write miss/attempted. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. Then Car 4.

{CAR4_HEAD}
You are Sarah — Hermes desk operator. Desk Pack weekly — Eliza valuation width(Car 4, T&M). 
Not investment advice · observation only. ISO week: `date -u +%G-W%V`. 
Sarah only kanban_create — analysis. 
({MI_CONTRACT_MARKER})

1. kanban_create(eliza, goal_mode=True) valuation width scan: 
 - valuation_width_scan.py: Tier 1 width / Tier 2 quality overlay / Tier 3 value trap
   - MUST run BOTH tracks A+B(default both-tracks / omit `--track`). ❌ `--track A` / `--track B` partial runs(W40 RCA: partial A-only -> false 'Track B 0 hits'). Live runner: `~/.hermes/profiles/eliza/scripts/valuation/valuation_width_scan.py`
 - published passer `valuation_score`(0–100, five-factor only)+ `width_verdict`. ❌ `tm_score`
 - published selected row markdown Spot(as_of),FV Range,Upside %( band, scan JSON/revise overlay, runner ). JSON `$fv_range` `+%` , FV `?`. -> Omissions `attempted + miss`. ❌ FV. ❌ full DCF. 
 - runner `composite_score`: revise `valuation_composite`, ×100 -> `valuation_score`; `adjusted_composite` -> 0–100 `quality_adjusted_score`
 - `valuation_score` ticker passer, Omissions
 - E5: T&M overlap -> WARN, width JSON `e5_overlap`. value T&M 
 - Draft workspace + shared(*-valuation-width-report.md + JSON). ❌ portal
   - REQUIRED after Header: ## Session summary(Alice pull -> Market insight)
   - REQUIRED: ## Market insight + News/Market check + Lenses(valuation domain; ❌ desk Risk-on/off)
2. Zoe challenge(parents=[draft], goal_mode=True). Zoe challenge, *revised.md. 
{MERCURY_DECIDE_ZOE_HOOK}
3. Eliza revise(parents=[zoe]): 
 - portal `YYYY-WW-valuation-width-revised.md`
 - `{INBOX_ROOT}/valuation-width/`. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/` · ❌ `shared/reports/eliza/inbox/`
 - revise FV/verdict/RevDCF, `*-valuation-width-revised.json`( `_revise` overlay) workspace + shared
   - sync: bash ~/.hermes/scripts/sync_reports_www.sh
4. Width revised miss , `bash ~/.hermes/scripts/validate_wow_diff.sh`(non-blocking, exit 0). Car 5. 
Hard fail -> miss/attempted, Car 5. 

Soft-wait `valuation-width` at `{INBOX_ROOT}/valuation-width/YYYY-WW-valuation-width-revised.md` **or** write miss/attempted. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. Then Car 5.

{CAR5_HEAD}
You are Sarah — Hermes desk operator. Desk Pack weekly — Alice overall(cite , specialist). 
Not investment advice · observation only. Phase 2(Saturday self-review). 
Sarah only kanban_create — analysis. Zoe overall . 

DATE_UTC=$(date -u +%Y-%m-%d)
WK=$(date -u +%V)
Revised : ${{DATE_UTC}}-W${{WK}}-weekly-deep-dive-revised.md
 ISO week. 

1) Soft-wait revised, miss. Canonical inbox root = `{INBOX_ROOT}/<category>/`. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. ❌ emily/christina/renee/eliza session : 
   - {INBOX_ROOT}/commodities-session/YYYY-Www-*-revised.md
   - {INBOX_ROOT}/rates-session/YYYY-Www-*-revised.md
   - {INBOX_ROOT}/weekly-trend-momentum/YYYY-WW-*-revised.md
   - {INBOX_ROOT}/valuation-width/YYYY-WW-valuation-width-revised.md
2) kanban_create(alice) overall. `skills/four-specialist-integrate` + `skills/alice-weekly-report`. : Header Alice `## Session summary`(5–8 bullets)-> News/social -> Four Market insights -> Four Session summaries -> **Macro view**(≈1 )-> Relationships -> desk Risk-on/off -> Gaps(≤4)-> Sources. 
 cite `## Market insight`()+ `## Session summary`. Relationships insight-anchored; desk Risk-on/off Alice only. 
 GICS 11 crash-indicator( cite, miss) Macro view , `##`. 
   E5 WARN only. ❌ blend `tm_score`/`valuation_score`/`B_*`/`FX_*`/`C_*`. 
 `tm_score` ≥90 : renee Four Session summaries, `miss`. ❌ `§3.3`. GC=F daily cache canonical. UNH valuation+weekly BUY aligned WATCH. 
 Draft (header ' Zoe '): alice workspace + shared/reports/alice/weekly-deep-dive/. ❌ portal. 
3) Zoe challenge(parents=[alice draft]). Zoe *revised.md. 
{MERCURY_DECIDE_ZOE_HOOK}
4) Alice revise: workspace + shared + ➡️ {INBOX_ROOT}/weekly-deep-dive/${{DATE_UTC}}-W${{WK}}-weekly-deep-dive-revised.md. 
   sync: bash ~/.hermes/scripts/sync_reports_www.sh
 task IDs. 
"""
