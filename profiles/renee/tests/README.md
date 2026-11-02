# renee tests — T&M sleeve audit harness

Static consistency + lightweight **T&M session / funnel** hygiene for the renee P-TM profile.  
**No network · no API keys · no PnL.**

English or Chinese OK in tests.Observation only · no score rewrite · E5 never-blend · weekly no Option G.

---

## Quick start

From repo root:

```bash
./profiles/renee/tests/run_renee_audit.sh
```

Or:

```bash
bash profiles/renee/tests/run_renee_audit.sh
```

Exit `0` = all checks pass · non-zero = fail(CI-friendly).

Sleeve wrapper(eliza + renee + desk):

```bash
./scripts/run-equity-sleeve-audits.sh
```

---

## What it checks

| # | Suite | What |
|---|--------|------|
| 1 | **P0 skills exist** | `tm-session-report` · `tm-signal-funnel` · `tm-e5-firewall` |
| 2 | **Skill keywords** | no score rewrite · `## Session summary` · `## Market insight` · Alice pull/Lenses miss split · News `miss` REJECT · headlines-only ban · E5 `score_breakdown` + Market insight cite · funnel after Lenses · Mon–Fri roll-up · SOUL placement |
| 3 | **Checklist** | Must **not** claim “no per-agent skills tree”;must mention P0 profile skills |
| 4 | **apply-to-hermes** | `RENEE_SKILLS` includes the three skills |
| 5 | **Fixture hygiene** | Good fixtures PASS(daily · weekly · funnel · null-ADX)· bad fixtures FAIL as negative controls(incl. after_G=0 ⇒ after_vol=0) |

---

## Files

```text
profiles/renee/tests/
  README.md                      ← this file
  run_renee_audit.sh             ← runner(exit nonzero on fail)
  tm_session_fixture.md          ← good daily T&M(hygiene PASS)
  tm_weekly_fixture.md           ← good weekly T&M(Session summary · no Option G applied · tm_score)
  funnel_fixture.md              ← good funnel(monotonic PASS)
  funnel_null_adx_fixture.md     ← good null-ADX(Option G N/A — ADX missing)
  fixtures/
    tm_session_bad.md            ← bad(negative control)
    funnel_bad.md                ← bad non-monotonic(negative control)
    funnel_after_g_zero_bad.md   ← bad after_G=0 but after_vol>0(negative control)
```

---

## Fixture template(how to reuse)

1. Copy `tm_session_fixture.md` / `tm_weekly_fixture.md` / `funnel_fixture.md` → fill real revise drafts.
2. Always include `## Session summary`;ranking = live pack `tm_score` only.
3. Never blend `valuation_score` into T&M ranking;weekly never apply Option G suppress.
4. Funnel counts must be monotonic:`theo ≥ after_G ≥ after_vol`;`after_G=0 ⇒ after_vol=0`;missing / null ADX → **N/A — ADX missing**(not trending).
5. Re-run the script — section 5 scores hygiene only(**never** compute PnL).

---

## Requirements

- `bash` + `python3`(stdlib only)
- Repo layout with `profiles/renee/skills/*/SKILL.md`
