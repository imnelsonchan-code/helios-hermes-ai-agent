#!/usr/bin/env python3
"""Saturday self-review Phase 2 — Option A serial @12:00 on saturday-self-review.

Serial chain (one-by-one, Sunday-style parents=):
  emily -> christina -> renee -> eliza -> alice self -> zoe self
  -> Alice integrate -> Mercury Decide ENFORCE -> spawn APPROVE
  -> Zoe R1 -> Alice revise

Christina/emily at **same audit depth** as renee/eliza (Part A/B/C).
Portal light = Alice revise only: inbox/weekly-performance/*-revised.md.
Specialist legs = workspace + shared only — NOT rates-session / commodities-session.

Does not touch live cron by itself — see patch_saturday_self_review.py.
"""
from __future__ import annotations

JOB_ID = "saturday-self-review"
JOB_MARKER = "Saturday Self-Review Phase · Option A (6 serial @12:00)"
JOB_NAME = "Sarah: Saturday self-review (Phase 2)"
JOB_SCHEDULE = "0 12 * * 6"

# Desk-pack order then process arms (serial).
SERIAL_ASSIGNEES = (
    "emily",
    "christina",
    "renee",
    "eliza",
    "alice",
    "zoe",
)

# Back-compat alias used by older tests / docs snippets.
PARALLEL_ASSIGNEES = SERIAL_ASSIGNEES

STEP1_HEAD = "Step 1–6 — (6 cards, one-by-one · parents= chain)"
INTEGRATE_HEAD = "Step 7 — Alice integrate(depends on t6)"
DECIDE_HEAD = "Step 7b — Mercury Decide ENFORCE(depends on t7)"
SPAWN_HEAD = "Step 7c — Alice spawn APPROVE topics(depends on t8)"
ZOE_HEAD = "Step 8 — Zoe challenge Round 1(depends on Step 7c / t9)"
REVISE_HEAD = "Step 9 — Alice revise after Zoe R1(depends on Step 8 / t10)"

SELF_REVIEW_PATHS = (
    "shared/reports/emily/self-review/YYYY-Www-emily-review.md",
    "shared/reports/christina/self-review/YYYY-Www-christina-review.md",
    "shared/reports/renee/self-review/YYYY-Www-renee-review.md",
    "shared/reports/eliza/self-review/YYYY-Www-eliza-review.md",
    "shared/reports/alice/weekly-performance-review/YYYY-Www-alice-review.md",
    "shared/reports/zoe/weekly-self-review/YYYY-Www-zoe-review.md",
)

PORTAL_REVISED = (
    "$REPORTS_INBOX/weekly-performance/"
    "YYYY-Www-phase2-summary-revised.md"
)

FORBIDDEN_SAT_INBOX = (
    "inbox/rates-session",
    "inbox/commodities-session",
)

EMILY_CARD = """  1) kanban_create(assignee="emily", skills=["commodity-sources-crawl", "world-to-commodity", "commodity-insight", "commodity-direction", "commodity-forecast", "commodity-signal-table", "commodity-puzzle", "commodity-session-report", "commodity-obs-backtest"],
     title="Emily: weekly commodities data + self-review",
     body="Display "emily · commodities"(≠ broker Emily/M7). Not investment advice · observation only. 
Same audit depth as Renee/Eliza(commodities sleeve). ≠ rewrite full ten-column session; ❌ inbox/commodities-session Sat portal. 
Load SSOT(Keep 8): commodity-sources-crawl -> world-to-commodity -> commodity-insight -> commodity-direction -> commodity-forecast -> commodity-signal-table -> commodity-puzzle -> commodity-session-report(+ Eval/Sat commodity-obs-backtest). 

Part A — Week artifact roll-up
- List this fire-Saturday ISO week's Mon–Fri `inbox/commodities-session/*-revised.md`(same token; 2026-10-19..23 = 2026-W43)(or shared draft if revise miss)
- Each file: `## Session summary` + `commodity_regime` present? commodity_regime ≠ desk Risk-on/off
- World->commodity · Insight · Direction(DIR_*)· Forecast chapters present or miss?
- News/Lenses chapters present or explicit miss?

Part B — Signal & hygiene health(cite published only)
- dual-venue tape completeness; C_* naming; ❌ C_* Direction · ❌ DIR_* Signal; Obs entry/SL/TP budget(Daily≤3 full levels; Basis cite Forecast)
- Puzzle blocks ≥3 hygiene; Miss ledger
- Signal/Obs vs later Last(narrative cite-only; ❌ invent commodity_hit_rate)
- Shadow keys if present: commodity_signal/shadow_commodity_score/commodity_signal_breakdown — else N/A
- Post-crawl QA: ticker SSOT · XAG-USD ban · GBp · proxy≠futures≠LSE · LSE zero->miss · as-of(failures -> Miss ledger only; ❌ invent backfill)
- Term/COT gates: term structure cite-or-miss; COT crowdedness cite-or-miss; ❌ COT C_*/Est
- Paid-source zero tolerance: ❌ OilPriceAPI/LSEG/Bloomberg/FactSet/ICE paid 
- NEVER invent C_*/inventory/ARIMA Scenario; NEVER blend C_*↔B_*↔FX_*/tm_score/valuation_score
- ≠ broker Emily/orders/M7 · ❌ bare BUY · ❌ PnL

Part C — Self-Review + Toolchain
- Which commodity signals/regime/DIR_* calls worked or missed(cite published only)
- Zoe challenge acceptance rate for commodities sessions this week
- May run `commodity-obs-backtest` -> `shared/reports/emily/self-review/YYYY-Www-emily-obs-backtest.md`(observation only; ❌ PnL/orders)
- Toolchain Audit:
  - [Add] any new data sources or skills needed
  - [Upgrade] existing tools with better alternatives
  - [Retire] error-prone or obsolete scripts

save:
[OK] ~/.hermes/profiles/emily/workspace/reports/self-review/YYYY-Www-emily-review.md
[OK] ~/.hermes/shared/reports/emily/self-review/YYYY-Www-emily-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-emily-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Emily commodities self-review" --ticker BROAD --type self-review --profile emily --path shared/reports/emily/self-review/YYYY-Www-emily-review.md --date YYYY-MM-DD
")
  Capture ID as t1. Hard-fail -> miss/attempted; chain continues.
"""

CHRISTINA_CARD = """  2) kanban_create(assignee="christina", skills=["curve-watch", "real-rates", "fedwatch-consume", "bond-etf-tape", "fx-us-uk-bridge", "rates-session-report"],
     title="Christina: weekly rates data + self-review",
     body="Display "christina · rates". Not investment advice · observation only. 
Same audit depth as Renee/Eliza(rates sleeve). ≠ rewrite full rates-session; ❌ inbox/rates-session Jobs light. 

Part A — Week artifact roll-up
- List this fire-Saturday ISO week's Mon–Fri `inbox/rates-session/*-revised.md`(same token; 2026-10-19..23 = 2026-W43)(or shared draft if revise miss)
- Each file: `## Session summary` present? FedWatch cite-or-miss discipline?
- ❌ hermes cron-run FedWatch; ❌ invent FedWatch probs

Part B — Signal & hygiene health(cite published only)
- B_*/FX_* naming + Obs budget + Miss ledger + Ccy hygiene
- Rate scenario Δbp vs later Last(narrative cite-only; ❌ invent rates_hit_rate)
- Shadow keys if present: rates_signal/shadow_rates_score/rates_signal_breakdown — else N/A
- NEVER invent B_*/FX_*; NEVER blend with tm_score/valuation_score/C_*
- NEVER touch FedWatch cron fedwatch-daily

Part C — Self-Review + Toolchain
- Which curve/real-rate/FX calls worked or missed(cite published Est/Obs/Last only)
- Zoe challenge acceptance rate for rates sessions this week
- Toolchain Audit:
  - [Add] any new data sources or skills needed
  - [Upgrade] existing tools with better alternatives
  - [Retire] error-prone or obsolete scripts

save:
[OK] ~/.hermes/profiles/christina/workspace/reports/self-review/YYYY-Www-christina-review.md
[OK] ~/.hermes/shared/reports/christina/self-review/YYYY-Www-christina-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-christina-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Christina rates self-review" --ticker BROAD --type self-review --profile christina --path shared/reports/christina/self-review/YYYY-Www-christina-review.md --date YYYY-MM-DD
", parents=[t1])
  Capture ID as t2. Hard-fail -> miss/attempted; chain continues.
"""

RENEE_CARD = """  3) kanban_create(assignee="renee", skills=["technical-analysis", "trade-journal", "chart-generator", "backtest-methodology", "stock-screener"],
     title="Renee: weekly data update + self-review",
     body="Part A — Weekly Indicator Update
Run: python3 ~/.hermes/scripts/backtest/weekly_indicator_update.py
Output to: ~/.hermes/shared/reports/renee/weekly/

Part B — Backtest Health Check
- Run: python3 ~/.hermes/scripts/backtest/v2_3_backtest_smoothing.py
- Check bracket WR vs baseline (49.3%)
- Check dimension weights stability

Part C — Self-Review
- Trade journal for the week: win/loss count, which setups worked/didn't
- Score bracket WR vs backtest baseline
- Indicator performance review
- Toolchain audit: add/upgrade/retire suggestions

§ P-TM eval overlay audit
- Funnel roll-up = aggregate Mon–Fri ART-TM-DAILY-EVAL(theo -> after_G -> after_vol). ❌ invent from weekly-eval alone. 
- Cite book_t + settlement.tm_hit_rate from prior-week/latest ART-WEEKLY-EVAL; N/A if missing. 
- The roll-up must quote the latest settlement.tm_hit_rate and its n from that weekly eval. That figure is the live hit rate. Backtest WR is not live edge. Do not reuse a prior week's rate (W43 example only: 0.3529 n=51 versus backtest WR 49.6%).
- NEVER cite value_hit_rate in this arm(Z-XC-07). 

save:
[OK] ~/.hermes/profiles/renee/workspace/reports/weekly-indicator/YYYY-Www-data.json
[OK] ~/.hermes/shared/reports/renee/weekly/YYYY-Www-indicator-data.json
[OK] ~/.hermes/profiles/renee/workspace/reports/self-review/YYYY-Www-renee-review.md
[OK] ~/.hermes/shared/reports/renee/self-review/YYYY-Www-renee-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-renee-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Renee weekly data + self-review" --ticker BROAD --type self-review --profile renee --path shared/reports/renee/self-review/YYYY-Www-renee-review.md --date YYYY-MM-DD
", parents=[t2])
  Capture ID as t3. Hard-fail -> miss/attempted; chain continues.
"""

ELIZA_CARD = """  4) kanban_create(assignee="eliza", skills=["stock-valuation", "dcf-sensitivity", "financial-health", "peer-comparison", "financial-analysis"],
     title="Eliza: weekly self-review + toolchain audit",
     body="Self-Review:
- Fair value vs actual price error review
- WACC / growth assumptions accuracy
- Financial health score accuracy
- Mistake review: which valuations were off and why
- Zoe challenge acceptance rate for the week

Toolchain Audit:
- [Add] any new data sources or skills needed
- [Upgrade] existing tools with better alternatives
- [Retire] error-prone or obsolete scripts

§ P-VAL eval overlay audit
- Audit numeric valuation_score on every published selected name; omissions hygiene. 
- Cite book_v + settlement.value_hit_rate only — NEVER tm_hit_rate; NEVER blend(Z-XC-07). 
- E5 overlap list WARN only; value-session must not have emitted tm_score(Z-XC-05). 

save:
[OK] ~/.hermes/profiles/eliza/workspace/reports/self-review/YYYY-Www-eliza-review.md
[OK] ~/.hermes/shared/reports/eliza/self-review/YYYY-Www-eliza-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-eliza-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Eliza self-review" --ticker BROAD --type self-review --profile eliza --path shared/reports/eliza/self-review/YYYY-Www-eliza-review.md --date YYYY-MM-DD
", parents=[t3])
  Capture ID as t4. Hard-fail -> miss/attempted; chain continues.
"""

ALICE_CARD = """  5) kanban_create(assignee="alice", skills=["investment-broad-pipeline", "company-research", "financial-analysis", "risk-analysis"],
     title="Alice: weekly self-review + toolchain audit",
     body="Self-Review:
- Macro calls review: which worked, which missed
- Report quality assessment
- Zoe challenge acceptance rate
- Catalyst tracking accuracy

Toolchain Audit:
- [Add] new data sources or skills needed
- [Upgrade] existing tools with better alternatives
- [Retire] error-prone or obsolete scripts

save:
[OK] ~/.hermes/profiles/alice/workspace/reports/weekly-performance-review/YYYY-Www-alice-review.md
[OK] ~/.hermes/shared/reports/alice/weekly-performance-review/YYYY-Www-alice-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-alice-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Alice self-review" --ticker BROAD --type self-review --profile alice --path shared/reports/alice/weekly-performance-review/YYYY-Www-alice-review.md --date YYYY-MM-DD
", parents=[t4])
  Capture ID as t5. Hard-fail -> miss/attempted; chain continues.
"""

ZOE_CARD = """  6) kanban_create(assignee="zoe", skills=["zoe-challenge-enforcement", "financial-analysis"],
     title="Zoe: weekly self-review + toolchain audit + new topics proposal",
     body="Self-Review:
- Challenge quality: false positive / false negative rate
- Severity distribution (Blocker / Major / Minor)
- Alice acceptance rate
- Verification tool quality

Toolchain Audit:
- [Add] new challenge frameworks or verification methods
- [Upgrade] existing verification tools
- [Retire] ineffective challenge patterns

New Topics & Info Suggestions (Trial — 1-3 items):
- New Research Topic: uncovered industry/theme/event
- New Data Source: unused information sources
- New Methodology: untested analysis methods
- Pipeline Improvement: existing flow optimizations
Each item: suggestion | why worth doing | suggested Assignee (Alice/Eliza/Renee/Christina/Emily) | Priority (High/Med/Low)

save:
[OK] ~/.hermes/profiles/zoe/workspace/challenges/weekly-self-review/YYYY-Www-zoe-review.md
[OK] ~/.hermes/shared/reports/zoe/weekly-self-review/YYYY-Www-zoe-review.md
Filename and header Week: = `date -u +%G-W%V` exactly (example `2026-W43-zoe-review.md`).

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Zoe self-review + new topics" --ticker BROAD --type self-review --profile zoe --path shared/reports/zoe/weekly-self-review/YYYY-Www-zoe-review.md --date YYYY-MM-DD
", parents=[t5])
  Capture ID as t6. Hard-fail -> miss/attempted; chain continues.
"""

INTEGRATE_STEP = """Step 7 — Alice integrate(depends on t6): 
  kanban_create(assignee="alice", skills=["four-specialist-integrate", "financial-analysis"],
     title="Integrate Saturday S1 sat-overall",
 body="Mode sat-overall. Load `skills/four-specialist-integrate`. Portal = inbox/weekly-performance/ only. ❌ full weekly overall. ❌ Sunday trunk weekly-deep-dive. 

Read all 6 self-reviews from shared dirs (serial order):
  - shared/reports/emily/self-review/YYYY-Www-emily-review.md
  - shared/reports/christina/self-review/YYYY-Www-christina-review.md
  - shared/reports/renee/self-review/YYYY-Www-renee-review.md
  - shared/reports/eliza/self-review/YYYY-Www-eliza-review.md
  - shared/reports/alice/weekly-performance-review/YYYY-Www-alice-review.md
  - shared/reports/zoe/weekly-self-review/YYYY-Www-zoe-review.md
 -> profile miss; integrate . Process notes(key findings/cross-profile/toolchain) overall . 

Cite prior Sunday 5-pack revised paths or miss+reason(cite only, inbox): 
Canonical inbox root = `$REPORTS_INBOX/<category>/`. ❌ `~/.hermes/shared/inbox/`( desk-pack category dirs; `inbox/...` miss). 
  - $REPORTS_INBOX/commodities-session/
  - $REPORTS_INBOX/rates-session/
  - $REPORTS_INBOX/weekly-trend-momentum/
  - $REPORTS_INBOX/valuation-width/
  - $REPORTS_INBOX/weekly-deep-dive/
Header Alice `## Session summary`(5–8 bullets). 

scoring-eval: prior-week/latest available `scoring-eval/*-weekly-eval.json`. 
Two separate lines, never blended:
(1) book_t + settlement.tm_hit_rate
(2) book_v + settlement.value_hit_rate
N/A if missing. 

E5: do not blend tm_score/valuation_score/B_*/FX_*/C_*/shadow rates_*/commodity_* — juxtapose only; never one blended score. 

Zoe New Topics(candidates only — ❌ kanban_create ): 
Read Zoe's New Topics & Info Suggestions from her review.
List every High priority + actionable row into a candidates JSON(do NOT spawn yet):
  topic_id(stable slug)| title | assignee(Alice/Eliza/Renee/Christina/Emily)| priority | actionable | details
Med/Low -> note only in summary; ❌ spawn. 
save candidates:
[OK] ~/.hermes/shared/reports/mercury/YYYY-Www-candidates.json
Cite path in summary(); spawn Step 7c after Mercury Decide ENFORCE. 

save:
[OK] ~/.hermes/profiles/alice/workspace/reports/weekly-performance-review/YYYY-Www-phase2-summary.md
[OK] ~/.hermes/shared/reports/alice/weekly-performance-review/YYYY-Www-phase2-summary.md

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Self-review summary" --ticker BROAD --type self-review --profile alice --path shared/reports/alice/weekly-performance-review/YYYY-Www-phase2-summary.md --date YYYY-MM-DD
", parents=[t6])
  Capture ID as t7.
"""

DECIDE_STEP = """Step 7b — Mercury Decide ENFORCE(depends on t7): 
  kanban_create(assignee="alice", skills=["financial-analysis"],
    title="Alice: Mercury Decide ENFORCE on Zoe New Topics",
    body="Sarah/Alice terminal only for Decide — ❌ rewrite portal · ❌ *-revised.md. 
Read candidates:
  - shared/reports/mercury/YYYY-Www-candidates.json
  - shared/reports/zoe/weekly-self-review/YYYY-Www-zoe-review.md(cite)

 — terminal:
  python3 ~/.hermes/scripts/mercury_decide.py --scope sat --mode enforce --week YYYY-Www --candidates ~/.hermes/shared/reports/mercury/YYYY-Www-candidates.json --telegram

ENFORCE: ledger + Telegram(Yes/No + scores). 
FAIL-OPEN/DECIDE_UNAVAILABLE/MERCURY_DECIDE_MODE=off -> approve High(legacy); ledger. 
❌ kanban_create topic cards. 

save:
[OK] ~/.hermes/shared/reports/mercury/YYYY-Www-improvement-decisions.json
", parents=[t7])
  Capture ID as t8.
"""

SPAWN_STEP = """Step 7c — Alice spawn APPROVE topics(depends on t8): 
  kanban_create(assignee="alice", skills=["financial-analysis"],
    title="Alice: spawn Mercury-APPROVE Zoe topics",
 body="Read Decide ledger ONLY(❌ mercury_decide decide/❌ ): 
  - shared/reports/mercury/YYYY-Www-improvement-decisions.json
ENFORCE spawn: approve_topic_ids(decision=APPROVE). 
DEFER/REJECT -> ; . 
For each APPROVE topic_id:
  -> kanban_create(assignee=<assignee>, title=<title>, body=<details>, goal_mode=True)
  -> assignees may include alice / eliza / renee / christina / emily(Alice/Eliza/Renee/Christina/Emily)
 -> list new task IDs in phase2-summary footer(append cite)
Idempotency: skipped_already_spawned -> . 
 stamp(no API): 
  python3 ~/.hermes/scripts/mercury_decide.py --scope sat --stamp-only --week YYYY-Www --ledger ~/.hermes/shared/reports/mercury/YYYY-Www-improvement-decisions.json --no-telegram

❌ inbox/rates-session · ❌ inbox/commodities-session · ❌ *-revised.md
", parents=[t8])
  Capture ID as t9.
"""

ZOE_STEP = """Step 8 — Zoe challenge Round 1(depends on Step 7c): 
  kanban_create(assignee="zoe", skills=["zoe-challenge-enforcement", "financial-analysis"],
    title="Zoe: challenge Saturday self-review summary (Round 1)",
    body="Read Alice's integration summary:
  - shared/reports/alice/weekly-performance-review/YYYY-Www-phase2-summary.md
Cite-only Mercury ledger( Decide ):
  - shared/reports/mercury/YYYY-Www-improvement-decisions.json

Write a structured challenge covering:
1. Data quality: Are the self-review claims backed by actual data or just opinions?
2. Analysis gaps: What did the profiles miss in their self-assessments?
3. Contradictions: Cross-profile contradictions or inconsistencies
4. Risk assessment: Are there hidden risks the summary glosses over?
5. Recommendations: What must be fixed before finalizing?

save:
[OK] ~/.hermes/profiles/zoe/workspace/challenges/weekly-self-review/YYYY-Www-challenge-r1.md
[OK] ~/.hermes/shared/reports/zoe/weekly-self-review/YYYY-Www-challenge-r1.md

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Zoe challenge R1 on self-review" --ticker BROAD --type challenge --profile zoe --path shared/reports/zoe/weekly-self-review/YYYY-Www-challenge-r1.md --date YYYY-MM-DD
", parents=[t9])
  Capture ID as t10.
"""

REVISE_STEP = """Step 9 — Alice revise after Zoe R1(depends on Step 8): 
  kanban_create(assignee="alice", skills=["four-specialist-integrate", "financial-analysis"],
    title="Alice: revise Saturday S1 sat-overall after Zoe R1",
    body="Read Zoe's R1 challenge:
  - shared/reports/zoe/weekly-self-review/YYYY-Www-challenge-r1.md
Revise the integration summary addressing each Zoe point inline.
Keep sat-overall cites: prior Sunday 5-pack under `$REPORTS_INBOX/` or miss+reason(cite only; ❌ `~/.hermes/shared/inbox/`); two lines book_t + settlement.tm_hit_rate and book_v + settlement.value_hit_rate(prior-week/latest; N/A if missing); Alice `## Session summary`. ❌ full weekly overall.
List Mercury ENFORCE: approved/deferred/rejected topic_ids + spawned task IDs(cite ledger).
MoA Round 2 is deferred (out of band). This is the official revise.
E5 WARN only · never blend packs(tm/value/B_*/FX_*/C_* keep separate).
Portal light = this overall only -> `$REPORTS_INBOX/weekly-performance/`(❌ rates-session / commodities-session inbox; ❌ `~/.hermes/shared/inbox/`). 

save:
[OK] ~/.hermes/profiles/alice/workspace/reports/weekly-performance-review/YYYY-Www-phase2-summary-revised.md
[OK] ~/.hermes/shared/reports/alice/weekly-performance-review/YYYY-Www-phase2-summary-revised.md
  [->] $REPORTS_INBOX/weekly-performance/YYYY-Www-phase2-summary-revised.md

OpenViking:
  python3 ~/.hermes/scripts/viking_kb.py upsert --summary "Revised self-review summary (Zoe R1)" --ticker BROAD --type self-review --profile alice --path shared/reports/alice/weekly-performance-review/YYYY-Www-phase2-summary-revised.md --date YYYY-MM-DD

 — terminal tool bash ~/.hermes/scripts/sync_reports_www.sh sync web server
", parents=[t10])
"""

TRAIN_PROMPT = f"""Sarah only kanban_create — no analysis and no delegate_task in the Sarah session. MoA is out of band (not in this Saturday batch).

You are Sarah — Hermes desk operator. schedule trigger: self-review batch(12:00 UTC / 13:00 BST), . 
{JOB_MARKER}. 
Serial one-by-one(): emily -> christina -> renee -> eliza -> alice -> zoe -> Alice integrate -> Mercury Decide ENFORCE -> spawn APPROVE -> Zoe R1 -> Alice revise. 
Hard-fail on a leg -> miss/attempted, . 

Save path convention:
 : ~/.hermes/profiles/<name>/workspace/<category>/
 : ~/.hermes/shared/reports/<name>/<category>/
 : $REPORTS_INBOX/<category>/
ISO week token = stdout of `date -u +%G-W%V` (literal letter W; example `2026-W43`).
  Paste that stdout into every `YYYY-Www`. Header Week: and filename are the same token.
  Mon–Fri of the fire Saturday are that ISO week (2026-10-19..23 = 2026-W43).
  Prior Sunday pack files keep their stored stems.
  Catch-up after a missed Sat uses the original Saturday: `date -u -d '<that Sat>' +%G-W%V`.
  Same-week re-run MAY overwrite existing files (overwrite OK).
  Ban stem `2026-43` and any `YYYY-WW` with no letter W.
  Ban W+1 bump(❌ bump to the next ISO week to avoid overwrite).
  Ban date-stem portal.
  Portal path is `$REPORTS_INBOX/weekly-performance/<token>-phase2-summary-revised.md`.
Specialist Sat self-reviews(emily/christina/renee/eliza/alice/zoe)-> workspace + shared only. 
Portal Jobs light = Alice revise only -> inbox/weekly-performance/*-revised.md
  (glob expectation `{{iso_week}}-phase2-summary-revised.md`). 
❌ inbox/rates-session · ❌ inbox/commodities-session for this batch.

========================================
{JOB_MARKER}
========================================

{STEP1_HEAD}: 

{EMILY_CARD}
{CHRISTINA_CARD}
{RENEE_CARD}
{ELIZA_CARD}
{ALICE_CARD}
{ZOE_CARD}

{INTEGRATE_STEP}

{DECIDE_STEP}

{SPAWN_STEP}

{ZOE_STEP}

{REVISE_STEP}

Completion
========================================
 terminal tool bash ~/.hermes/scripts/sync_reports_www.sh sync web server
"""


def _save_lines(prompt: str) -> list[str]:
    out: list[str] = []
    for ln in (prompt or "").splitlines():
        low = ln.lower()
        if "[ok]" in low or "[->]" in ln or "➡️" in ln:
            out.append(ln)
    return out


def prompt_complete(prompt: str) -> bool:
    p = prompt or ""
    if JOB_MARKER not in p:
        return False
    if "6 serial" not in p and STEP1_HEAD not in p:
        return False
 if "one-by-one" not in p and "" not in p:
        return False
    if "0 12 * * 6" not in JOB_SCHEDULE:
        return False
    if "12:00 UTC" not in p:
        return False
 if "" in p or "6 parallel" in p.lower():
        return False
    for name in SERIAL_ASSIGNEES:
        if f'assignee="{name}"' not in p:
            return False
    for path in SELF_REVIEW_PATHS:
        if path not in p:
            return False
    if "parents=[t1]" not in p or "parents=[t6]" not in p or "parents=[t10]" not in p:
        return False
    if "parents=[t7]" not in p or "parents=[t8]" not in p or "parents=[t9]" not in p:
        return False
    if "mercury_decide.py" not in p or "Mercury Decide ENFORCE" not in p:
        return False
    if "approve_topic_ids" not in p:
        return False
    if "YYYY-Www-candidates.json" not in p:
        return False
    if "2026-W43" not in p:
        return False
    if "2026-43" not in p:
        return False
    if "YYYY-WW-" in p:
        return False
    if "inbox/weekly-performance/" not in p:
        return False
    if "$REPORTS_INBOX/" not in p:
        return False
    if "❌ `~/.hermes/shared/inbox/`" not in p and "❌ ~/.hermes/shared/inbox/" not in p:
        return False
    # ISO week of fire day — Option A (no W+1 bump; overwrite OK; no date-stem portal).
    if "%G-W%V" not in p and "date -u +%G-W%V" not in p:
        return False
    if "overwrite" not in p.lower() and "MAY overwrite" not in p:
        return False
    bump_ban = (
        "bump to W{n+1}" in p
        or "bump to W{{n+1}}" in p
        or "next ISO week to avoid overwrite" in p
        or "❌ bump" in p
    )
    if not bump_ban:
        return False
    if "YYYY-MM-DD-phase2" not in p and "date-stem" not in p.lower():
        return False
    # Must not encourage bumping the week number to dodge collisions.
    if "use W+1" in p.lower() or "prefer W+1" in p.lower() or "bump week to avoid" in p.lower():
        return False
    if "Alice/Eliza/Renee/Christina/Emily" not in p:
        return False
    if "E5" not in p:
        return False
    if "never blend" not in p.lower() and "do not blend" not in p:
        return False
    if "NEVER invent B_*" not in p:
        return False
    if "broker Emily" not in p:
        return False
    if "Part A — Week artifact roll-up" not in p:
        return False
    if "Same audit depth as Renee/Eliza" not in p:
        return False
    if "Lite self-review" in p:
        return False
    for needle in (
        "sat-overall",
        "four-specialist-integrate",
        "prior Sunday 5-pack",
        "book_t + settlement.tm_hit_rate",
        "book_v + settlement.value_hit_rate",
        "§ P-TM eval overlay audit",
        "§ P-VAL eval overlay audit",
        "## Session summary",
    ):
        if needle not in p:
            return False
    for ln in _save_lines(p):
        for bad in FORBIDDEN_SAT_INBOX:
            if bad in ln:
                return False
    return True


def build_prompt(existing: str = "") -> str:
    body = TRAIN_PROMPT.strip() + "\n"
    if not prompt_complete(body):
        raise RuntimeError("refuse: assembled Saturday self-review prompt failed contract checks")
    # Structural completeness alone is not enough — refresh when firewall/body drifts.
    if (existing or "").rstrip("\n") == body.rstrip("\n"):
        return existing if existing.endswith("\n") else existing + "\n"
    return body
