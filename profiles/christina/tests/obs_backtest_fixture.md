# christina · rates — Obs backtest fixture (observation hygiene · no PnL)

**Purpose:** Lightweight template for scoring *hygiene rules* given a fake prior rates session + next-day prints.  
**Not:** PnL / returns / execution / broker orders.  
**Mode:** observation only · ETF proxy ≠ cash bond · NO_DB.

---

## Meta
- **As-of (prior session):** 2026-09-21
- **Next-day prints as-of:** 2026-09-22
- **Cadence:** daily lite (fixture)
- **Disclaimer:** Not investment advice · observation only · ETF proxy ≠ cash bond/gilt · **no PnL** · NO_DB

---

## Session summary
- Curve: 2s10s slightly flatter; DGS10 base −5bp (1–4w Rate scenario).
- FedWatch consume-only cite present (fixture path); no cron-run.
- Bond Obs levels (Daily ≤3): TLT · IEF only — LQD/HYG Signal-only.
- FX Obs levels (Daily ≤2): DXY only — majors Last+Signal.
- Miss ledger: DFII5 miss (no invent BE).
- **rates_regime:** easing/mixed — real yields soft; credit ETFs lag gov.
- **Alice pull:** Market insight — soft real yields; gov lean vs credit lag (no full ladder paste).

---

## Market insight
- Curve/rates: 2s10s flatter; DGS10 base −5bp — soft real yields lean.
- Credit vs gov: LQD/HYG lag gov Obs; Dominant macro-led.
- ❌ Desk Risk-on/off → Alice Macro view only.

---

## Prior session — Rate scenario (Δbp · 1–4w)

| Tenor | Horizon | Bull Δbp | Base Δbp | Bear Δbp | FedWatch cite | Invalidation |
|-------|---------|----------|----------|----------|---------------|--------------|
| DGS2 | 1–4w | −15 | −5 | +10 | fixture cite <job-id> | yield leaves envelope |
| DGS10 | 1–4w | −12 | −5 | +8 | fixture cite | |
| DGS30 | 1–4w | −10 | −4 | +6 | fixture cite | |

---

## Gov bond ETF view (prior session draft · B_* only)

| Bucket | ETF | Venue | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|--------|-----|-------|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| ~7–10y | IEF | US | USD | 95.2 | cite scenario band 94.5–96.5 | 94.8 | 93.5 | 97.0 | B_LONG | 1–4w | Dominant: macro-led · Rate scenario Δbp DGS10 · as-of 2026-09-21 | M |
| ~20y+ | TLT | US | USD | 92.1 | cite scenario band 91–94 | 91.5 | 89.8 | 95.0 | B_LONG | 1–4w | Dominant: macro-led · Rate scenario Δbp DGS30 · as-of 2026-09-21 | L |
| ~1–3y | SHY | US | USD | 82.4 | miss | | | | B_WAIT | 1–4w | — | L |
| ~3–7y | IEI | US | USD | 118.0 | miss | | | | NO_SETUP | 1–4w | — | L |
| ~10–20y | TLH | US | USD | 103.5 | miss | | | | B_HOLD | 1–4w | — | L |

**Daily trim:** full Obs entry+cut+TP rows = (≤3): IEF · TLT (2 ≤ 3). Rest Last+Signal only.

---

## Other bond ETF view (LQD/HYG · Signal-only this fixture)

| ETF | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|-----|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| LQD | USD | 108.2 | miss | | | | B_WAIT | 1–4w | — | L |
| HYG | USD | 76.8 | miss | | | | NO_SETUP | 1–4w | — | L |

---

## FX forecast view (prior session · FX_* only · Daily ≤2 full levels)

| Pair/Index | Yahoo | Quote | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|------------|-------|-------|------|-----|-----------|---------|--------|--------|---------|-------|------|
| DXY | DX-Y.NYB | index | 104.2 | cite rates scenario 103–105 | 103.8 | 102.5 | 105.5 | FX_LONG | 1–4w | Dominant: macro-led · Fed/real + Rate scenario · as-of 2026-09-21 | M |
| EURUSD | EURUSD=X | USD/EUR | 1.085 | miss | | | | FX_WAIT | 1–4w | — | L |
| GBPUSD | GBPUSD=X | USD/GBP | 1.302 | miss | | | | NO_SETUP | 1–4w | — | L |

**Daily trim:** FX full levels ≤2 — DXY only (1 ≤ 2).

---

## Miss ledger

| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| DFII5 | FRED | FRED DFII5 | series gap in fixture | no |

---

## Next-day prints (fixture · Yahoo-shaped · fake)

| Symbol | US print (2026-09-22) | Note |
|--------|----------------------|------|
| TLT | TLT · 92.8 · +0.8% | inside prior Est band |
| IEF | IEF · 95.6 · +0.4% | inside prior Est band |
| DXY | DX-Y.NYB · 104.0 · −0.2% | still inside Est band |
| LQD | LQD · 108.0 · −0.2% | Signal-only — no levels to mark |
| HYG | HYG · 76.5 · −0.4% | NO_SETUP — no hygiene hit |

---

## Hygiene scorecard (what the harness asserts · no PnL)

| Rule | Expected |
|------|----------|
| `## Session summary` present | yes |
| `## Market insight` present | yes |
| No desk Risk-on/off final | yes |
| `rates_regime` OR notes optional | yes (optional field present) |
| Bond view table AND/OR FX forecast table with Signal | yes (both) |
| Next-day prints block | yes |
| Declares observation only / no PnL / hygiene | yes |
| Signal column uses `B_*`/`FX_*`/`NO_SETUP`/`miss` only | yes |
| ❌ bare `BUY` as Signal | none |
| Daily full bond Obs levels ≤3 | yes (2 here) |
| FX full levels ≤2 when daily | yes (1 here) |
| Basis present when Obs levels filled | yes |
| Ccy present on bond rows when table has Ccy | yes |
| No PnL / ROI / return % columns | yes |

**Scoring note:** Mark levels as “inside / outside Est band” only as *observation hygiene*; **do not** compute PnL or fill quantity/order fields.
