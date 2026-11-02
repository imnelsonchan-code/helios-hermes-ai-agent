---
name: curve-watch
description: >-
  christina: FRED nominal curve + spreads (DGS2/10/30, T10Y2Y, T10Y3M).
  Draft Rate scenario Δbp bull|base|bear for trunk finalize. Free FRED only;
  miss > invent; no OIS/forwards/ML path.
---

# Curve watch — nominal curve

**Owner:** christina · rates  
**Load order:** **this skill (first)** → real-rates → fedwatch → bond-etf → fx → trunk  
**Not:** invented forwards/OIS/fed-funds path · emily tape theft · desk Risk-on/off  

---

## When to use

- Start every daily/weekly rates session by pulling nominal curve and slopes  
- Prepare **Rate scenario draft** (Δbp envelope) for trunk  
- Missing series → cell/tenor `miss`; do not invent  

---

## Data (free)

| Series | Role |
|--------|------|
| `DGS2` | 2y nominal |
| `DGS10` | 10y nominal |
| `DGS30` | 30y nominal |
| `T10Y2Y` | 10s2s slope |
| `T10Y3M` | 10s3m slope |

Source: FRED (📊 Data). Gilt/UK 10y: public cite or `miss` (no invention).  
Every pull: **As-of** required; lag/non-trading day → Note `data_delay` or Miss ledger (do not silently treat as today’s print).

---

## Output (handoff → trunk)

1. **Curve table** (level + near-term Δ + **as-of**; lag → `data_delay`)  
2. **Shape one-liner** (steep/flat/inverted/butterfly qualitative — no fake precision decomposition)  
3. **Rate scenario draft** (trunk finalizes):

```markdown
| Tenor | Horizon | Bull Δbp | Base Δbp | Bear Δbp | FedWatch cite | Invalidation | As-of |
|-------|---------|----------|----------|----------|---------------|--------------|-------|
| DGS2 | 1–4w or 4–12w | | | | (fedwatch skill fills / miss) | yield leaves envelope | |
| DGS10 | | | | | | | |
| DGS30 | | | | | | | |
```

- Daily horizon **1–4w**; Weekly **4–12w**  
- Bull/base/bear = **human/session judgment** (curve narrative + later FW cite), **not** near-term Δy continuation auto-extrapolation  
- Invalidation default: realized yield leaves envelope  

---

## Macro mirror duty

This skill mainly contributes **Macro**: nominal curve + Rate scenario draft.  
Do not invent ETF Est under Micro/Market here.

---

## Forbidden

- ❌ OIS/futures strip/invented FW probabilities  
- ❌ ML path/auto yield-continuation as scenario  
- ❌ Use curve scores to alter `tm_score`/`valuation_score`  
- ❌ Fake DV01/OAS  

---

## Checklist

- [ ] DGS2/10/30 + T10Y2Y/T10Y3M or explicit `miss`  
- [ ] Rate scenario draft three Δbp columns + Invalidation  
- [ ] as-of complete (lag → `data_delay`); source 📊 Data  
- [ ] No forwards/continuation-as-scenario  
