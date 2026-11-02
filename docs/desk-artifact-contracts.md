# Desk artifact contracts (P0 cross-cutting)

> **Docs only** for Hermes refine. Not live host cron. Not Helios app.
> Portal paths in ID tables may stay **logical** `inbox/{dir}/…` stems (3-layer: workspace → shared → inbox).
> **Hard rule — agent filesystem ops:** user-facing inbox writes/reads use **`$REPORTS_INBOX/`** only. **`~/.hermes/shared/inbox/` is never valid** (nor `shared/inbox/` as a root).
> Do **not** invent new cron IDs here — cadence labels only (Wave / Car / Sat arm). Live clocks: [`cron-jobs.md`](cron-jobs.md).

**Scope:** shared contracts across **Eliza · Renee · Alice · Zoe** desks (emily / christina sessions cite the same Session-summary + E5 rules when they touch equity sleeves).

```text
Draft → Zoe IC challenge → owner *revised.md → inbox / portal
Zoe never writes *revised.md
```

---

## Hard rules (all artifacts)

| Rule | Meaning |
|------|---------|
| **E5 — no blend** | P-TM (`tm_score`) and P-VAL (`valuation_score`) stay separate screens. Overlap ticker → **WARN only**. Never average, never bare `score`, never one sleeve rewrite the other, never blended leaderboard / blended hit rate. |
| **Fail-closed** | Missing ADX / pack / eval JSON / revised path → **N/A · miss · pending · hard-fail note** — do **not** invent numbers, demotions, hit rates, or FV. Soft-wait legs may continue with `miss` so Alice can cite. |
| **Broker quarantine** | Research language only (candidates / observation / not investment advice). No broker Emily/M7 orders, account IDs, fills, Long/Short tickets, or execution API. Profile slug `emily` (commodities) ≠ broker Emily. |
| **Session summary required** | Every session / overall draft that ships as portal light must include **`## Session summary`** after Header (5–8 bullets + sleeve stance / regime where owned). Missing → Zoe **`REJECT`**. Alice overall has **two** blocks: her own `## Session summary` after Header, **and** four specialist summary cites **or** explicit `miss` + reason. The own block is not a paste of the four. |
| **Market insight required** | emily／christina／renee／eliza session drafts must include **`## Market insight`** (domain comments & insight; Daily compact / Weekly thicker). Missing → Zoe **`REJECT`（Z-MI-01）**. Alice overall cites four Market insights **or** `miss` + reason（**Z-MI-03**）. Compact cite only — no second specialist essay. |
| **Macro view + desk Risk-on/off (Alice only)** | Alice daily / weekly overall must include **`## Macro view`** (synthesize four Market insights → agree / tension / miss → desk-wide macro relationships; daily 8–15 lines; weekly ~1 page) + desk Risk-on/off final. Missing Macro view → Zoe **`REJECT` (Z-MI-04)**. Specialist finalizing desk Risk-on/off or desk-wide Macro view → **`REJECT` (Z-MI-02)**. |
| **Inbox absolute path** | Agent save/cite paths for portal lights resolve under `$REPORTS_INBOX/{dir}/…`. Never `~/.hermes/shared/inbox/` · never relative `inbox/` under `shared/reports/<profile>/`. |

---

## Shared artifact ID table

| Artifact ID | Producer | Consumers | Minimum contract | Portal path (when applicable) |
|-------------|----------|-----------|------------------|-------------------------------|
| **ART-TM-DAILY-PACK** | T&M daily generator (`daily_trend_momentum` family) under **Renee** train | Renee narrative · Zoe · Alice overall (cite) · Sat P-TM | Live pack: **published** `tm_score` (0–100, Option 6 weighted then hard clip) + optional `weighted_total_raw` (uncapped audit) + `score_breakdown` + brackets / ranking on published score; Option G may suppress effective BUY (daily only); **no** `valuation_score`; fail-closed on ADX / tape miss | Pack lives under shared Renee T&M paths; user-facing narrative is **ART-TM-SESSION-D** |
| **ART-TM-WEEKLY-PACK** | Weekly T&M pipeline (`weekly_indicator_update` + `weekly_report_gen` + `verify_weekly_adx`) under **Renee** | Renee weekly narrative · Zoe · Alice deep-dive · Sat P-TM | Same published `tm_score` (0–100) + optional `weighted_total_raw`; Risk% + ATR14% columns; SPY ADX = true-Wilder **fail-closed**; **no Option G** banner / BUY suppress; **no** blend with value-100 | Feeds **ART-TM-SESSION-W** |
| **ART-TM-DAILY-EVAL** | Scoring-eval daily overlay (host script class) | Renee § funnel cite · Sat **§ P-TM** roll-up · Zoe monotonicity gate | JSON: `spy_adx`, `option_g_active` (null → N/A ADX missing), `buys_theoretical` ≥ `buys_after_option_g` ≥ `buys_after_volume_gate`, `volume_demotions[]`; demotions **informational** — never rewrite live `tm_score` | `inbox/scoring-eval/YYYY-MM-DD-daily-eval.json` (also shared `renee/scoring-eval/`) |
| **ART-VAL-WIDTH-PACK** | Eliza `valuation_width_scan` draft + JSON | Eliza revise · Zoe · Alice (after revise) · WoW guard | Every published passer: numeric `valuation_score` (0–100) + breakdown + `width_verdict`; map `composite_score` → `valuation_composite` / `valuation_score`; **`e5_overlap` WARN list**; **never** `tm_score` / bare `score` | Draft: shared Eliza width report + JSON — **not** inbox until revise |
| **ART-VAL-WIDTH-REVISED** | **Eliza** revise after Zoe | Alice Sunday overall · Monday A-08 · position_watch E5 · Sat P-VAL | Inbox stem `YYYY-WW-valuation-width-revised.md` (+ optional revise JSON overlay); FV/verdict changes must stay consistent with JSON; E5 overlap WARN only | `inbox/valuation-width/*-valuation-width-revised.md` |
| **ART-VAL-SESSION** | **Eliza** daily value-session | Alice market-close overall · Zoe · Sat P-VAL hygiene | Cite Sunday lock `valuation_score`; movers vs lock; **no** reshuffle value-100; **no** emit `tm_score`; required `## Session summary` + **`## Market insight`** + News／Market + Lenses；no desk Risk-on/off | `inbox/value-session/YYYY-MM-DD-*-revised.md` |
| **ART-TM-SESSION-D** | **Renee** daily T&M revise | Alice overall · Zoe · Sat P-TM | Header → **`## Session summary`** → **`## Market insight`** → News／Market → Lenses → optional § funnel（when **ART-TM-DAILY-EVAL** exists）→ ranking from **live pack only**; no re-score; no desk Risk-on/off | `inbox/daily-trend-momentum/YYYY-MM-DD-*-report-revised.md` |
| **ART-TM-SESSION-W** | **Renee** weekly T&M revise | Alice deep-dive · Zoe · Sat P-TM | Same G1 family + **`## Session summary`** + **`## Market insight`** + News／Market + Lenses；**no Option G**; keep generator tables; optional Book T footnote from prior **ART-WEEKLY-EVAL** — never Book V | `inbox/weekly-trend-momentum/YYYY-WW-*-trend-momentum-report-revised.md` |
| **ART-WEEKLY-EVAL** | Scoring-eval weekly overlay (host script class) | Sat **§ P-TM** / **§ P-VAL** · Alice S1 integrate · Zoe hit-rate gate | Separate Book T / Book V; `settlement.tm_hit_rate` and `settlement.value_hit_rate` on **two lines** — never blended; N/A if missing (Sat often cites prior-week / latest) | `inbox/scoring-eval/YYYY-MM-DD-weekly-eval.json` (also shared `scoring-eval/`) |
| **ART-E5-OVERLAP** | Eliza width JSON field `e5_overlap` (+ narrative WARN lines) | Alice · Zoe · Renee/Eliza boundary notes · risk overlays | List of same-week tickers in both sleeves; **WARN only**; never change ranks / scores / exits from the other sleeve | Embedded in **ART-VAL-WIDTH-*** JSON / revised narrative; not a standalone Jobs light |
| **ART-THESIS** | **Alice** `thesis-tracker` | Zoe · Sat thesis-drift · idea handoff | Living `theses/TICKER.md`; formal update after Zoe; sleeve `tm` \| `value` \| `both` — **`both` requires E5 WARN**; falsifiable invalidation; no invented pack scores | `inbox/analysis/YYYY-MM-DD-<TICKER>-thesis-update-revised.md` (+ drift under `analysis/`); registry under shared Alice `theses/` |
| **ART-IDEA-SCREEN** | **Alice** `idea-generation` | Zoe · route consumers (Renee/Eliza later trains) | Shortlist with `route: tm \| value \| both-WARN \| drop`; eval-only; **must not** mutate Option 6 / five-factor weights or emit blended score | `inbox/analysis/YYYY-Www-idea-screen-revised.md` |
| **ART-CATALYST** | **Alice** `catalyst-calendar` | Zoe · Alice integrate / close pointer | Forward earnings / Form 4 clusters etc.; observation only; invented dates → Zoe Major/`REJECT`; no broker positioning language | `inbox/analysis/YYYY-Www-catalysts-revised.md` |
| **ART-SESSION-SUMMARY** | Every session / overall **author** (emily · christina · renee · eliza · alice) | Alice overall (cite) · Zoe gate · Sat artifact roll-up | Required `## Session summary` block; miss cite needs **reason**; Alice must not substitute a second full specialist essay | Section inside each `*-revised.md` portal light (not a separate file) |
| **ART-MARKET-INSIGHT** | emily · christina · renee · eliza (session authors) | Alice overall Macro view · Zoe **Z-MI-01…03** | Required `## Market insight` (domain comments & insight); Alice pull pointer in Session summary; compact cite only; no desk Risk-on/off or desk Macro view final | Section inside specialist `*-revised.md` (not a separate file) |
| **ART-MACRO-VIEW** | **Alice** overall #5 | Zoe **Z-MI-04** · desk Risk-on/off | Required `## Macro view` on daily + weekly overall; synthesize four Market insights → relationships; Alice alone owns desk Risk-on/off | Section inside `inbox/market-close/` · `daily-social/` · `weekly-deep-dive/` overall |

**Alias:** `ART-TM-SESSION-D/W` in planning notes = **ART-TM-SESSION-D** + **ART-TM-SESSION-W**.

---

## Cadence → primary artifacts

| Cadence (label) | Primary artifacts |
|-----------------|-------------------|
| **Daily Desk Pack** (Wave1∥ → Wave2∥ → Alice → Zoe → Alice revise) | Rates/commodities sessions (peer) · **ART-TM-SESSION-D** · **ART-VAL-SESSION** · Alice overall（Four Market insights + Macro view + dual market-close / daily-social）· optional later **ART-TM-DAILY-EVAL** |
| **Sunday Desk Pack** (Cars 1→5) | Weekly commodities/rates · **ART-TM-SESSION-W** ← **ART-TM-WEEKLY-PACK** · **ART-VAL-WIDTH-REVISED** ← **ART-VAL-WIDTH-PACK** (+ **ART-E5-OVERLAP**) · Alice deep-dive portal `weekly-deep-dive/YYYY-MM-DD-Wnn-weekly-deep-dive-revised.md`（Jobs `{date}*`；not pure `YYYY-WW-*`） |
| **Saturday S1** | Specialist self-review arms (shared only) · **§ P-TM** / **§ P-VAL** cite **ART-TM-DAILY-EVAL** roll-up + **ART-WEEKLY-EVAL** · Alice portal exact `weekly-performance/{iso_week}-phase2-summary-revised.md`（Option A: `{iso_week}` = `YYYY-Www` = stdout of `date -u +%G-W%V`, literal W, example `2026-W43`；ban stem `2026-43`；never W+1；overwrite OK） |
| **Adhoc Alice research** | **ART-THESIS** · **ART-IDEA-SCREEN** · **ART-CATALYST** |

Workflow sketches (documentation YAML, not auto-executing host cron):

- [`../profiles/desk/workflows/desk-pack-daily.yaml`](../profiles/desk/workflows/desk-pack-daily.yaml)
- [`../profiles/desk/workflows/desk-pack-weekly.yaml`](../profiles/desk/workflows/desk-pack-weekly.yaml)
- [`../profiles/desk/workflows/desk-pack-saturday.yaml`](../profiles/desk/workflows/desk-pack-saturday.yaml)

Zoe cross-cutting challenge IDs: **Z-XC-01…08** + **Z-MI-01…05** in [`../profiles/zoe/SOUL.md`](../profiles/zoe/SOUL.md) / [`../profiles/zoe/skills-checklist.md`](../profiles/zoe/skills-checklist.md).

### ART-DECIDE-ENFORCE (Mercury Decide)

| Field | Value |
|-------|-------|
| **Producer** | Host [`../scripts/host/mercury_decide.py`](../scripts/host/mercury_decide.py) |
| **Sat ledger** | `shared/reports/mercury/YYYY-Www-improvement-decisions.json` (+ candidates `YYYY-Www-candidates.json`) |
| **Zoe ledger** | `shared/reports/mercury/zoe/YYYY-MM-DD-*.decide.json` |
| **Telegram** | Yes/No (+ probs) + scores; prefix `ENFORCE` |
| **Sat consumer** | Spawn step — only `approve_topic_ids` |
| **Zoe consumer** | Escalate-only vs Zoe verdict (never relax REJECT) |
| **Fail-open** | `DECIDE_UNAVAILABLE` / `MERCURY_DECIDE_MODE=off` → Sat High spawn legacy; Zoe keep verdict |
| **Forbidden** | Bare field name `score`; write `*-revised.md` / inbox portal; external chat pin; blend Book T/V |

Not tracked by `zoe_tracker.py` (self-review / JSON ledgers out of scope).

**Kill switch / rollback:** set host env `MERCURY_DECIDE_MODE=off` (overrides CLI `--mode enforce`); restore prior scripts from `~/.hermes/scripts/_backup_refine_<TS>/` or remove `mercury_decide.py` if first deploy; Sat prompts may be reverted via `patch_saturday_self_review.py` from git.

### ART-DECIDE-MOA-PUBLISH

| Field | Value |
|-------|-------|
| **Producer** | [`../scripts/host/mercury_decide.py`](../scripts/host/mercury_decide.py) `--scope moa_publish` + [`../scripts/host/moa_rework_gate.py`](../scripts/host/moa_rework_gate.py) |
| **Input** | Existing MOA report `.md` (Hermes chat / skill produces it — gate does not run MOA) |
| **Ledger** | `shared/reports/mercury/moa/<date>-<stem>.decide.json` |
| **Rework brief** | `shared/reports/mercury/moa/<date>-<stem>-rework.json` when REWORK |
| **Threshold** | `publish_score >= 90` → ACCEPT; else REWORK (v1) |
| **Weights** | completeness 45% · coherence 35% · sources 20%; invented_numbers hard gate; E5 blend → REWORK |
| **Infra fail-open** | `DECIDE_UNAVAILABLE` / `MERCURY_DECIDE_MODE=off` → ACCEPT (no auto-rework) |
| **Exit** | gate `0` ACCEPT / fail-open; `1` REWORK; `2` refuse |
| **Order** | MOA report → Mercury gate → (optional human/MOA rework ≤2) → Zoe IC |
| **Forbidden** | Mercury as MOA seat; daily MOA; write `*-revised.md`; blend with `tm_score` / `valuation_score` |

---

## Scrub notes

- No API keys, chat IDs, holdings, fills, or live MEMORY.
- No new cron / kanban instance IDs invented in this file.
- Logical `inbox/…` stems in the ID table are fine; agent ops still expand to `$REPORTS_INBOX/…`.
