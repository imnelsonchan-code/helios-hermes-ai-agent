#!/usr/bin/env python3
"""Desk Pack daily — single Mon–Fri train on desk-pack-daily.

One Sarah cron @21:25 UTC:
  Wave1 parallel: christina rates || renee T&M
  Wave2 parallel: emily commodities || eliza value
  then Alice overall -> Zoe -> Alice revise (dual inbox)
  then terminal daily_tm_with_exits.sh (Telegram via hermes send · Option A).

Absorbed clocks (pause, do not resume):
  rates-daily-legacy · tm-daily-legacy · commodities-daily-legacy · value-daily-legacy · exit-digest-legacy
  (2026-10-08 cleanup: rates-daily-legacy / commodities-daily-legacy / value-daily-legacy / exit-digest-legacy
   deleted user-authorized; only tm-daily-legacy remains paused; absent ids tolerated.)

Does not touch live cron by itself — see patch_desk_pack_daily_train.py.
FedWatch fetch fedwatch-daily and social watcher stay independent.
"""
from __future__ import annotations

# Canonical desk-pack portal root (filesystem). Never ~/.hermes/shared/inbox/.
INBOX_ROOT = "$REPORTS_INBOX"

TRAIN_ID = "desk-pack-daily"
TRAIN_MARKER = "Desk Pack W-D1 daily train @ 21:25 UTC"
TRAIN_NAME = "Sarah: Mon–Fri full Desk Pack (W1||W2 -> Alice -> T&M+exit)"
TRAIN_SCHEDULE = "25 21 * * 1-5"

RATES_ID = "rates-daily-legacy"
TM_ID = "tm-daily-legacy"
COMMODITIES_ID = "commodities-daily-legacy"
VALUE_ID = "value-daily-legacy"
EXIT_ID = "exit-digest-legacy"
ABSORBED_IDS = (RATES_ID, TM_ID, COMMODITIES_ID, VALUE_ID, EXIT_ID)

WAVE1_HEAD = "## Wave 1 — parallel rates || T&M"
WAVE2_HEAD = "## Wave 2 — parallel commodities || value"
ALICE_HEAD = "## Alice overall — market-close + daily-social"
EXIT_HEAD = "## Post — T&M signal + exit overlay"

PAUSE_REASON = (
    "absorbed into desk-pack-daily full Desk Pack daily train; do not resume"
)

FEDWATCH_ID = "fedwatch-daily"

# Bump when daily rates contract text must refresh on already-patched trains
# (FX on all 8 rows; range does not consume the full-Obs slot).
# v3 (2026-10-08): M1/M2/M3 gate hardening — FedWatch three-source divergence presentation,
# FX bullet mandatory in Session summary, News outlet + full URL + date.
DAILY_RATES_CONTRACT_MARKER = "christina-daily-rates-contract:v3"

# Sarah owns draft->Zoe->revise; workers must not spawn Zoe/revise children
# (mega-card + child Zoe caused Wave1 circular deadlock -> Wave2 skip 2026-10-01).
SARAH_CHAIN_MARKER = "desk-pack-sarah-chain:v1"
WAVE2_CONTINUE_MARKER = "wave2-continue-on-wave1-stuck:v1"
NO_EARLY_EXIT_MARKER = "desk-pack-no-early-exit:v1"
COMPLETION_GATE_MARKER = "desk_pack_daily_completion_gate.py"

CHAIN_RULE = f"""({SARAH_CHAIN_MARKER})Sarah **three cards**: W* Draft(draft-only)-> Zoe(parents=[draft_id])-> owner revise(parents=[zoe_id]). 
Draft worker draft/3-layer draft paths `kanban_complete` — ❌ draft/revise worker `kanban_create` Zoe/revise children(circular parents ). 
"""

# After Zoe saves challenge artifact — Mercury Decide ENFORCE (escalate-only).
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

# --- Leg bodies (same contracts as prior split clocks) ---

RATES_DAILY = f"""### Leg rates(christina)
{CHAIN_RULE}Titles: `W1 Draft: christina · rates (${{DATE_UTC}})` -> `W1 Zoe: rates (${{DATE_UTC}})` -> `W1 Revise: christina rates (${{DATE_UTC}})`. 
Mode=daily lite. Display "christina · rates". Not investment advice · observation only. 
({DAILY_RATES_CONTRACT_MARKER})
**Draft card body only**(assignee=christina, goal_mode=True): 
1) Load skills: curve-watch -> real-rates -> fedwatch-consume -> bond-etf-tape -> fx-us-uk-bridge -> rates-session-report(trunk). 
2) FedWatch: CONSUME-ONLY cron fedwatch-daily. `~/.hermes/shared/reports/alice/fedwatch/latest.json` `cross_check.citation`(latest.json only; 2b). ❌ Polymarket/predictmarketcap FW . ❌ hermes cron-run · ❌ re-fetch · ❌ invent probs. FX Obs Signal; `B_WAIT`/`FX_WAIT` Daily Obs . 
2b) **FedWatch three-source divergence( gate)**: read `cross_check.citation` from latest.json only. `miss`,missing key,a_primary hike probability at 0% or 100%,or calibration `range_pct` outside 0–100 -> the whole ## FedWatch section is `miss` plus `degenerate_zq_sole_source`. Do not quote that probability. `primary_only`(reason `sentiment_miss`)-> quote a_primary only when it is not 0% or 100%; c_sentiment cell is `miss`. `b_backup_zq` is the same ZQ=F instrument and is not a second source. Copy `c_sentiment` only when citation is `ok` and `freshness.layers.c_sentiment` is fresh and the value is not 0 or 100; otherwise that cell is miss. There is no news layer, so the news cell is miss. Do not cron-run, re-fetch, or invent a number. regime/B_*/FX_* basis (××), ❌ quote a degenerate probability. 
3) Pre-publish: DQ(Ccy/proxy≠cash/FX polarity/as-of)+ calendar fail-closed + Est-after-FX. 
4) Draft: shared/reports/christina/YYYY-MM-DD-rates-session.md. 
5) REQUIRED after Header: ## Session summary(5–8 bullets; rates_regime; Alice pull -> Market insight). rates_regime ≠ desk Risk-on/off. 
5b) REQUIRED: ## Market insight(; ❌ desk Risk-on/off ). 
6) Daily: bond Obs ≤3; FX (low–high miss; Obs ); Obs ≤2( DXY, GBPUSD; FX_LONG/FX_SHORT); **Session summary `FX ranges:` bullet( gate · M2; / bullets )**; News ≥1: **outlet+full URL(; ❌ )+date**(, ❌ ; `News: miss`); Miss ledger. 
7) 3-layer **draft only** -> `kanban_complete`. ❌ Zoe/revise. 
7b) **Pre-complete ( `terminal`; complete)**: ① ## FedWatch `miss`, key,a_primary hike probability 0% 100%, `range_pct` 0–100 -> `miss`+`degenerate_zq_sole_source`(❌ quote probability); ② Session summary 'FX '; ③ News full URL(`https?://` )+date. 
**Zoe card**(assignee=zoe, parents=[draft_id], goal_mode=True): IC -> shared/reports/zoe/rates-session/. *-revised.md. 
{MERCURY_DECIDE_ZOE_HOOK}
**Revise card**(assignee=christina, parents=[zoe_id]): owner only; Zoe B/M/m(); B_*/FX_*(); ❌ FedWatch / FX Est/Rate Δbp; Major [ `degenerate_zq_sole_source`/quote 0% 100% a_primary/FX bullet /News URL-date ] -> 2b + Sources. 
3-layer final — paste these three lines verbatim into the revise card:
save: ✅ ~/.hermes/profiles/christina/workspace/rates-session/${{DATE_UTC}}-rates-session-revised.md
save: ✅ ~/.hermes/shared/reports/christina/rates-session/${{DATE_UTC}}-rates-session-revised.md
➡️ {INBOX_ROOT}/rates-session/${{DATE_UTC}}-rates-session-revised.md
❌ {INBOX_ROOT}/${{DATE_UTC}}-rates-session-revised.md
`test -f` the portal path before kanban_complete.
Hard fail miss/attempted , Alice overall miss. 
"""

TM_DAILY = f"""### Leg T&M(renee)
{CHAIN_RULE}Titles: `W1 Draft: renee · T&M (${{DATE_UTC}})` -> `W1 Zoe: T&M (${{DATE_UTC}})` -> `W1 Revise: renee T&M (${{DATE_UTC}})`. 
**Draft card body only**(assignee=renee, goal_mode=True): 
1) ~/.hermes/hermes-agent/venv/bin/python3 daily_trend_momentum.py
1b) Load skills: tm-e5-firewall -> tm-session-report ->(scoring-eval/*-daily-eval.json )tm-signal-funnel. Daily Option G OK(SPY ADX <25 BUY, ). Eval § funnel ## Lenses ,ranking ; N/A + pending. . 
2) REQUIRED after Header: `## Session summary`(5–8 bullets; Alice pull -> THIS file Market insight). Generator G1; revise . ❌ ' `## Market insight`' Tracker . ❌ `No formal market-insight brief today` when the section exists. Alice macro brief miss -> Lenses Macro(`No brief.` / `miss`), NOT Alice pull. 
2b) REQUIRED: `## Market insight` + News/Market check + Lenses(T&M domain; ❌ desk Risk-on/off). ranking News `News: miss` -> REJECT. 
3) 3-layer **draft only**: 
save: ✅ ~/.hermes/profiles/renee/workspace/daily-trend-momentum/<date>-report.md
save: ✅ ~/.hermes/shared/reports/renee/daily-trend-momentum/<date>-report.md
4) `kanban_complete` draft — ❌ `kanban_create` Zoe/revise(circular parents ). 
**Zoe card**(assignee=zoe, parents=[draft_id]): IC Vote + English rationale -> shared/reports/zoe/daily-trend-momentum/<date>-challenge.md
{MERCURY_DECIDE_ZOE_HOOK}
**Renee revise**(assignee=renee, parents=[zoe_id])— ❌ do not hand off to Alice; **** `tm_score`/brackets/ranking. Final portal `*-report-revised.md`: 
save: ✅ ~/.hermes/profiles/renee/workspace/daily-trend-momentum/<date>-report-revised.md
save: ✅ ~/.hermes/shared/reports/renee/daily-trend-momentum/<date>-report-revised.md
➡️ {INBOX_ROOT}/daily-trend-momentum/<date>-report-revised.md
"""

COMMODITIES_DAILY = f"""### Leg commodities(emily)
{CHAIN_RULE}Titles: `W2 Draft: emily · commodities (${{DATE_UTC}})` -> `W2 Zoe: commodities (${{DATE_UTC}})` -> `W2 Revise: emily commodities (${{DATE_UTC}})`. 
Mode=daily lite. Display "emily · commodities"(≠ broker Emily). Not investment advice · observation only. 
**Draft card body only**(assignee=emily, goal_mode=True): 
1) Load: commodity-sources-crawl -> world-to-commodity -> commodity-insight -> commodity-direction -> commodity-forecast -> commodity-signal-table -> commodity-puzzle -> commodity-session-report(trunk). 
2) Draft: shared/reports/emily/YYYY-MM-DD-commodity-session.md( commodities-session ). 
3) REQUIRED after Header: ## Session summary(5–8 bullets + commodity_regime; Alice pull -> Market insight). commodity_regime ≠ desk Risk-on/off. 
3b) REQUIRED: ## Market insight(cite commodity-insight; ❌ desk Risk-on/off ). 
4) Cite slots: Insight · Direction(DIR_*)· Forecast( · 1–4w · bull|base|bear ± Est band; miss, ; skip). News/Market check( Scenario/levels ): ≥1 Emily-topic `News: miss`. Lenses(Macro+Micro; Market ; Dominant). 
5) Daily: + Trade map C_*; Obs ≤3 Obs entry/cut/TP, Obs TP cite Est band ; levels -> Basis cite Forecast + Dominant tag(macro-led|micro-led|market-led|mixed); Forecast/Est cite -> Obs levels. levels Basis lean: base|bull|bear|two-way. 3–5; ≥3 . 
6) ❌ C_* Direction · ❌ DIR_* Signal · ❌ bare BUY · ❌ invent inventory/ARIMA Scenario. 
- Precious 1D%(): Gold/Silver DIR_* may cite only a 1D% from GLD or GC=F previous close(silver: SLV or SI=F). gold-api XAU/XAG spot is US Last only. Missing that previous close -> that row is miss. Cite Gold/Silver table row note(`1D% src: GLD prev close`). 
- Oil(): UK/EU stays BZ=F. Any BZ=F or CL–BZ sentence must, on that same line, say ICE Brent financial futures (may diverge from ICE settlement), and that CL and BZ are the same pull and same as-of(`same-source`). Missing a leg or a different source -> that spread sentence is miss. 
7) FX/rates: require SAME-SESSION Wave1 `{INBOX_ROOT}/rates-session/*-revised.md` or miss. ❌ T-1/yesterday `shared/reports/christina` lock live cite(= miss). ❌ FX Est/B_*/Rate Δbp. 
8) 3-layer **draft only** -> `kanban_complete`. ❌ Zoe/revise. 
**Zoe card**(assignee=zoe, parents=[draft_id])-> **emily revise**(assignee=emily, parents=[zoe_id]; owner only). ❌ C_*↔B_*↔FX_*. 
{MERCURY_DECIDE_ZOE_HOOK}
3-layer final(basename: workspace/shared = `commodity-session-revised.md`; portal = plural `commodities-session-revised.md`): 
save: ✅ ~/.hermes/profiles/emily/workspace/commodities-session/YYYY-MM-DD-commodity-session-revised.md
save: ✅ ~/.hermes/shared/reports/emily/commodities-session/YYYY-MM-DD-commodity-session-revised.md
➡️ {INBOX_ROOT}/commodities-session/YYYY-MM-DD-commodities-session-revised.md
`test -f` the portal revised file before complete. `kanban_complete` `python3 ~/.hermes/scripts/validate_price_source_direction_gate.py <draft path>`; exit status 0 -> ❌ kanban_complete. If revise landed only on draft `YYYY-MM-DD-commodity-session.md` -> run `python3 ~/.hermes/scripts/desk_pack_revised_gate.py`(promotes post-challenge draft only). ❌ do not kanban_complete if you only patched YYYY-MM-DD-commodity-session.md. 
Hard fail -> miss/attempted, . 
"""

VALUE_DAILY = f"""### Leg value(eliza)
{CHAIN_RULE}Titles: `W2 Draft: eliza · value (${{DATE_UTC}})` -> `W2 Zoe: value (${{DATE_UTC}})` -> `W2 Revise: eliza value (${{DATE_UTC}})`. 
Desk pack #4 value-session. Not investment advice. P-VAL only — ❌ tm_score/T&M brackets. 
**Draft card body only**(assignee=eliza, goal_mode=True): 
1) value-sleeve data snapshot + movers vs Sunday lock. Sunday valuation_score; ; reshuffle weekly value-100. 
1b) Wave2: cite same-session Wave1 portal miss — ❌ Wave1 rates/T&M . 
2) REQUIRED after Header: ## Session summary(5–8 bullets + valuation stance; Alice pull -> **THIS file** Market insight). Forbidden: 'No formal market-insight brief today'when the section exists. 
2b) REQUIRED: ## Market insight + News/Market + Lenses(valuation domain; ❌ desk Risk-on/off/tm_score). Movers Sunday `valuation_score` skip + `attempted + miss`. Movers : Today spot / %,Sunday lock FV( revised JSON `fv_range` ),Display upside %(= FV / spot − 1). FV spot -> `attempted + miss`. ❌ FV. ❌ upside `valuation_score`/`width_verdict`/. 
3) 3-layer **draft only** -> `kanban_complete`. ❌ Zoe/revise. Eliza draft . 
**Zoe card**(assignee=zoe, parents=[draft_id])-> **eliza revise**(assignee=eliza, parents=[zoe_id]; owner only)— ❌ do not hand off to Alice value revise. 
{MERCURY_DECIDE_ZOE_HOOK}
3-layer final: workspace + shared + {INBOX_ROOT}/value-session/YYYY-MM-DD-*-revised.md. 
E5: overlap ticker WARN only. Hard fail -> miss/attempted, . 
"""

ALICE_OVERALL = f"""You are Sarah — Hermes desk operator. Desk Pack W-D1 Alice overall( train). 
Not investment advice. E5++: do not blend `tm_score`/`valuation_score`/`B_*`/`FX_*`/`C_*`. 
Sarah only kanban_create — analysis. Zoe overall . 
❌ christina/renee/emily/eliza session . 

### Soft barrier( specialist draft)
Canonical inbox root = `{INBOX_ROOT}/<category>/`. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`( `inbox/...` miss). 
 `*-revised.md` **** `miss`: 
- `{INBOX_ROOT}/rates-session/`(christina)
- `{INBOX_ROOT}/daily-trend-momentum/`(renee)
- `{INBOX_ROOT}/commodities-session/`(emily)
- `{INBOX_ROOT}/value-session/`(eliza)
 -> miss; overall . 
Four-path `ok | miss | pending-rechallenge`. Zoe ran ≠ PASS -> `pending-rechallenge`, ❌ `ok`/`✅`. ❌ owner `5/5 `. T-1/ insight -> `miss` `as-of T-1 + gap`, live cite. Daily Relationships ≤2–4 (). callback material_gap. 

### Step 1 — Alice overall draft(goal_mode=True)
kanban_create(alice). : 
- `skills/four-specialist-integrate`(section order/Relationships/desk Risk-on/off/callback budgets)
- `skills/market-close-news-social`(news/social/Sources = D)
- `skills/market-close-report-format`(: §4 `##`; Integration Template )

: Header · Alice `## Session summary`(Header 5–8 bullets)· News/social/macro · Four Market insights cites(or miss)· four `## Session summary` cites(or miss)· **Macro view**(daily 8–15 )· Relationships(≤2–4 SENTENCES; insight-anchored; ❌ daily weekly-style table)· desk Risk-on/off · `## Gaps / callbacks` · Sources. 
Four-path status = `ok` | `miss` | `pending-rechallenge`. `ok` = same-day portal revised **AND** Zoe PASS/no re-challenge. Stale/unre-challenged/T-1 lock -> `miss` `as-of T-1 + gap` — live 3–5 bullets. ❌ `✅` ≠ Zoe PASS. ❌ owner self-claim `5/5 `/PASS — Zoe re-votes. 
Daily callback ≤1 `material_gap: true`, **must** target the train-blocking gap(unre-challenged/T-1 lock/missing same-day Wave1)— ❌ 5bp side issue if a P0 gap exists. cite-only `{INBOX_ROOT}/social-watch/*-snapshot.md`; Top-20/Reddit/StockTwits. 
Macro/desk regime / — . 
3-layer draft( portal): 
save: ✅ ~/.hermes/profiles/alice/workspace/reports/daily-social/<date>-summary.md
save: ✅ ~/.hermes/shared/reports/alice/daily-social/<date>-summary.md
(market-close draft format skill)

### Step 2 — Zoe IC gate(parent=alice_overall_id)
Zoe challenge -> shared/reports/zoe/daily-social/. *-revised.md. Step 1. 
{MERCURY_DECIDE_ZOE_HOOK}

### Step 3 — Alice revise(parent=zoe_id)
Reviser = **alice only**. Deliver dual portal(❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`): 
➡️ {INBOX_ROOT}/market-close/<date>*-summary-revised.md
➡️ {INBOX_ROOT}/daily-social/<date>*-summary-revised.md
python3 ~/.hermes/scripts/four_path_auto_derive_gate.py --report {INBOX_ROOT}/market-close/${{DATE_UTC}}-summary-revised.md --date "${{DATE_UTC}}"
daily-social bytes market-close (same bytes -> ): 
python3 ~/.hermes/scripts/four_path_auto_derive_gate.py --report {INBOX_ROOT}/daily-social/${{DATE_UTC}}-summary-revised.md --date "${{DATE_UTC}}"
exit 1 -> ❌ sync_reports_www.sh. 
exit 0 terminal: bash ~/.hermes/scripts/sync_reports_www.sh

## Social cite-only + news analysis
Integrate `{INBOX_ROOT}/social-watch/{{date}}*-snapshot.md`: ticker/ -> ' vs '; pointer; -> N/A. close Top-20/Reddit/StockTwits. Macro arm / regime, . : (5–10 ledger + Alice themes/bull-bear)+ Sources(outlet/date/URL/grade; miss attempted+miss). : social-watch snapshot; wrap Top-20/Reddit/StockTwits. Zoe: cite snapshot ; outlet/Sources; headlines-only Alice -> challenge; social-watch. 
"""

EXIT_STEP = """Sarah terminal only( agent ): 
bash ~/.hermes/scripts/daily_tm_with_exits.sh
- Wrapper: T&M BUY digest + `exit_signal_checker.py --dry-run`(score decay <50)
- Telegram: `hermes send`(Option A)— Desk Pack cron deliver=local
- ❌ `--mfe-json`(time-stop 23:00 position_watch)
- ❌ trade_journal · · SL/TP
- Hard fail -> miss/attempted, **** inbox; overall 
"""

TRAIN_PROMPT = f"""You are Sarah — Hermes desk operator. {TRAIN_MARKER}(Wave1|| -> Wave2|| -> Alice -> T&M+exit). 
Not investment advice · observation only. Sarah only kanban_create — analysis. 
Hard fail of one leg -> miss/attempted, continue. E5: do not blend `tm_score`/`valuation_score`/`B_*`/`FX_*`/`C_*`. 
DATE_UTC=$(date -u +%Y-%m-%d). 
{SARAH_CHAIN_MARKER}: Sarah draft->Zoe->revise three cards; worker ❌ spawn Zoe/revise children. 
{WAVE2_CONTINUE_MARKER}: Wave1 (circular parents/blocked child/judge reject loop)-> miss/attempted, **still open Wave 2**. ❌ cron session unblock . 
{NO_EARLY_EXIT_MARKER}: cron session **** soft-wait(terminal poll) portal `*-revised.md` **** miss/attempted, `desk_pack_revised_gate.py` -> Alice overall -> sync_reports_www -> daily_tm_with_exits. ❌ end turn after fan-out only; ❌ ''/'will check in a later round'/promise later round. Blocked revise(e.g. agent crash)-> mark miss/attempted **CONTINUE**(do not exit). Soft-wait: `~/.hermes/shared/reports` `*-revised.md` inbox portal -> `cp` `{INBOX_ROOT}/rates-session/`,`{INBOX_ROOT}/daily-trend-momentum/`,`{INBOX_ROOT}/commodities-session/`,`{INBOX_ROOT}/value-session/`(basename ). ❌ `cp` inbox root `{INBOX_ROOT}/`. 

{WAVE1_HEAD}
Create **both** Wave1 legs in parallel(no parents= between rates and T&M). : Sarah **three cards** draft-only -> Zoe -> owner revise -> portal. 

{RATES_DAILY.strip()}

{TM_DAILY.strip()}

Soft-wait `{INBOX_ROOT}/rates-session/${{DATE_UTC}}*-revised.md` **and** `{INBOX_ROOT}/daily-trend-momentum/${{DATE_UTC}}*-revised.md` **or** miss/attempted per leg. 
❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/*/inbox/`. 
Shared `*-revised.md`,inbox -> `cp` category (basename ): `{INBOX_ROOT}/rates-session/`,`{INBOX_ROOT}/daily-trend-momentum/`,`{INBOX_ROOT}/commodities-session/`,`{INBOX_ROOT}/value-session/`. ❌ `cp` inbox root `{INBOX_ROOT}/`. 
 stuck/circular/waiting on child/blocked revise -> miss/attempted, ** Wave 2**( unblock · end turn). Then Wave 2.

{WAVE2_HEAD}
Create **both** Wave2 legs in parallel(no parents= between commodities and value). : Sarah **three cards** draft-only -> Zoe -> owner revise -> portal. 
Wave2 notes: cite same-session Wave1 portal miss — ❌ Wave1 FX Est/B_*/Rate Δbp/T&M . Zoe ran ≠ PASS -> re-challenge before four-path ok. 

{COMMODITIES_DAILY.strip()}

{VALUE_DAILY.strip()}

Soft-wait(terminal poll)all four session `*-revised.md` under `{INBOX_ROOT}/rates-session/`,`{INBOX_ROOT}/daily-trend-momentum/`,`{INBOX_ROOT}/commodities-session/`,`{INBOX_ROOT}/value-session/` **or** miss/attempted per leg — ❌ 'will check in a later round'. Shared revised,inbox -> `cp` category (basename ): `{INBOX_ROOT}/rates-session/`,`{INBOX_ROOT}/daily-trend-momentum/`,`{INBOX_ROOT}/commodities-session/`,`{INBOX_ROOT}/value-session/`. ❌ `cp` inbox root `{INBOX_ROOT}/`. Then run `python3 ~/.hermes/scripts/desk_pack_revised_gate.py` before Alice overall: exit 0 = commodities revised present or promoted from a post-challenge draft; exit 2 = true miss — do not rename an unreviewed draft. Then Alice overall.

{ALICE_HEAD}
{ALICE_OVERALL.strip()}

After Alice revise + sync_reports_www.sh, Post step( specialist). 

{EXIT_HEAD}
{EXIT_STEP.strip()}

Before final text response: MUST run `python3 ~/.hermes/scripts/{COMPLETION_GATE_MARKER}` — **exit 0 required** before final reply. exit≠0 -> keep working(soft-wait/Alice/sync/exit). Only after soft-wait + Alice attempted and gate still ≠0 may end with brief TRAIN_INCOMPLETE.
 task IDs + exit wrapper (ok/miss). 
"""
