# christina · rates — Obs backtest BAD fixture（negative control · must FAIL）

**Purpose:** Intentional hygiene violations so the harness negative-control check passes.  
**Not** a real session. Do not copy into production drafts.

**Disclaimer:** Not investment advice · observation only · this file is a deliberate fail case.

---

## Session summary
- Bad fixture: Signal column deliberately uses bare BUY and wrong-namespace `tm_score`.
- Harness must detect and fail this file.

---

## Gov bond ETF view（violations on purpose）

| Bucket | ETF | Venue | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|--------|-----|-------|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| ~20y+ | TLT | US | USD | 92.1 | 91–94 | 91.5 | 89.8 | 95.0 | BUY | 1–4w | fake | L |
| ~7–10y | IEF | US | USD | 95.2 | miss | | | | tm_score | 1–4w | — | L |

---

## Next-day prints（fixture · fake）

| Symbol | US print | Note |
|--------|----------|------|
| TLT | 92.8 | ignore — negative control only |
