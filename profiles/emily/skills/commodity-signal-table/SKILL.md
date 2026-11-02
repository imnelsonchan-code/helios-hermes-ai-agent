---
name: commodity-signal-table
description: >-
  emily Trade map draft + Yahoo shadow features. C_* signals only;
  daily ≤3 full Obs levels; keys commodity_signal, shadow_commodity_score,
  commodity_signal_breakdown. Never bare BUY or tm_score. Observation only;
  emily ≠ Emily broker.
---

# Commodity signal table — observation signal table (Trade map draft)

**Owner:** emily · commodities · **Train:** draft → trunk (`commodity-session-report`) embed  
**Load with:** after `commodity-forecast` (Scenario ± Est); before `commodity-puzzle` / trunk  
**Upstream lean:** `commodity-direction` (`DIR_*` hints only, not equivalent to `C_*`)  
**Not:** place orders · broker Emily / M7 · Renee `tm_score` · custom desk-wide Risk-on/off (puzzle suggests, trunk finalizes)  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "Not investment advice · observation only". Source grading: `📊 Data` (Yahoo features) / optional `📰 News` (invalidation events).

---

## When to use

- **Every** daily / weekly session: produce Trade map **draft** + shadow meta  
- Daily: ten Signal rows; full Obs entry + SL + TP **≤3** rows  
- Weekly: may fill all actionable levels; **Basis final** from trunk after history finalize; this skill may tag `Basis: pending-history` **only when** Forecast / Scenario / Est **cite** already present (weekly mandatory)  
- **Not:** standalone Jobs report · replace trunk session · broker order list

---

## LOAD ORDER (unified · hard · SSOT)

```text
commodity-sources-crawl
  → world-to-commodity
  → commodity-insight
  → commodity-direction
  → commodity-forecast
  → commodity-signal-table
  → commodity-puzzle
  → commodity-session-report
```

This skill runs **after** forecast; **do not** parallel-open full Obs levels before forecast.

---

## Hard rules

### C_* enum (namespaced — prevent Renee bleed)

| Signal | Meaning (observation) |
|--------|--------------|
| `C_BUY` | observation bullish setup (not an order) |
| `C_WAIT` | wait for confirmation / range |
| `C_HOLD` | hold narrative for existing observation logic (not an open-interest instruction) |
| `C_REDUCE` | observation reduce / de-risk |
| `NO_SETUP` | no clear setup |
| `miss` | data / source insufficient |

**Banned labels:** ❌ bare `BUY` · ❌ `WATCH` · ❌ `NO_SIGNAL` · ❌ any Signal without `C_` / `NO_SETUP` / `miss` equity wording · ❌ **`DIR_*` written into Signal column** (Direction stays in `commodity-direction`)

### Levels

- Columns: Last · Est value (cite forecast) · Obs entry · Obs cut loss · Obs TP (TP1 · TP2 OK) · Horizon · Invalidation · Basis · Conf (H / M / L)
- **Basis gate (hard):** when levels present, Basis **must** include Dominant tag + **cite Forecast / Scenario / Est**; no Forecast / Scenario / Est cite → **do not fill** full Obs entry / cut / TP (Signal only / `NO_SETUP` / `miss` OK). Full-level rows must have Obs TP (TP1 / TP2 OK), TP at near-term cited Est band; outside band → row levels `miss` or only `C_WAIT` / `NO_SETUP`. Basis with levels must include `lean: base|bull|bear|two-way`. lean conflicts with upstream `DIR_*` (bull vs DIR_BEARISH, bear vs DIR_BULLISH) → Conf↓ or `C_WAIT`, **do not** rewrite Forecast table
- **Daily:** among non-`C_WAIT` / `NO_SETUP` / `miss`, full entry+SL+TP **at most ≤3** rows; rest Signal (+Invalidation) only
- **Weekly:** all actionable rows filled; Basis **must** align with that week history / Forecast (trunk finalize; draft may `pending-history` **if** Forecast cite already in)
- Primary levels = **US print**; UK / ETC / proxy driven → tag `proxy-only` + Conf≤L
- ❌ invent SL / TP · ❌ quantity · ❌ order type · ❌ "send to Emily"

### Shadow keys (eval only)

Must use these three names (do not use short names that collide with Renee):

| Key | Role |
|-----|------|
| `commodity_signal` | per ticker / commodity `C_*` (or map) |
| `shadow_commodity_score` | 0–100 **shadow / eval only**; no live blend |
| `commodity_signal_breakdown` | feature breakdown (Yahoo features); not `score_breakdown` |

❌ `tm_score` · ❌ bare `score` · ❌ average / merge with `valuation_score` · ❌ live sleeve blend

### Shadow score breakdown pattern (hard · if using shadow)

**If** this session / draft uses `shadow_commodity_score` or `commodity_signal` shadow map → **must** also have `commodity_signal_breakdown`, each column uses **named factors** (e.g. `near_return` · `rel_ma` · `vol_percentile` · `volume_oi` · `dual_leg_spread` · `miss`) — each factor needs as-of or mark `miss`; ❌ unnamed "factor1" black box.

```markdown
### Shadow meta (eval only)
- commodity_signal: { Gold: C_WAIT, … }
- shadow_commodity_score: { Gold: 0–100 or miss, … }
- commodity_signal_breakdown:
  Gold: { near_return: …, rel_ma: …, vol_percentile: …, dual_leg_spread: miss, … }
  …
```

**Hard separation:**
- ❌ **`DIR_*` never written into Signal column** (Direction only in `commodity-direction`)  
- **Basis** with levels **must cite Forecast / Scenario / Est** (+ Dominant tag)

---

## Free data / ticker

Same as trunk ten-column SSOT (precious US = gold-api; other Yahoo). **FX / rates:** prefer cite `shared/reports/christina/…-rates-session.md` (or `miss`) as DFII / GBPUSD / DXY pointer to explain Conf; ❌ invent `FX_*` / `B_*` / Rate Δbp.

| Commodity | US | UK/EU |
|-----------|-----|-------|
| Gold | `XAU` (gold-api) | `SGLN.L` |
| Silver | `XAG` (gold-api) | `PHAG.L` |
| Copper | `HG=F` | `COPA.L` |
| Soy | `ZS=F` | `SOYB`* |
| Wheat | `ZW=F` | `WEAT`* |
| Corn | `ZC=F` | `CORN`* |
| Oil | `CL=F` | `BZ=F` |
| Cocoa | `CC=F` | `NIB`* |
| Sugar | `SB=F` | `CANE`* |
| Coffee | `KC=F` | `JO`* |

\*proxy≠futures≠LSE; ❌ `XAG-USD`; JO name-check; KC ≠ equity.

Feature examples (free Yahoo auditable): near-term return, relative MA, vol / range position, volume / open interest (if present) — all need as-of; miss → do not fill fake numbers.

---

## Output paths

Optional draft (review before trunk embed):

| Cadence | Path |
|---------|------|
| Daily | `shared/reports/emily/YYYY-MM-DD-commodity-signals-draft.md` |
| Weekly | `shared/reports/emily/YYYY-Www-commodity-signals-draft.md` |

Canonical session remains trunk:

- `shared/reports/emily/YYYY-MM-DD-commodity-session.md`
- `shared/reports/emily/YYYY-Www-commodities-session.md`

❌ do not write inbox / Jobs light

---

## Required sections / tables

### 1. Meta

- As-of · cadence (daily / weekly) · data grade  
- Hard line: observation only · emily ≠ Emily (broker/M7) · Not investment advice

### 2. Trade map draft (ten rows)

```markdown
| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|-------|------|
| Gold | C_* / NO_SETUP / miss | {US px} | Est band verbatim (e.g. bull a–b / base c–d / bear e–f or envelope) or miss | {US px or zone} | {px} | TP1 · TP2 | 1–4w / 4–12w | {break / event} | Dominant + cite Forecast / Scenario / Est · lean: base or pending-history (weekly · Forecast cite present) | H/M/L |
| Silver | | | | | | | | | | |
| Copper | | | | | | | | | | |
| Soy | | | | | | | | | | |
| Wheat | | | | | | | | | | |
| Corn | | | | | | | | | | |
| Oil | | | | | | | | | | |
| Cocoa | | | | | | | | | | |
| Sugar | | | | | | | | | | |
| Coffee | | | | | | | | | | |
```

### 3. Daily trim note (daily mandatory)

```markdown
### Daily trim
Full levels rows (≤3): <Commodity1>, <Commodity2>, <Commodity3>
Remaining: Signal (+Invalidation) only
Full levels rows must have Obs TP; TP at cited Est band near-term
```

### 4. Omissions

```markdown
### Omissions
- <Commodity or field>: attempted + miss · <source tried>
```

### 5. Shadow meta (three keys)

```markdown
### Shadow meta (eval only)
- commodity_signal: { Gold: C_WAIT, … } or table with same names
- shadow_commodity_score: { Gold: 0–100 or miss, … }
- commodity_signal_breakdown: { Gold: { near_return: …, rel_ma: …, vol_percentile: …, … }, … }
```

Hard line: above is **shadow / eval only**; **do not** live blend into `tm_score` / `valuation_score` / desk-wide ranking.  
**If shadow used:** breakdown **must have named factors**; Signal column **no `DIR_*`**; with levels → Basis **cite Forecast**.

### 6. Sources + Footer

```markdown
## Sources
- 📊 Data: gold-api XAU / XAG · Yahoo · <as-of> · <symbols pulled>
- Misses: …

## Footer
Not investment advice · observation only · emily ≠ Emily (broker/M7) · no bare BUY · no tm_score
```

---

## Blank Trade map draft scaffold (copy-paste)

```markdown
# emily · commodities — Commodity signals draft
**As-of:** YYYY-MM-DD · **Cadence:** daily / weekly
**Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7)

## Trade map draft

| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|-------|------|
| Gold | | | | | | | | | | |
| Silver | | | | | | | | | | |
| Copper | | | | | | | | | | |
| Soy | | | | | | | | | | |
| Wheat | | | | | | | | | | |
| Corn | | | | | | | | | | |
| Oil | | | | | | | | | | |
| Cocoa | | | | | | | | | | |
| Sugar | | | | | | | | | | |
| Coffee | | | | | | | | | | |

### Daily trim
Full levels rows (≤3): _______ · _______ · _______

### Omissions
- …

### Shadow meta (eval only)
- commodity_signal: …
- shadow_commodity_score: …
- commodity_signal_breakdown: …

Hard line: shadow / eval only — do not live blend into tm_score / valuation_score.

## Sources
- 📊 Data: …
- Misses: …

## Footer
Not investment advice · observation only · emily ≠ Emily (broker/M7) · C_* only · no bare BUY · no tm_score
```

---

## Handoff with trunk

| Item | signal-table | trunk |
|------|--------------|-------|
| Trade map | draft | review embed in session |
| Daily ≤3 | this skill mandatory | trunk checklist re-verify |
| Weekly Basis | may `pending-history` **if** Forecast cite present | finalize after history |
| Risk-on/off | **do not write formal section** | trunk requires "Commodity Risk-on/off" |
| Shadow keys | this skill produces | session may appendix cite |

---

## Banned

- bare `BUY` / `WATCH` / `NO_SIGNAL` · `tm_score` · bare `score`  
- **`DIR_*` written into Signal column**  
- invent Obs entry / SL / TP · quantity / order type / "send to Emily"  
- Daily **>3** full-level rows · no Forecast / Est cite but full Obs levels filled · full-level row missing Obs TP · Obs TP outside cited Est band  
- Basis with levels **without** Dominant + Forecast / Scenario / Est cite  
- `XAG-USD` · KC as equity · JO without name-check  
- live score blend · treat shadow as published sleeve score  
- custom formal "Commodity Risk-on/off" replacing trunk (private note OK, final call in trunk)  
- output inbox / second Jobs file
- `DIR_*` 1D% may only come from GLD / `GC=F` (silver SLV / `SI=F`) previous close, cited in that row; gold-api spot is level only. Missing prev close → `miss`. `BZ=F` row must say ICE Brent financial futures, same source CL–BZ, same pull, same as-of. Missing → `miss`.

---

## Checklist

- [ ] LOAD ORDER: sources → world → insight → direction → forecast → **signal** → puzzle → trunk  
- [ ] Ten Signal rows; only `C_BUY` / `C_WAIT` / `C_HOLD` / `C_REDUCE` / `NO_SETUP` / `miss`; **no `DIR_*`**  
- [ ] No bare BUY / WATCH / NO_SIGNAL / `tm_score`  
- [ ] Daily ≤3 full Obs entry+SL+TP (full-level rows must have Obs TP, TP at Est band near-term); trim note written; no Forecast / Est cite → no full levels  
- [ ] Weekly: actionable levels complete; Basis pending-history **only when** Forecast cite present; or aligned with history  
- [ ] Trade map has Last / Est (cite forecast) / Horizon  
- [ ] Basis + Dominant + cite Forecast / Scenario / Est (when levels present)  
- [ ] Basis with levels includes lean: base|bull|bear|two-way; DIR_* conflict → Conf↓ or C_WAIT; do not rewrite Forecast  
- [ ] Primary levels = US; proxy-only → Conf≤L  
- [ ] Shadow three keys named: `commodity_signal` · `shadow_commodity_score` · `commodity_signal_breakdown`  
- [ ] **If shadow used:** breakdown has **named factors**; Signal has no `DIR_*`; Basis cites Forecast  
- [ ] Omissions / Misses complete; Not investment advice footer  
- [ ] emily ≠ Emily (broker/M7); no order language  
- [ ] Hand off to trunk embed; not standalone Jobs
