# renee · daily T&M session — hygiene fixture (GOOD · synthetic revised)

**Purpose:** Lightweight template for scoring *T&M session hygiene* on a fake revised daily report.  
**Not:** PnL / score rewrite / valuation blend.  
**Mode:** observation only · P-TM · live pack truth.

---

## Meta
- **Session date:** 2026-09-22
- **Cadence:** daily
- **Regime:** trending · SPY ADX 28 · VIX 14
- **Disclaimer:** Not investment advice · hygiene only · **no PnL** · no score rewrite

Hard line: ranking from live pack only — **no score rewrite**.

---

## Session summary
- T&M regime: **trending** (SPY ADX 28) — Option G not suppressing effective BUY.
- Top movers: AAA `tm_score` 82 BUY; BBB 71 BUY; CCC 58 WATCH (pack truth).
- Funnel cite deferred to eval JSON when present; this fixture focuses on session trunk.
- No `valuation_score` in ranking — E5 separate screens.
- Coverage: 3 names · 1 miss under Sources.
- **Alice pull:** THIS file `## Market insight` — trending breadth + AAA/BBB leadership (do not paste full section). Alice macro brief miss does not go here.

---

## Market insight
- Tape: risk-on leadership in high-`tm_score` names; breadth supportive of trend regime.
- Mechanism: SPY ADX 28 → trend-continuation bias; VIX 14 calm — size overlay OK.
- Watch: if breadth thins while AAA holds → Conf↓; do not set desk Risk-on/off.
- ❌ Desk Risk-on/off → Alice Macro view only.

---

## News/Market check (Renee-topic)
- 📰 News: miss (fixture) — attempted + miss
- 📊 Market tape: index range tight · leadership concentrated in AAA/BBB

---

## Lenses
- Macro: No brief. / miss (Alice macro brief absent) · trend regime overlay (ADX 28) — do not set desk Risk-on/off
- Micro: pack BUY cluster AAA/BBB
- Market: calm VIX/volume OK · Conf effect neutral
- Dominant: market-led

---

## Ranking (live pack)

| Ticker | `tm_score` | Bracket | Note |
|--------|------------|---------|------|
| AAA | 82 | BUY | pack truth · breakdown present upstream |
| BBB | 71 | BUY | pack truth |
| CCC | 58 | WATCH | pack truth |

---

## Sources
- 📊 Data: live tm pack · fixture-basename · as_of 2026-09-22
- Eval: N/A + pending (funnel checked in separate fixture)
- Misses: DDD pack row: attempted + miss

---

## Hygiene scorecard (what the harness asserts)

| Rule | Expected |
|------|----------|
| `## Session summary` present | yes |
| `## Market insight` present | yes |
| News/Market + Lenses present | yes |
| No desk Risk-on/off final call | yes |
| `tm_score` movers present | yes |
| No `valuation_score` blend in ranking | yes |
| No weekly Option G suppress-as-applied | yes (daily fixture) |
