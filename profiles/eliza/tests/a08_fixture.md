# eliza · A-08 follow-up — hygiene fixture (GOOD · Sunday lock only)

**Purpose:** Lightweight template for scoring *A-08 follow-up hygiene* on a fake Monday note.  
**Not:** width re-score · re-rank · invent prices / FV · `tm_score`.  
**Mode:** observation only · P-VAL · verbatim Sunday lock.

---

## Meta
- **Session date:** 2026-09-22 (Monday A-08)
- **Sunday lock week:** 2026-W38
- **as_of:** 2026-09-22T14:30:00Z
- **generated_at:** 2026-09-22T14:35:00Z(fixture)
- **Disclaimer:** Not investment advice · hygiene only · **no PnL** · never `tm_score`

Hard line: A-08 **does not change** `valuation_score`, ranks, or `width_verdict` — repeat Sunday lock **verbatim**. Display upside vs today does not re-score.

---

## Follow-up notes
- Stance: Candidates still lead vs Sunday lock; Watch names quiet.
- Skip 🔴 Avoid entirely (e.g. VWX Avoid not followed).
- Skip names missing numeric Sunday `valuation_score` (GHI).
- Spots from Yahoo only; miss → `attempted + miss` — **no invented prices**.
- Sunday lock FV verbatim from Sunday revised JSON `fv_range`; Display upside % = cited FV / today spot − 1 — **no invented FV** · no re-score.

---

## Names (🟢 Candidate / 🟡 Watch with numeric Sunday score only)

| Ticker | Today spot / % | Sunday lock FV | Display upside % | Sunday `valuation_score` (verbatim) | `width_verdict` | Note |
|--------|----------------|----------------|------------------|-------------------------------------|-----------------|------|
| ABC | 41.20 / +0.3% | reasonable $50.00 | +21.4% | 72 | Candidate | cite Sunday lock · no re-score |
| DEF | miss | reasonable $90.00 | attempted + miss | 61 | Watch | spot miss · score and FV verbatim |
| VWX | — | — | — | — | Avoid 🔴 | **skipped** — A-08 skips 🔴 |
| GHI | — | — | — | — | — | **skipped** — no numeric Sunday score |

---

## Sources
- Sunday lock: `2026-W38-valuation-width-revised.md` · as_of 2026-09-21
- 📊 Data: Yahoo · 2026-09-22 · fixture
- FV cited from Sunday lock JSON `fv_range` ; upside = cited reasonable / today spot − 1 ; not a new model.
- Misses: DEF spot: attempted + miss; GHI Sunday score: skip; VWX 🔴: skip

---

## Hygiene scorecard (what the harness asserts)

| Rule | Expected |
|------|----------|
| `as_of` present | yes |
| Verbatim Sunday `valuation_score` cites | yes |
| Sunday lock FV column | yes |
| Display upside column | yes |
| Skip 🔴 / Avoid noted | yes |
| No `tm_score` | yes |
| No invent / re-score affirmative | yes |
