---
name: real-rates
description: >-
  christina: FRED real yields DFII5/DFII10 + NY Fed SOFR cite-or-miss.
  Never invent breakevens or SOFR. Feeds Macro lens and FX→emily bridge stub.
---

# Real rates — real yields + SOFR

**Owner:** christina · rates  
**Load order:** curve-watch → **this skill** → fedwatch → bond-etf → fx → trunk  
**Not:** invented breakeven/inflation expectation curve · fake TIPS OAS · invented SOFR · SOFR substituting for nominal curve  

---

## When to use

- Every session: pull `DFII5`/`DFII10` when available  
- Every session: **cite-or-miss** NY Fed **SOFR** (USD overnight funding/liquidity one-liner)  
- One **real rates** line for Rate scenario / FX→emily bridge  
- Missing → `miss` (do not fill nominal minus “estimated” inflation; do not invent SOFR)  

---

## Data

| Series / print | Role | Source |
|----------------|------|--------|
| `DFII5` | 5y TIPS/real proxy | FRED |
| `DFII10` | 10y TIPS/real proxy | FRED |
| **SOFR** | Secured overnight financing; liquidity one-liner | [NY Fed SOFR](https://www.newyorkfed.org/markets/reference-rates/sofr) (~08:00 ET) |

FRED: ❌ homemade BE = DGS − DFII as precise inflation pricing (qualitative one-liner OK but label estimate, Conf≤L).  
SOFR: ❌ substitute for `DGS*`/`DFII*`; ❌ no as-of treated as today.

---

## Output

```markdown
| Series | Level | Δ | As-of | Note |
|--------|-------|---|-------|------|
| DFII5 | … or `miss` | | | |
| DFII10 | … or `miss` | | | |
| SOFR | … or `miss` | | | NY Fed · funding/liquidity |
```

One transmission line: real rates ↑/↓ **qualitative** impact on long UST proxy (TLT) and gold leg (emily) — detail bridge stays in `fx-us-uk-bridge`/trunk.  
SOFR: optional **one line** funding/liquidity (when print exists); missing → Miss ledger `SOFR: miss`.

---

## Forbidden

- ❌ Invent BE curve/inflation swap  
- ❌ Invent SOFR or use SOFR to alter Rate scenario Δbp formulas  
- ❌ Mix real-rate/SOFR “scores” into equity/commodity score  
- ❌ Fill fake DFII with no data  
- Real/TIPS levels: only FRED DFII5/DFII10 (10y real = DFII10); level must be that series’ print. Nominal 10y: only FRED DGS10. Cannot pull DFII print, or level is DGS* → cell `miss`. Do not fill DFII cells with nominal levels.  

---

## Checklist

- [ ] DFII5/DFII10 or `miss`  
- [ ] SOFR print + as-of **or** `miss`  
- [ ] as-of; 📊 Data/📊 Institutional (NY Fed)  
- [ ] No fake BE/OAS/fake SOFR  
