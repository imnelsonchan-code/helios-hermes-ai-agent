# christina tests — observation-only audit harness

Static consistency + scaffold + lightweight **obs backtest** hygiene for the christina rates/bonds/FX profile.  
**No network · no API keys · no PnL.**

English OK in tests. Observation only · ETF proxy ≠ cash bond · NO_DB.

---

## Quick start

From repo root:

```bash
./profiles/christina/tests/run_christina_audit.sh
```

Or:

```bash
bash profiles/christina/tests/run_christina_audit.sh
```

Exit `0` = all checks pass · non-zero = fail (CI-friendly).

---

## What it checks

| # | Suite | What |
|---|--------|------|
| 1 | **Load-order SSOT** | All 6 Keep skills + `skills-checklist.md` + `SOUL.md` contain canonical order: `curve-watch → real-rates → fedwatch-consume → bond-etf-tape → fx-us-uk-bridge → rates-session-report` (or short tokens `curve → real → fedwatch → bond-etf → fx → trunk`) |
| 2 | **Namespace isolation** | Signal only `B_*`/`FX_*`/`NO_SETUP`/`miss`; bare `BUY` banned in SOUL/checklist/bond-etf/fx/trunk; checklist documents ❌ `C_*`↔`B_*`↔`FX_*` |
| 3 | **Scaffold completeness** | Daily + Weekly blank templates in `rates-session-report` each have `## Session summary` · FedWatch · Miss ledger · Ccy · Rate scenario · FX range (column header + summary bullet) |
| 4 | **Obs backtest hygiene** | Scores `obs_backtest_fixture.md` (fake prior session + next-day prints) on hygiene rules only — **no PnL**. Negative control: `fixtures/obs_backtest_bad.md` must exhibit violations |
| 5 | **FedWatch consume-only** | `fedwatch-consume` documents consume-only + cron `<job-id>` + locked path `alice/fedwatch`/`latest.json` |
| 6 | **Firewall** | SOUL/checklist mention `NO_DB` · observation only · ETF proxy ≠ cash |

---

## Files

```text
profiles/christina/tests/
  README.md                 ← this file
  run_christina_audit.sh    ← runner (exit nonzero on fail)
  obs_backtest_fixture.md   ← good fixture (hygiene PASS)
  fixtures/
    obs_backtest_bad.md     ← bad fixture (negative control)
```

---

## Obs backtest template (how to reuse)

1. Copy `obs_backtest_fixture.md` → fill a real prior draft path / prints.
2. Keep Signal only `B_*`/`FX_*`/`NO_SETUP`/`miss` — never bare `BUY`/`tm_score`/`C_*`.
3. When Obs entry+cut+TP filled: Basis **must** be present; Daily ≤3 full bond levels; FX full levels ≤2.
4. Bond rows: Ccy present when table has Ccy column.
5. Re-run the script — section 4 scores hygiene only (inside/outside Est band is narrative; **never** compute PnL).

---

## Requirements

- `bash` + `python3` (stdlib only)
- Repo layout with `profiles/christina/skills/*/SKILL.md`
