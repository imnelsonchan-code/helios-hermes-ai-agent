---
name: bond-etf-tape
description: >-
  christina: gov maturity ladder (incl TLT) + LQD/HYG tape. Method A
  scenario→Est band/Obs entry·cut·TP with Ccy and Basis. R²/HYG/TLT/FX
  gates from backtest. Daily ≤3 full rows. ETF≠cash literacy. Free Yahoo+FRED.
---

# Bond ETF tape — government / credit bond ETF view

**Owner:** christina · rates  
**Load order:** curve → real → fedwatch → **this skill** → fx → trunk  
**Not:** fake OAS/DV01/CTD · silent FX · peer fill prices · bare BUY · yield-continuation auto Est · DB  

---

## When to use

- Every session: assemble **Gov ladder** + **Other (LQD/HYG)**  
- Use trunk/curve **Rate scenario** (fixed or draft) for Method A translation  
- Daily: all rows Last+Ccy; full levels **≤3**; Weekly: both tables as complete as possible  

### Fill timing (hard)

| Phase | May fill | Wait for gate |
|------|------|------|
| Early (before FX) | **Last+Ccy** (full universe) | — |
| After `fx-us-uk-bridge` handoff (or FX already `miss`) | **Est/Obs entry/cut/TP** final | FX-gate |
| FX not done | Est/TP mark **`FX-gate pending`** or leave blank; ❌ treat as final | — |

---

## Universe (SSOT · do not invent)

### Gov — US

| Bucket | ETF | Ccy |
|--------|-----|-----|
| ~1–3y | `SHY` | USD |
| ~3–7y | `IEI` | USD |
| ~7–10y | `IEF` | USD |
| ~10–20y | `TLH` | USD |
| ~20y+ | `TLT` | USD |

### Gov — LSE/UCITS

| Bucket | Prefer | Alt | Ccy note |
|--------|--------|-----|----------|
| 1–3y | `IBTA.L` | — | USD |
| 7–10y | **`IDTM.L`** | `IBTM.L` | label actual (IDTM≈USD; IBTM often GBP) |
| 20y+ | **`IDTL.L`** | `IBTL.L` | label actual (IDTL≈USD; IBTL often GBP) |
| 3–7y/10–20y | — | — | **`miss`** (no SSOT peer; ❌ invent) |

### Gilts

`IGLS.L` · `IGLT.L` · (weekly optional) `INXG.L` — Ccy GBP/GBp as stated.

### Other (required)

`LQD` · `HYG` — USD; forecast columns required (cells may `miss` but rows stay).

Hedged share classes (IBTE/IBTG) → OOU.

---

## Table columns (locked)

**Required:** `Bucket` (gov) · `ETF` · `Venue` · **`Ccy`** · `Last` · `Est value` · **`Obs entry`** · **`Obs cut loss`** · **`Obs TP`** · `Signal` · `Horizon` · `Invalidation` · **`Basis`** · `Conf`

**Signal:** `B_LONG`/`B_SHORT`/`B_HOLD`/`B_WAIT`/`NO_SETUP`/`miss`  
❌ bare BUY/WATCH/NO_SIGNAL

**Levels require Basis** (name Macro/Micro/Market + as-of). No Basis → do not fill entry/cut/TP.

---

## Method A steps (default)

1. **Map tenor:** SHY/IBTA↔`DGS2`; IEF/IDTM↔`DGS10`; TLT/IDTL↔`DGS30`; gilt→UK cite or `miss`  
2. **Read Rate scenario** (bull|base|bear Δbp + FW cite) — **scenario quality first**  
3. **Coarse sensitivity disclose:** “coarse proxy, **not** terminal DV01”; optional β̂; **low R²/counter-intuitive sign → skip β** → Method B or `miss`  
4. **Est:** translate to price/**band** (bull|base|bear); same Ccy as Last  
5. **Obs entry/cut/TP:** near-term price band; TP toward Est; Basis required  
6. **Failure → `miss`:** no Last/no Ccy/no scenario/cannot disclose proxy/gate triggered  

**❌ Forbidden:** “recent rate momentum auto-extrapolation” as Est/TP (backtest direction accuracy ~0.46–0.53).

### Method B (fallback)

FRED/FW both miss: Est≈20d mid/MA20; rates nudge Conf only.

### Method C (weekly footnote)

Same bucket agree/diverge/miss; **each leg own Ccy/Est**; no peer fill, no silent FX.

---

## Backtest gates (must)

| Gate | Behavior |
|------|------|
| **R²/β** | Low/unstable (often SHY) → Est/TP `miss` or Method B |
| **HYG** | Default **spread-led/mixed**; no spread narrative → Est=`miss`; rates nudge Conf only |
| **TLT** | **Conf≤M** (even if R²+FW aligned stay cautious); large MAE |
| **proxy-only** | ETF/LSE proxy no cash peer → **Conf≤L** |
| **TLT ∩ proxy-only** | Both → Conf=`min(TLT, proxy-only)`=**≤L** |
| **Cross-ccy/FX** | Ccy mismatch or GBPUSD/DXY large move with wrong comparison → Est/TP `miss`; **wait for FX handoff** before final |
| **FW conflict** | Opposite scenario → `B_WAIT`/no Obs TP/Conf≤L |
| **Est shape** | Prefer **band**, not fake precision point |
| **Daily ≤3** | Pick highest Conf×|Est−Last| full rows only; rest Last+Ccy+Signal |
| **Est-after-FX** | Full levels only after FX bridge (or FX miss); early fill Last+Ccy only |

Credit vs Gov: LQD/HYG drivers = rates **+** credit risk appetite; Basis vocab: `rates-led`/`spread-led`/`mixed`.

---

## Daily vs Weekly

| | Daily | Weekly |
|--|-------|--------|
| Last+Ccy | full universe | full universe |
| Full entry+cut+Est+TP | **≤3** (both tables combined) | rows as complete as possible; cells may miss |
| Horizon | 1–4w (short end 1–2w; TLT/HYG shorter) | 4–12w |
| Peer/Method C | may omit | footnote OK |

---

## Literacy footnote (every report · hand to trunk Footer)

> ETF proxy ≠ cash bond/gilt/single CTD; quote currency in **Ccy**; observation levels not orders; coarse proxy ≠ DV01.

---

## Shadow (eval only)

`rates_signal` · `shadow_rates_score` · `rates_signal_breakdown`  
❌ bare `score` · ❌ mix `tm_score`/`valuation_score`/`commodity_signal`

---

## Forbidden

- ❌ Fake OAS/DV01/CTD · ❌ silent FX · ❌ peer fill prices  
- ❌ Invent LSE 3–7/10–20 tickers  
- ❌ bare BUY · ❌ quantity/order type  
- ❌ yield-continuation auto Est  
- ❌ Tradefeeds/paid holdings  

---

## Checklist

- [ ] Gov ladder + LQD/HYG rows present (missing price=`miss`, rows do not vanish)  
- [ ] Every row Ccy; levels same currency  
- [ ] Last+Ccy early OK; Est/Obs TP **after FX** (or pending/miss)  
- [ ] Method A disclose coarse proxy≠DV01  
- [ ] Gates: R²/HYG/TLT/FX/FW  
- [ ] Daily ≤3 full rows; Basis before TP  
- [ ] Prefer IDTM.L/IDTL.L; no invented peer  
- [ ] Literacy footnote to trunk  
