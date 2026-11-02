---
name: fx-us-uk-bridge
description: >-
  christina: eight FX majors tape + FX forecast (Range Daily+Weekly, Obs
  entry/cut/TP, FX_*, Daily≤2 full-Obs, Weekly DXY Range) + US↔UK/LSE/gilt
  transmission + FX→emily bridge. No silent FX, no forwards/NDF/IV, no
  rewrite of emily 10-row tape.
---

# FX US–UK bridge — tape + forecast + US/UK bridge

**Owner:** christina · rates  
**Load order:** curve → real → fedwatch → bond-etf → **this skill** → trunk  
**Not:** rewrite emily ten columns · invent forwards/NDF/IV · onshore CNY · silent FX · `C_*`↔`FX_*`

---

## When to use

- Every session: mandatory **eight-row majors tape**  
- Every session: **FX forecast view** (observation levels; Daily/Weekly all eight rows need **Range** or `miss`)  
- Explain USD vs LSE/gilt same-ccy/cross-ccy (supports bond-etf **FX gate**)  
- Write **FX→emily** one line / one paragraph  

---

## Quote convention + polarity (hard)

| Pair | Yahoo | Quote | `FX_LONG` meaning |
|------|-------|-------|----------------|
| DXY | `DX-Y.NYB` | index | USD basket up |
| EURUSD | `EURUSD=X` | **USD per 1 EUR** | quote up = USD weaker vs EUR |
| GBPUSD | `GBPUSD=X` | **USD per 1 GBP** | same vs GBP |
| USDJPY | `USDJPY=X` | **JPY per 1 USD** | quote up = USD stronger |
| USDCHF | `USDCHF=X` | **CHF per 1 USD** | same |
| USDCAD | `USDCAD=X` | **CAD per 1 USD** | same; oil adjusts Conf/bridge only |
| AUDUSD | `AUDUSD=X` | **USD per 1 AUD** | quote up = USD weaker vs AUD |
| USDCNH | `USDCNH=X` | **CNH per 1 USD** | offshore; ❌ invent onshore |

`FX_LONG` = **that row’s quote number rises** (DXY exception = basket strength). ❌ wrong convention inverts Signal.

### Obs geometry (hard · when levels complete)

With Last + Obs cut + Obs TP (USD-per-XXX per quote convention; geometry follows **quote number**, not “USD strong/weak” colloquial):

| Signal | Geometry |
|--------|----------|
| `FX_LONG` | **TP > Last** and **cut < Last** |
| `FX_SHORT` | **TP < Last** and **cut > Last** |

Geometry conflicts Signal → **delete full Obs set** (entry/cut/TP) or switch to `FX_WAIT`. ❌ LLM invent/swap prices to “fit geometry.”

**Daily slots:** `FX_WAIT` (like trunk `B_WAIT`) **does not consume** Daily full Obs TP slot (Daily FX ≤2 counts only non-WAIT rows with full levels).

---

## FX majors tape (mandatory eight rows)

| Pair | Yahoo | Last | Chg | As-of | Note |
|------|-------|------|-----|-------|------|
| DXY | DX-Y.NYB | | | | |
| EURUSD | EURUSD=X | | | | |
| GBPUSD | GBPUSD=X | | | | |
| USDJPY | USDJPY=X | | | | |
| USDCHF | USDCHF=X | | | | |
| USDCAD | USDCAD=X | | | | |
| AUDUSD | AUDUSD=X | | | | |
| USDCNH | USDCNH=X | | | | |

Missing → `miss`. Every row **As-of**; Yahoo lag/weekend → Note `data_delay` (not live pricing).

---

## FX forecast view (locked)

| Pair/Index | Yahoo | Last | Range | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|------------|-------|------|-------|-----------|---------|--------|--------|---------|-------|------|
| DXY | DX-Y.NYB | | | | | | FX_* | | | |
| … (eight rows same as tape) | | | | | | | | | | |

**Range (hard · independent of Obs entry/cut/TP):**
- Range = that row’s quote convention `low–high` (EURUSD/GBPUSD/AUDUSD = USD per 1 foreign; USDJPY = JPY per 1 USD; DXY = index points). **low < high**.
- Daily **and** Weekly: all eight forecast rows **must have Range** or cell exactly `miss` + reason. ❌ blank/dash/single point.
- Range **does not consume** Daily full Obs slots (still ≤2, DXY first then GBPUSD).
- `FX_HOLD`/`FX_WAIT`/`NO_SETUP` **still need Range**; ❌ fill Obs entry/cut/TP.
- `FX_LONG`/`FX_SHORT`: if Obs TP filled → TP must lie inside Range (inclusive); else drop TP or Range → `miss`. ❌ invent prices for geometry.
- Method unchanged: Micro near-term band = Rate scenario (Last±scenario). ❌ auto continuation · ❌ forwards/NDF/IV.
- Weekly: DXY + EURUSD + GBPUSD + USDJPY **Range cannot be omitted** (if unknown `miss` + reason); other four rows Range or `miss`.

**Signal only:** `FX_LONG`/`FX_SHORT`/`FX_HOLD`/`FX_WAIT`/`NO_SETUP`/`miss`  
**Levels require Basis** (Macro Rate scenario + Fed vs peer CB · Micro band · Market vol/narrative + as-of).

**Method:**
1. Macro: USD Rate scenario + Fed vs BoE/ECB/BoJ one line (❌ OIS) — DXY mainly Fed/real rates  
2. Micro: near-term coarse band; Range = Last±scenario (**band**; no auto continuation)  
3. Market: Conf/Invalidation only  
4. ❌ forwards/NDF/IV · ❌ silent crosses (incl. EUR×GBP→EURGBP) · ❌ onshore CNY  

**Gates:**
- Daily full Obs entry/cut/TP **≤2** (DXY then GBPUSD); others still Last+Signal+**Range** (or `miss`)  
- **`FX_WAIT` does not consume Daily full Obs TP slot** (WAIT/`NO_SETUP`/`FX_HOLD` still need Range; no entry/cut/TP)  
- Weekly: **DXY Range mandatory** (may `miss` + reason but row stays); Obs only on LONG/SHORT — ❌ fake TP on HOLD; DXY+EUR+GBP+JPY Range cannot be skipped  
- Calendar inside horizon → Conf↓/`FX_WAIT`  
- No free verifiable Market-Based → Conf≤M  
- FW vs USD Rate scenario conflict → **no FX Obs TP**  
- Geometry vs Signal conflict → delete full Obs or `FX_WAIT`; ❌ LLM invent prices  

**Literacy (no engine):** PPP = optional long-horizon narrative; ARIMA/LSTM = OOU; Market-Based = do not invent forwards.

---

## US ↔ UK/LSE/gilt bridge

- Same bucket: agree/diverge/miss + each leg Ccy  
- GBPUSD large move with wrong-ccy compare → bond-etf **Est/TP miss** (FX gate)  
- GBp vs GBP: disclose  

---

## FX → emily (locked)

1. emily writes two legs/`C_*`  
2. Explain only how GBPUSD/DXY/DFII drive US/UK leg divergence  
3. cite `shared/reports/emily/…` or `miss`  
4. ❌ rewrite ten columns · ❌ `C_*`↔`FX_*`/`B_*`  

Daily: ≥1 sentence. Weekly: one paragraph.

---

## Market mirror (this skill)

Public FX/USD narrative one line may adjust **FX Conf**; oil/gold at most one line and Conf/emily bridge only — ❌ alter Rate Δbp.

---

## Miss ledger (FX rows)

| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| EURUSD=X etc. | FX | Yahoo | | no |

---

## Forbidden

- ❌ forwards/NDF/IV · ❌ onshore CNY · ❌ silent FX · ❌ rewrite emily ten columns  
- ❌ headline-invented Last/Range  
- ❌ Range blank/dash/single point (Daily/Weekly eight rows need Range or `miss` + reason)  
- ❌ LLM invent/swap Obs prices for geometry  
- ❌ `FX_WAIT` consumes Daily full Obs TP slot  
- ❌ `FX_HOLD`/`FX_WAIT`/`NO_SETUP` fill Obs entry/cut/TP  

---

## Checklist

- [ ] Eight-row tape complete or `miss`; each row as-of/`data_delay`  
- [ ] FX forecast: Daily/Weekly all eight **Range** or `miss` + reason; Daily full Obs ≤2 (DXY then GBPUSD); Weekly DXY Range mandatory; Basis before TP  
- [ ] Quote convention + `FX_*` polarity correct; Range = `low–high` (low<high); full-level geometry: `FX_LONG`⇒TP>Last and cut<Last; `FX_SHORT`⇒TP<Last and cut>Last; TP inside Range when present  
- [ ] Geometry conflict → delete full Obs or `FX_WAIT`; `FX_HOLD`/`FX_WAIT`/`NO_SETUP` still need Range, no entry/cut/TP; `FX_WAIT` does not consume Daily full Obs TP slot  
- [ ] GBPUSD/DXY bridge to LSE/emily present  
- [ ] No forwards/IV/onshore fake/cross invention  
- [ ] No ten-column rewrite; ❌ `C_*`↔`FX_*`  
- [ ] After handoff unlock bond-etf Est/Obs finalization  
