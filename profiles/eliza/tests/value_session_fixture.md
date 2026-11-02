# eliza · value-session — hygiene fixture (GOOD · synthetic revised)

**Purpose:** Lightweight template for scoring *value-session hygiene* on a fake revised daily session.  
**Not:** PnL / returns / execution / holdings.  
**Mode:** observation only · P-VAL · cite Sunday lock only.

---

## Meta
- **Session date:** 2026-09-22
- **as_of:** 2026-09-22T20:05:00Z
- **generated_at:** 2026-09-22T20:10:00Z(fixture)
- **Sunday lock week:** 2026-W38
- **Disclaimer:** Not investment advice · hygiene only · **no PnL** · never `tm_score`

Hard line: this session **does not change** `valuation_score`, five-factor weights, or weekly width ranks.

---

## Session summary
- Valuation stance: **fair→cheap tilt** vs Sunday lock — Candidates still lead; no Avoid promotions.
- Material movers: ABC cited Sunday `valuation_score` 72 AND Sunday lock FV reasonable $50.00 (display upside +21.4% vs today); DEF cited 61 / reasonable $90.00 (+2.3%); GHI skipped (no numeric Sunday score).
- Tape: large-cap value quiet; no invented FV / no width_verdict changes.
- Coverage: 2 movers with Sunday cites · 1 miss noted under Sources.
- Data quality: Yahoo spots OK; Sunday lock pack basename only.
- **Alice pull: ** Market insight — fair→cheap tilt; ABC Candidate holds (do not paste full table).
- Provenance stamped: `as_of` required.

---

## Market insight
- Valuation tape: cheap tilt intact vs Sunday lock; Candidates lead without Avoid promotions.
- Mechanism: ABC (`valuation_score` 72) holds Candidate; DEF Watch fair — no re-rank.
- ❌ Desk Risk-on/off → Alice Macro view only.

---

## News/Market check (Eliza-topic)
- 📰 News: miss(fixture)— attempted + miss
- 📊 Market tape: large-cap value quiet · staples/financials mixed

---

## Lenses
- Macro: cite Alice brief if present — overlay only; do not set desk Risk-on/off
- Micro: Sunday lock Candidates intact
- Market: quiet tape · Conf effect neutral
- Dominant: micro-led

---

## Data snapshot
- Coverage note: Sunday lock revised pack present; 1 name missing numeric score → skip cite.

---

## Value movers vs Sunday lock

Fixture cites only (not a live pack): 

| Ticker | Today spot / % | Sunday lock FV | Display upside % | Sunday `valuation_score` | `width_verdict` | Note |
|--------|----------------|----------------|------------------|--------------------------|-----------------|------|
| ABC | 41.20 / +1.1% | reasonable $50.00 | +21.4% | 72 | Candidate | cite Sunday lock · no re-rank |
| DEF | 88.00 / −0.4% | reasonable $90.00 | +2.3% | 61 | Watch | cite Sunday lock |
| GHI | miss | attempted + miss | attempted + miss | — | — | skip: no numeric Sunday score |

---

## Sources
- 📊 Data: Yahoo · 2026-09-22 · fixture
- Sunday lock: `2026-W38-valuation-width-revised.md` · as_of 2026-09-21
- FV cited from Sunday lock JSON `fv_range` ; upside = cited reasonable / today spot − 1 ; not a new model.
- Misses: GHI Sunday score: attempted + miss

---

## Hygiene scorecard (what the harness asserts)

| Rule | Expected |
|------|----------|
| `## Session summary` present | yes |
| `## Market insight` present | yes |
| News/Market + Lenses present | yes |
| No desk Risk-on/off final call | yes |
| Valuation stance present | yes |
| Sunday `valuation_score` cites | yes |
| Sunday lock FV column | yes |
| Display upside column | yes |
| No `tm_score` | yes |
| `as_of` present | yes |
| No bare Score / Adj columns | yes |
