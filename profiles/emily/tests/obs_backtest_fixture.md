# emily · commodities — Obs backtest fixture (observation hygiene · no PnL)

**Purpose:** Lightweight template for scoring *hygiene rules* given a fake prior session + next-day prints.
**Not:** PnL / returns / execution / broker Emily.
**Mode:** observation only.

---

## Meta
- **As-of (prior session):** 2026-09-21
- **Next-day prints as-of:** 2026-09-22
- **Cadence:** daily lite (fixture)
- **Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7) · **no PnL**

---

## Session summary
- Oil dual-leg (CL vs BZ) stayed tight; Conf capped L on proxy legs elsewhere.
- Softs: Cocoa Signal `C_WAIT` — no full Obs levels (Basis gate).
- Insight/Direction/Forecast cited upstream drafts (fixture paths below).
- Daily trim: ≤3 full levels — Oil · Gold only (2 ≤ 3).
- **commodity_regime:** Neutral — mixed precious vs energy lean; no Crisis trigger.
- **Alice pull:** Market insight — Neutral regime; precious vs energy lean (do not paste full ten-column).

---

## Market insight
- Drivers: precious soft vs energy lean — mixed complex.
- Dual-leg: Oil CL vs BZ note (fixture).
- ❌ Desk Risk-on/off → Alice Macro view only.

---

## Prior session — Direction cite (DIR_* · not Signal)

| Commodity | Direction | Conf |
|-----------|-----------|------|
| Gold | DIR_BULLISH | M |
| Oil | DIR_TWO_WAY | L |
| Cocoa | DIR_NEUTRAL | M |

---

## Prior session — Forecast cite (Scenario / Est band)

| Commodity | Horizon | Base | Est band |
|-----------|---------|------|----------|
| Gold | 1–4w | real-yield ease + ETF flow | 2650–2720 |
| Oil | 1–4w | inventory miss + CL–BZ two-way | 68–74 |
| Cocoa | 1–4w | range soft / supply ok | miss |

---

## Trade map (prior session draft · C_* only)

| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis (+ Dominant) | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|---------------------|------|
| Gold | C_BUY | 2680 | cite forecast 2650–2720 | 2665 | 2620 | 2710 | 1–4w | break 2620 | Dominant: macro-led · cite Forecast/Scenario/Est Gold | M |
| Oil | C_WAIT | 71.2 | cite forecast 68–74 | | | | 1–4w | EIA surprise | — | L |
| Cocoa | C_WAIT | 9200 | miss | | | | 1–4w | ICE inventory | — | M |
| Silver | NO_SETUP | 31.2 | miss | | | | 1–4w | — | — | L |
| Copper | miss | | miss | | | | | data miss | — | L |

**Daily trim:** full Obs entry+SL+TP rows (≤3): Gold  
**Remaining:** Signal (+Invalidation) only. No Forecast/Est cite → do not fill full levels. Full-level rows must have Obs TP at cited Est band near-term.

---

## Next-day prints (fixture · Yahoo-shaped · fake)

| Commodity | US print (2026-09-22) | Note |
|-----------|----------------------|------|
| Gold | XAU · gold-api · 2695 · +0.6% | inside prior Est band |
| Oil | CL=F · 69.8 · −2.0% | still inside Est band; two-way lean intact |
| Cocoa | CC=F · 9150 · −0.5% | no levels to mark |
| Silver | XAG · gold-api · 31.0 · −0.6% | NO_SETUP — no hygiene hit |
| Copper | HG=F · miss | still miss |

---

## Hygiene scorecard (what the harness asserts · no PnL)

| Rule | Expected |
|------|----------|
| `## Session summary` present | yes |
| `## Market insight` present | yes |
| `commodity_regime` present | yes |
| No desk Risk-on/off final call | yes |
| Signal column uses `C_*` / `NO_SETUP` / `miss` only | yes |
| ❌ bare `BUY` as Signal | none |
| ❌ `DIR_*` as Signal value | none (DIR_* stays in Direction cite) |
| Daily full Obs levels ≤3 | yes (1 here) |
| Basis cites Forecast/Scenario/Est when levels filled | yes |
| No PnL / ROI / return % columns | yes |

**Scoring note:** Mark levels as “inside / outside Est band” only as *observation hygiene*; **do not** compute PnL or fill quantity/order fields.
