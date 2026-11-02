# eliza tests — value-sleeve audit harness

Static consistency + lightweight **value-session / width / A-08** hygiene for the eliza P-VAL profile.  
**No network · no API keys · no PnL.**

English OK.Observation only · never `tm_score` · cite Sunday lock only.

---

## Quick start

From repo root:

```bash
./profiles/eliza/tests/run_eliza_audit.sh
```

Or:

```bash
bash profiles/eliza/tests/run_eliza_audit.sh
```

Exit `0` = all checks pass · non-zero = fail (CI-friendly).

Sleeve wrapper (eliza + renee + desk):

```bash
./scripts/run-equity-sleeve-audits.sh
```

---

## What it checks

| # | Suite | What |
|---|--------|------|
| 1 | **P0 skills exist** | `value-session` · `valuation-width` · `a08-followup` + existing `earnings-preview` / `earnings-analysis` / `comps-analysis` |
| 2 | **Skill keywords** | Each P0 bans `tm_score`; session/width require `## Session summary` + `as_of`; width Candidate ≥+15% + `scoring-engine-v4` / E5 never blend; A-08 no re-score + `as_of` / `generated_at`\|`data_delay`\|provenance |
| 3 | **SOUL + checklist** | Mention the three new P0 skills |
| 4 | **apply-to-hermes** | `ELIZA_SKILLS` includes the three P0 skills |
| 5 | **Fixture hygiene** | Good fixtures (PASS)+ bad fixtures as **negative controls** (must FAIL hygiene)— value-session · width · A-08 |
| 6 | **Secrets / host paths** | Soft grep: Telegram · `API_KEY=` · absolute `~/.hermes/profiles` in skill bodies |

---

## Files

```text
profiles/eliza/tests/
  README.md                      ← this file
  run_eliza_audit.sh             ← runner(exit nonzero on fail)
  value_session_fixture.md       ← good value-session (hygiene PASS)
  width_fixture.md               ← good width revise snippet (hygiene PASS · as_of)
  a08_fixture.md                 ← good A-08 (verbatim Sunday · skip 🔴 · as_of)
  fixtures/
    value_session_bad.md         ← bad(negative control)
    width_bad.md                 ← bad(negative control)
    a08_bad.md                   ← bad re-score / invent / tm_score(negative control)
```

---

## Fixture template (how to reuse)

1. Copy `value_session_fixture.md` / `width_fixture.md` / `a08_fixture.md` → fill real revise drafts.
2. Always stamp `as_of` (session / width / A-08); optional `generated_at` / `data_delay`.
3. Cite Sunday lock `valuation_score` only — never emit `tm_score`; never bare `Score` / `Adj`. Daily / A-08 tables include Sunday lock FV + Display upside; weekly tables include Spot, FV Range, Upside %. Cite only; never invent FV; never change verdict from the display upside.
4. Width: numeric `valuation_score` on selected rows; unscorable → Omissions (not selected `N/A`).
5. A-08: verbatim Sunday scores; skip 🔴 and missing numeric; no invented prices.
6. Re-run the script — section 5 scores hygiene only (**never** compute PnL).

---

## Requirements

- `bash` + `python3` (stdlib only)
- Repo layout with `profiles/eliza/skills/*/SKILL.md`
