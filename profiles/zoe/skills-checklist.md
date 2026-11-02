# Zoe — Hermes refined draft (H-W1)
> Not Helios prompts · Not live Hermes host · Scrubbed for review

Mapped from shared Hermes `hermes/skills/` (export-redacted inventory). Zoe **challenges** Alice/Eliza profile skills under `profiles/*/skills/` — Zoe does **not** author those trees.  
Parent: [`../zoe/SOUL.md`](SOUL.md) · matrix: [`../../AGENTS.md`](../../AGENTS.md) §4.

**Legend:** ✅ keep for Zoe refine · ⚠️ optional / support · ❌ exclude from Zoe core (wrong owner or ops/secret surface)

---

## 1. Core — IC gate & challenge

| Skill (shared path slug) | Role for Zoe | Notes |
|--------------------------|--------------|-------|
| `investment/zoe-challenge-enforcement` | ✅ | Mandatory challenge before “final”; compliance / gate mindset. Scrub host paths & concrete model IDs when porting skill text. |
| `investment/zoe-challenge-rubrics` | ✅ | Active rubrics: data quality, structure, cross-version escalation, “Fixed” label rules. Do **not** copy live MEMORY rubric anecdotes with holdings. |
| `investment/data-quality-audit` | ✅ | Claim-vs-evidence; Round 2+ revised drafts. Scrub week-specific incident IDs / personal examples. |
| `investment/scoring-engine-audit-checklist` | ✅ | When challenging T&M / scoring-engine change claims (logic, scale, determinism) — audit **claims**, not author scoring. |

**Output contract (Helios-aligned):** challenge task → JSON `{verdict, severity, summary, items[]}`; data-QA task → JSON completeness shape (see SOUL §3–§4).

---

## 2. Core — verification helpers (investment)

| Skill | Role for Zoe | Notes |
|-------|--------------|-------|
| `investment/company-research` | ✅ | Background check when a draft’s company claim is material |
| `investment/financial-analysis` | ✅ | Read statements / ratios to stress narrative claims |
| `investment/financial-health` | ✅ | Quantitative health scoring as **challenge evidence** |
| `investment/moat-assessment` | ✅ | Moat claims need evidence / weaknesses |
| `investment/peer-comparison` | ✅ | Peer tables in drafts must be checkable |
| Eliza `skills/comps-analysis` / `earnings-*` (challenge only) | ⚠️ | Challenge as-of/Sources/no score overwrite — **not** author |
| Alice `skills/catalyst-calendar` / `thesis-tracker` / `idea-generation` (challenge only) | ⚠️ | Challenge invented dates/routes/blended scores — **not** author |
| `investment/risk-analysis` | ✅ | Risk severity language vs evidence |
| `investment/solvency-verification` | ✅ | Distress / Z-Score false-alarm checks on value claims |

These support **challenge / QA**. They must not turn Zoe into the valuation or research narrative author.

---

## 3. MOA awareness (not Zoe-only)

| Skill | Role for Zoe | Notes |
|-------|--------------|-------|
| `investigation/moa-investigation` | ⚠️ | Understand presets / Task Force pattern when reviewing MOA output. **MOA = Hermes config preset** — not Zoe-only. Daily Zoe REJECT must not request MOA. |

Do **not** list Zoe as owner of `run_moa` or MOA panel execution.

---

## 4. Support / style

| Skill | Role for Zoe | Notes |
|-------|--------------|-------|

---

## 5. Explicit exclusions

| Skill / surface | Why ❌ |
|-----------------|--------|
| `valuation/*` authoring pipelines (e.g. Eliza MOA valuation pipeline as **writer**) | Eliza / valuation engine owns production; Zoe challenges only |
| `trading/technical-analysis` as author | Renee / scoring |
| Broker / account clients (execution API utils) | Secrets / holdings; Emily / M7 for execution |
| Host `workspace/scripts/*` path lists from export SOUL | Paths scrubbed; reintroduce only as logical tool names later |
| Kanban orchestrator / worker as Zoe identity | Prefect owns orchestration |
| `devops/*` profile/cron audits as core IC | Ops hygiene, not investment gate |
| Live `MEMORY.md` / personal P&L / fills | Never in drafts or OSS |
| Narrative draft / revise / integrate skills owned by Alice / Renee / Eliza | Wrong agent |

---

## 6. Task × skills (Zoe)

| Task class | Skills primarily used |
|------------|------------------------|
| IC challenge | `zoe-challenge-*`, rubrics, data-quality-audit, verification helpers |
| Phase-3 session gate | REJECT missing `## Session summary` or `## Market insight`; reviser map T&M→renee · commodities→emily · rates→christina · value-session→eliza · close/deep-dive→alice |
| Desk cross-cutting **Z-XC-01…08** + **Z-MI-01…05** | Challenge IDs in SOUL §3; contracts [`docs/desk-artifact-contracts.md`](../../docs/desk-artifact-contracts.md) — docs only, no new cron IDs |
| Data QA (e.g. Saturday arm) | `data-quality-audit`, pack/artifact checks |
| MOA panel | `moa-investigation` awareness only — **not** Zoe executing the panel |
| Draft / revise narrative / `*-revised.md` | **Not Zoe** · E5 no blend |

**Z-XC quick list:** Z-XC-01 blended leaderboard **REJECT** · Z-XC-02 miss without reason · Z-XC-03 thesis `both` without E5 **WARN** · Z-XC-04 idea route mutating scores · Z-XC-05 value-session emit `tm_score` · Z-XC-06 weekly T&M Option G · Z-XC-07 blended hit rates · Z-XC-08 broker language in research reports.

**Z-MI quick list:** Z-MI-01 missing `## Market insight` **REJECT** · Z-MI-02 specialist desk Risk-on/off/desk Macro view **REJECT** · Z-MI-03 Alice missing four Market insight cites **REJECT** · Z-MI-04 Alice missing `## Macro view` **REJECT** · Z-MI-05 four-path overclaim/**5/5 revision stands**/T-1 live cite **Major/CONDITIONAL**.

**Model:** not pinned. Select in Hermes setup / `hermes model`.

---

## 7. Scrub checklist (this agent)

- [x] No host / wiki / LAN paths in draft text  
- [x] No API keys, chat IDs, broker accounts  
- [x] No holdings / fills / live MEMORY  
- [x] No concrete provider model ID pins (Hermes setup selects models)  
- [x] MOA clarified as config panel, not Zoe-only  
- [x] Zoe not framed as narrative writer  
- [x] Phase-3 reviser map + Session summary/Market insight REJECT + E5 no blend  
- [x] Desk cross-cutting **Z-XC-01…08** + **Z-MI-01…05** (docs P0; no new cron IDs)

---

## 8. Source inventory (export-redacted)

Primary folders consulted:

- `hermes/skills/investment/` — challenge, rubrics, DQ, scoring audit, research/financial helpers  
- `hermes/skills/investigation/moa-investigation`  
- Profile SOUL: `hermes/profiles/zoe/SOUL.md` (redacted export)  
- Helios reference: `app/agents/prompts/zoe.md`, `docs/AGENTS.md`
