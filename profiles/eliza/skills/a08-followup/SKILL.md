---
name: a08-followup
description: >-
  Eliza Monday A-08 value follow-up on Sunday lock only: no re-score / no
  re-rank; skip Avoid 🔴 and names missing numeric Sunday valuation_score;
  repeat valuation_score verbatim; Today spot / Sunday lock FV / Display
  upside % cite-only; no invented prices or FV; never emits tm_score.
---

# A-08 follow-up — Monday value follow-up

**Owner:** Eliza · **Train:** formal when standalone (Draft → Zoe → Eliza revise) · Helios-aligned **A-08**  
**Load with:** Sunday lock **revised** pack (prefer JSON), `investment/yahoo-finance-data-fetch` for spot context only  
**Not:** width re-score · re-rank · inventing `valuation_score` · inventing prices / FV · any `tm_score`

Label "Not investment advice". Source grading: `📊 Data` / `📰 News`.

---

## When to use

- **Monday** follow-up on **Sunday lock** value names only  
- Brief status / tape note after weekend pack is locked  
- **Not** daily value-session full desk pack; **not** weekly width revise; **not** earnings preview (use `earnings-preview`)
- **Session summary:** A-08 is a **follow-up carve-out** — full `## Session summary` block **not required** (unlike value-session / width). Optional 2–3 bullet stance OK; Zoe should **not** REJECT solely for missing Session summary on A-08.

---

## Free data only

Published Sunday revised pack · Yahoo Finance · public IR headlines if needed  
**Banned:** FactSet / Bloomberg / LSEG · invented spots · invented Sunday scores · invented FV · holdings / entry prices

---

## Hard rules — no re-score / no re-rank

1. **Universe** = Sunday lock only (prefer `*-revised.json` / revised md)  
2. Process **🟢 Candidate** and **🟡 Watch** only  
3. **Skip 🔴 Avoid** entirely  
4. **Skip** any name **missing numeric** Sunday `valuation_score` — do not carry forward `N/A` selected row; do not invent scores  
5. For each included name: **repeat `valuation_score` verbatim** from Sunday lock  
6. Other missing fields → `N/A` OK; **no invented prices** (spot miss → `attempted + miss`)  
7. **Sunday lock FV** = verbatim from Sunday revised JSON `fv_range` (or the pack's already-published FV string). Missing → `attempted + miss`. **Never invent FV.**  
8. **Display upside %** = cited FV / today spot − 1. If either input is miss → `attempted + miss`.  
9. **Never** change `valuation_score`, `width_verdict`, ranks, or five-factor weights because today's display upside moved  
10. **Never** emit `tm_score`

---

## Output shape (short markdown)

### Header

- Session date · Sunday lock week id · `as_of` (required)  
- Optional: `generated_at` / `data_delay`  
- Hard line: A-08 **does not change** `valuation_score`, ranks, or `width_verdict` — Display upside vs today does not change score/verdict

### Per-name block (only 🟢/🟡 with numeric Sunday score)

| Field | Rule |
|-------|------|
| Ticker | from Sunday lock |
| Today spot / % | free data or `attempted + miss` — **never invent** |
| Sunday lock FV | **verbatim** from Sunday revised JSON `fv_range` — **never invent FV** |
| Display upside % | cited FV / today spot − 1; miss → `attempted + miss` |
| Sunday `valuation_score` (verbatim) | **verbatim** copy |
| `width_verdict` | cite published only — **not** re-scored from today's upside |
| Note | 1–3 lines tape / catalyst context; do not change score |

Example table (exact header — cite only; skip 🔴 and missing numeric scores):

| Ticker | Today spot / % | Sunday lock FV | Display upside % | Sunday `valuation_score` (verbatim) | `width_verdict` | Note |
|--------|----------------|----------------|------------------|---------------------------------------|-----------------|------|
| … | … | … | … | … | … | … |

### Sources

```markdown
## Sources
- Sunday lock: <revised pack basename> · as_of …
- 📊 Data: Yahoo · <date> · …
- Misses: <ticker or field>: attempted + miss
```

---

## Save / deliver

Prefer short note under analysis / A-08 path after Zoe, or embed appendix in Monday desk flow.  
**3-layer** for user-facing revised file.  
Self-revise after Zoe on A-08 when challenge applies — still **no re-score**.

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`  
- **Never** re-score / re-rank / recompute five-factor composite  
- **Never** invent prices, FV, or Sunday `valuation_score`  
- Display upside vs today **does not** change `valuation_score` / `width_verdict` / ranks  
- Skip-without-score / skip-🔴 violations → **Zoe REJECT** territory

---

## Banned

- Re-running `valuation-screener` arithmetic for A-08  
- Publishing Avoid 🔴 or N/A-score names as follow-up rows  
- Inventing FV or changing verdict because today's upside moved  
- FactSet/Bloomberg/LSEG language without public URL  
- Blending T&M BUY/WATCH into value follow-up verdicts
