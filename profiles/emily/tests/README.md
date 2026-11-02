# emily tests — observation-only audit harness

Static consistency + scaffold + lightweight **obs backtest** hygiene for the emily commodity profile.
**No network · no API keys · no PnL.**

Observation only · emily ≠ Emily (broker/M7).

---

## Quick start

From repo root:

```bash
./profiles/emily/tests/run_emily_audit.sh
```

Or:

```bash
bash profiles/emily/tests/run_emily_audit.sh
```

Exit `0` = all checks pass · non-zero = fail (CI-friendly).

---

## What it checks

| # | Suite | What |
|---|--------|------|
| 1 | **Load-order SSOT** | All 8 Keep skills + `skills-checklist.md` + `SOUL.md` contain canonical order: `sources → world → insight → direction → forecast → signal → puzzle → trunk` (or full `commodity-*` names in that order) |
| 2 | **Namespace isolation** | `DIR_*` not used as **Signal** values in Trade map examples; bare `BUY` banned; checklist documents isolation |
| 3 | **Scaffold completeness** | Daily + Weekly blank templates in `commodity-session-report` each have Insight / Direction / Forecast **cite** slots |
| 4 | **Obs backtest hygiene** | Scores `obs_backtest_fixture.md` (fake prior session + next-day prints) on hygiene rules only — **no PnL**. Negative control: `fixtures/obs_backtest_bad.md` must exhibit violations |
| 5 | **ADAPT patch gates** | Static keywords: post-crawl QA / `data_delay` · term+CY+COT · shock/calendar/FMP · anti-ARIMA Method A · shadow breakdown · obs-backtest Eval/Sat (not in Keep load) · host apply skill list (skipped if absent) · P1 Later stubs present (not in Keep) |
| 6 | **Desk-pack prompts** | `check_desk_pack_prompts.sh` — fails if emily load still `sources→signal→world…`; requires canonical 8-skill chain |

---

## Files

```text
profiles/emily/tests/
 README.md ← this file
 run_emily_audit.sh ← runner (exit nonzero on fail)
 check_desk_pack_prompts.sh ← desk-pack load-order gate
 smoke_live_checklist.md ← host adhoc daily-lite smoke (observation-only; private CLI)
 obs_backtest_fixture.md ← good fixture (hygiene PASS)
 fixtures/
 obs_backtest_bad.md ← bad fixture (negative control)
```

### Live smoke (optional · needs Hermes host)

See [`smoke_live_checklist.md`](smoke_live_checklist.md) — conceptual host smoke; no secrets. Static checks first; live SSH only when you choose.

---

## Obs backtest template (how to reuse)

1. Copy `obs_backtest_fixture.md` → fill a real prior draft path / prints.
2. Keep Direction in `DIR_*` cite blocks; Signal only `C_*` / `NO_SETUP` / `miss`.
3. When Obs entry+SL+TP filled: Basis **must** cite Forecast / Scenario / Est; Daily ≤3 full levels.
4. Re-run the script — section 4 scores hygiene only (inside/outside Est band is narrative; **never** compute PnL).

---

## Requirements

- `bash` + `python3` (stdlib only)
- Repo layout with `profiles/emily/skills/*/SKILL.md`
