---
name: commodity-obs-backtest
description: >-
  emily Saturday-style OBSERVATION-ONLY backtest: cite prior C_*/DIR_*/commodity_regime
  vs subsequent Last prints (precious=gold-api; else Yahoo). Hygiene metrics only (hit/miss lean, regime
  stability, dual-leg attribution rate, Basis-gate pass). Never broker PnL,
  never invent inventory, never place orders. Exclude SimpleFX/IB/Alpaca/RL/ARIMA.
---

# Commodity obs-backtest — observation backtest (cite-only hygiene)

**Owner:** emily · commodities · **Cadence:** **Eval/Sat** (Saturday-style; **not in** daily/weekly 8-skill load)  
**Load with:** Sat audit same period or after; read prior `inbox/commodities-session/*-revised.md` + next-day Last (precious = gold-api; else Yahoo)  
**Not:** broker PnL · orders · invent inventory/COT · SimpleFX/IB/Alpaca/RL/ARIMA engines · rewrite live session  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "**Not investment advice · observation only**". **miss > invent.**

---

## Purpose

Saturday-style **cite-only hygiene**: compare **prior** revised session `C_*`/`DIR_*`/`commodity_regime` (+ optional Basis/dual-leg flags) vs **subsequent** Last prints (precious = gold-api; else Yahoo; as-of stated), assess observation lean/regime/gate discipline — **not** a trading performance engine.

---

## When to use

- Sat Phase 2 commodities audit (align SOUL Saturday) or adhoc hygiene  
- Have ≥1 prior-week `inbox/commodities-session/*-revised.md` to cite  
- **Not:** daily/weekly session 8-skill mandatory load; **Not** as live Trade map input

---

## Hard rules (OBSERVATION-ONLY)

1. **NEVER** compute broker PnL/fills/slippage/portfolio return  
2. **NEVER** invent inventory/COT/WASDE/term-structure numbers  
3. **NEVER** place orders · quantity · order type · "send to Emily"  
4. **Cite-only:** all prior Signal/Direction/regime/Basis must come from revised MD path + as-of; next-day price must be Yahoo (or equivalent free print) + as-of  
5. Missing prior field / missing next-day price → that row **`miss`** (no guess)  
6. ❌ use this report to rewrite/overwrite live `C_*`/`DIR_*`/Est  

### Explicit EXCLUDE (hard)

| Exclude | Why |
|---------|-----|
| **SimpleFX** | Execution/broker path — out of scope |
| **IB** (Interactive Brokers) | Execution — out of scope |
| **Alpaca** | Execution — out of scope |
| **RL** (reinforcement learning) | Trading agent — out of scope |
| **ARIMA**/LSTM/darts backtest engines | Anti Method A; not observation hygiene |

---

## Allowed metrics (all cite-only)

| Metric | Definition (qualitative/count) | Source |
|--------|------------------------------|--------|
| **Direction lean hit/miss** | prior `DIR_BULLISH`/`DIR_BEARISH` vs next-day Last direction (qualitatively up/down/flat); `DIR_NEUTRAL`/`TWO_WAY`/`UNCLEAR`/`miss` → label `n/a` or count separately | prior Direction table + gold-api/Yahoo Last |
| **Regime stability** | prior `commodity_regime` vs weekend/next session same field (or next-day narrative cite); stable/changed/`miss` | prior + later revised or Last narrative |
| **Dual-leg attribution present rate** | prior Dual price/insight columns with attribution sentence ÷ ten-column (or auditable rows) | prior revised only |
| **Basis-gate pass rate** | among rows with Obs entry/cut/TP, share where Basis includes Dominant + **cite Forecast**; rows without levels excluded from denominator | prior Trade map |

❌ invent `commodity_hit_rate` fake precision as live KPI; may write coarse counts/table + `miss`.  
❌ cite `tm_hit_rate`/`value_hit_rate`/Book C.

---

## Output path

```text
shared/reports/emily/self-review/YYYY-Www-emily-obs-backtest.md
```

(may mirror workspace; **do not** write `inbox/commodities-session` as Sat portal; **not** Jobs light.)

Optional pointer in same-week `YYYY-Www-emily-review.md` Part B/C.

---

## Required sections / tables

### 1. Meta

```markdown
# emily · commodities — Observation-only backtest
**Week:** YYYY-Www · **As-of:** YYYY-MM-DD
**Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7)
**Hard:** no broker PnL · no orders · no invent inventory · EXCLUDE SimpleFX/IB/Alpaca/RL/ARIMA
**Prior sessions cited:** inbox/commodities-session/…-revised.md · …
**Subsequent prints:** Yahoo · as-of …
```

### 2. Lean hit/miss (ten-column or auditable rows)

```markdown
| Commodity | Prior DIR_* | Prior C_* | Subsequent Last · as-of | Lean vs Last | Note / miss |
|-----------|-------------|-----------|-------------------------|--------------|-------------|
| Gold | DIR_* / miss | C_* / miss | XAU · gold-api · … | hit / miss / n/a | cite paths |
| … | | | | | |
```

### 3. Regime stability

```markdown
| Prior commodity_regime | Later cite / print window | Stable? | Note |
|------------------------|---------------------------|---------|------|
| Risk-on / Neutral / … | path or Yahoo window | yes / no / miss | |
```

### 4. Hygiene rates

```markdown
| Metric | Count / rate | Cite basis | miss? |
|--------|--------------|------------|-------|
| Dual-leg attribution present | k/10 | prior dual notes | |
| Basis-gate pass | k/n (n=rows with levels) | prior Trade map Basis+Forecast cite | |
| Direction lean hit (excl n/a) | h/m | DIR vs Last | |
```

### 5. Omissions / Miss ledger

```markdown
### Miss ledger
| Item | Attempted | Reason |
|------|-----------|--------|
| … | prior path / Yahoo | …
```

### 6. Sources + Footer

```markdown
## Sources
- 📊 Data: prior revised · <paths>
- 📊 Data: gold-api/Yahoo subsequent Last · <symbols> · <as-of>
- Misses: see Miss ledger

## Footer
Not investment advice · observation only · emily ≠ Emily (broker/M7)
OBSERVATION-ONLY · no PnL · no orders · EXCLUDE SimpleFX/IB/Alpaca/RL/ARIMA
```

---

## Relation to 8-skill load (hard)

**Do not** insert into daily/weekly EXECUTION load:

```text
sources → world → insight → direction → forecast → signal → puzzle → trunk
```

This skill = **Eval/Sat only** (SOUL §12/checklist). May read trunk output; **not** mandatory in trunk load.

---

## Banned

- Broker/SimpleFX/IB/Alpaca execution or PnL  
- RL/ARIMA/LSTM/darts backtest engines  
- invent inventory/COT/fake curve/fake hit-rate KPI  
- bare `BUY`/quantity/orders  
- write obs-backtest into 8-skill Keep load  
- output inbox as Sat portal  

---

## Checklist

- [ ] Output: `shared/reports/emily/self-review/YYYY-Www-emily-obs-backtest.md`  
- [ ] Prior `C_*`/`DIR_*`/`commodity_regime` cite revised paths  
- [ ] Subsequent Last (precious=gold-api; else Yahoo) + as-of; missing → miss  
- [ ] Metrics: lean hit/miss · regime stability · dual-leg attribution rate · Basis-gate pass — cite-only  
- [ ] ❌ PnL · ❌ invent inventory · ❌ orders  
- [ ] ❌ SimpleFX/IB/Alpaca/RL/ARIMA  
- [ ] Not inserted in 8-skill load; Eval/Sat only  
- [ ] Not investment advice · emily ≠ Emily (broker/M7)
