# eliza · valuation-width — hygiene fixture (GOOD · Track A revise snippet)

**Purpose:** Lightweight template for scoring *width revise hygiene* on a fake Track A chapter.  
**Not:** PnL / runner arithmetic rewrite / `tm_score`.  
**Mode:** observation only · P-VAL · map Score/Adj → Valuation Score.

---

## Meta
- **Week id:** 2026-W38
- **as_of:** 2026-09-21T18:00:00Z
- **fv_engine:** pe_band_screen
- **Disclaimer:** Not investment advice · hygiene only · **no PnL** · never `tm_score`

Hard line: revise maps `composite_score` → `valuation_composite` / `valuation_score`; rename Score/Adj; never rewrite runner arithmetic.

---

## Session summary
- Valuation stance: Candidate tilt intact; Watch names stable; no Avoid promotions from quality alone.
- Material Candidates: MNO `valuation_score` 78 · upside ≥+15%; PQR 65 Watch.
- Omissions: STU unscorable five-factor → Omissions (not selected N/A).
- E5: one overlap WARN only — ranks unchanged.
- **Alice pull: ** Market insight — Candidate tilt; MNO leads (do not paste full table).

---

## Market insight
- Width tape: cheap/Candidate tilt intact vs prior week; Watch stable.
- Mechanism: MNO (`valuation_score` 78) ≥+15% Candidate; PQR Watch — no re-rank.
- ❌ Desk Risk-on/off → Alice Macro view only.

---

## News/Market check (Eliza-topic)
- 📰 News: miss(fixture)— attempted + miss
- 📊 Market tape: value vs growth dispersion quiet · Candidate cluster OK

---

## Lenses
- Macro: overlay only — do not set desk Risk-on/off
- Micro: Track A Candidate/Watch mix
- Market: quiet tape · Conf effect neutral
- Dominant: micro-led

---

## Track A — Large + Mid Cap

| Ticker | Spot (as_of) | FV Range | Upside % | Valuation Score | Quality-Adjusted Score | `valuation_score` | `width_verdict` | Note |
|--------|--------------|----------|----------|-----------------|------------------------|-------------------|-----------------|------|
| MNO | 120.00 | `$138–$162 (reasonable $150)` | `+25.0%` | 78 | 74 | 78 | Candidate | ≥+15% + quality OK |
| PQR | 88.00 | `$90–$99 (reasonable $94)` | `+6.8%` | 65 | 63 | 65 | Watch | |
| VWX | 40.00 | `$32–$36 (reasonable $34)` | `−15.0%` | 58 | 55 | 58 | Avoid | quality gate noted |

---

## Omissions
- STU: missing numeric five-factor score — omitted from selected

---

## Sources
- 📊 Data: runner / Finviz / Yahoo · as_of 2026-09-21
- Omissions: STU: unscorable
- Numbers cited from fixture scan JSON `fv_range` ; not recomputed here.

---

## Hygiene scorecard (what the harness asserts)

| Rule | Expected |
|------|----------|
| `## Session summary` present | yes |
| `## Market insight` present | yes |
| News/Market + Lenses present | yes |
| No desk Risk-on/off final call | yes |
| Track A table has `valuation_score` + `width_verdict` | yes |
| FV Range column | yes |
| Upside % column | yes |
| no lone `?` in FV Range | yes |
| No Score / Adj columns | yes |
| No `tm_score` | yes |
| No selected `N/A` valuation_score | yes |
| `as_of` present | yes |
