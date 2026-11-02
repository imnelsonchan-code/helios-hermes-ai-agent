---
name: commodity-forecast
description: >-
  emily: Commodity scenario bull|base|bear + Est value bands (or miss)
  (Method A, observation only). Daily 1–4w forced 10-col short table (miss cell, no whole-section skip); Weekly
  4–12w forced for all 10 cols. Feeds Trade map before full Obs levels;
  Basis must cite Forecast/Scenario. Cite-or-miss free data only; no invent
  WASDE/EIA; no FX/DXY Est (christina only); proxy-only Conf≤L. Not a
  broker order book; emily ≠ Emily broker.
---

# Commodity forecast — scenario / Est bands (Method A)

**Owner:** emily · commodities · **Train:** draft → Zoe → **emily revise** → `inbox/commodities-session/*-revised.md`  
**Load after:** `commodity-sources-crawl` → `world-to-commodity` → `commodity-insight` → `commodity-direction` (+ News / Market check)  
**Load before:** `commodity-signal-table` (full Obs levels) → `commodity-puzzle` → `commodity-session-report` (trunk) embed  
**Not:** broker Emily / M7 orders · broker order book · self-write FX / DXY / DFII Est · invent WASDE / EIA / COT / term-structure numbers · desk Risk-on/off  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "**Not investment advice · observation only**". Each finalize must disclose:

> **Coarse proxy / observation, not execution** — Est / scenario bands ≠ terminal pricing model; Obs levels are not orders.

Source grading: `📊 Data` / `📰 News` / `📊 Institutional`. **miss > invent.**

---

## When to use

| Cadence | Behavior |
|---------|------|
| **Daily lite** | **Mandatory** ten-column short table; Horizon **1–4w**. Each row bull | base | bear mechanism sentence + Est band; missing data → cell `miss`, **row stays**. ❌ skip entire section. No Scenario / Est cite → downstream do not fill full Obs levels. |
| **Weekly depth** | **Mandatory** ten-column bull | base | bear; Horizon **4–12w**. Missing data → cell / row `miss`, **row stays**. |

### Not

- ❌ standalone Jobs report replacing trunk session  
- ❌ broker order list / quantity / order type / "send to Emily"  
- ❌ near-term price momentum auto-extrapolation as scenario (anti Method A)  
- ❌ self-fill DXY / `DFII*` / Rate Δbp / `FX_*` / `B_*` (**christina only**; this skill **cite-or-miss** only)  
- ❌ invent inventory, stocks-to-use, COT net, fake curve numbers as "facts"

---

## LOAD ORDER (unified · 8-skill SSOT · hard)

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

This skill owns only its section; **do not** overreach into downstream `C_*` / Obs levels / finalized `commodity_regime` (except fields explicitly allowed here).

## Hard rules

1. **Forecasting =** bull | base | bear **mechanism scenarios** + optional **Est value band** (Method A; observation only) — **not** an order book  
2. **miss > invent:** no auditable WASDE / EIA / COT / inventory / curve source → cell `miss`; ❌ invent numbers  
3. **Est = band** (or `miss`); fake precise point price → change to band or `miss`; disclose "coarse proxy / observation, not execution"  
4. **This skill does not write** `C_*` / `DIR_*` / Obs entry / cut / TP / quantity / order type / bare `BUY`  
5. **DIR_* cite only** upstream `commodity-direction` as bias; **do not** rewrite Direction column in this table  
6. **Paid blacklist:** OilPriceAPI · LSEG / Bloomberg / FactSet · ICE Fundamentals paid APIs  
7. **No FX / DXY / DFII Est:** **christina cite-or-miss** only  
8. **proxy-only** driven bands → Conf≤L; primary anchor = US print  
9. **Forecast before** signal-table full Obs levels; downstream **Basis must cite** Scenario / Est  
10. **emily ≠ broker Emily;** Not investment advice · observation only  
11. LOAD ORDER: sources → world → insight → direction → **forecast** → signal → puzzle → trunk  

## Definition: "Forecasting" = scenario bands + optional Est bands

Aligned with christina **Rate scenario → Method A Est**:

| Layer | Meaning | Required? |
|----|------|--------|
| **Commodity scenario** | per column **bull | base | bear** one **mechanism** sentence (supply-demand / structure / transmission / calendar) + **price direction** | Daily + Weekly ten columns mandatory (Daily short 1–4w; missing cell miss; ❌ skip entire section) |
| **Est value (band)** | scenario → **price band** (not fake precise point); may write `bull… / base… / bear…` or single envelope | fill when translatable; not auditable / gate → `miss` |
| **Invalidation** | observation failure (event / structure / official window breaks envelope) | recommended; strongly recommended when Est / will feed levels |
| **Obs entry / cut / TP** | **not finalized in this skill** — hand to `commodity-signal-table` / trunk; this skill only delivers Scenario + optional Est | — |

**Hard order (LOAD ORDER aligned):**  
insight / direction (+ News / Market check) → **commodity-forecast (this skill)** → Est band (or miss) → **commodity-signal-table** full Obs levels (Basis **must cite** Forecast / Scenario) → puzzle → trunk.

**Basis gate (downstream hard):** no Basis (Dominant tag + **cite Forecast / Scenario**) → **do not fill** Obs entry / cut / TP.

---

## Universe (mandatory ten columns · SSOT)

Primary Est / scenario anchor = **US print**. UK / ETC / proxy may only adjust Conf / dual-leg narrative; if UK drives band → tag **`proxy-only`** + **Conf≤L**.

| Commodity | US primary print | UK/EU | Notes |
|-----------|-------------|-------|------|
| Gold | `XAU` (gold-api) | `SGLN.L` | indicative spot vs ETC; `GC=F` footnote only (futures≠spot) |
| Silver | `XAG` (gold-api) | `PHAG.L` | ❌ `XAG-USD` · ❌ Yahoo `XAGUSD=X`; `SI=F` footnote only (futures≠spot) |
| Copper | `HG=F` | `COPA.L` | tag `futures≠spot` |
| Soy | `ZS=F` | `SOYB`* | CBOT vs proxy |
| Wheat | `ZW=F` | `WEAT`* | … |
| Corn | `ZC=F` | `CORN`* | … |
| Oil | `CL=F` | `BZ=F` | WTI vs Brent; try CL–BZ attribution |
| Cocoa | `CC=F` | `NIB`* | ICE US cocoa |
| Sugar | `SB=F` | `CANE`* | Sugar #11 |
| Coffee | `KC=F` | `JO`* | ❌ KC≠equity; JO name-check |

\*Ag / softs UK: `proxy≠futures≠LSE`; missing → `miss`. Orange juice / cotton etc. OOU.

---

## Free data / cite-or-miss (scenario fuel · not an invent engine)

**Principle:** public pages / official PDF / free open data **cite when present** (outlet + date / as-of + URL or path); paywall / missing / stale not auditable → **`miss`**. ❌ invent numbers. ❌ paid API fill gaps.

| Use | Free / public source | Feeds Scenario / Est |
|------|-------------|-------------------|
| Oil inventory | **EIA WPSR** / Open Data | Oil bull / bear mechanism; **cite numbers only when report present**; else `miss` / days to next window |
| Grains balance / S-U | **USDA WASDE** / **PSD Online** / **Export Sales** | Soy / Wheat / Corn; Weekly **stocks-to-use direction sentence** when present; else `miss` (❌ guess buffer %) |
| Positioning | **CFTC COT** Disagg (weekly) | adjust Conf / Invalidation / qualitative mechanism only; ❌ intraday Signal; ❌ invent net |
| Metals / softs stocks | **LME** / **COMEX** / **LBMA** / **ICE certified** public pages | inventory path cite-or-miss |
| Softs balance | **ICO** / **USDA** Sugar / Coffee circulars | preferred over paid ICCO / ISO subscription |
| Monthly benchmark | **World Bank Pink Sheet** | weekly scenario cross-check (not intraday precision) |
| Term structure | Yahoo auditable dated / near-far **or** public curve one-liner | Contango / Back **qualitative**; fake precision roll / DV01 → `miss` |
| Dual-leg prints | precious US = **gold-api**; other Yahoo Finance (ToS) | Last / as-of; LSE 0 / NaN → `miss`; ❌ Yahoo `XAUUSD=X` / `XAGUSD=X` primary |
| FX / real rates / curves | **christina cite only** rates session / `inbox/rates-session/*-revised.md` | one sentence US/UK leg / Conf / Invalidation; ❌ this skill self-writes FX / DXY Est |

**Paid blacklist (hard):** OilPriceAPI · LSEG / Refinitiv · Bloomberg · FactSet · ICE Fundamentals paid APIs · other enterprise-licensed live feeds.

**Industry practice (observation · do not copy fake precision):** grains **lower stocks-to-use → tighter / more bullish narrative** (only when WASDE / PSD **auditable**); Oil / metals use inventory Δ + **term structure** qualitative; always **band**, do not force fake point price.

---

## Method A (default · mandatory disclose)

Aligned with christina bond Method A; commodity steps:

1. **Anchor:** each column US print Last + as-of (missing → row Scenario may have mechanism but Est=`miss`).  
2. **Read fuel (cite-or-miss):** inventory / S-U / term / COT / calendar / world→commodity / christina FX pointer — **only with source in mechanism sentence**.  
3. **Hand-write bull | base | bear:** three mechanism sentences + direction per column; **do not** use near-term return / MA auto-continuation as scenario.  
4. **Coarse proxy disclose:** label "**coarse proxy / observation, not execution**"; optional near-term vol envelope for Est band; **cannot state mechanism → Est=`miss`**.  
5. **Est = band** (preferred over fake precise point); Obs TP (downstream) at near-term band from Est / Scenario.  
6. **Failure → `miss`:** no Last / no auditable fuel / gate triggered / headlines-only invent.

### Method A gate (hard · anti Method A ban)

**Method A =** hand-written bull | base | bear **mechanism scenarios** (supply-demand / structure / transmission / calendar) + optional coarse proxy Est band.

**❌ Explicit ban (not Scenario / Est engines):**
- **ARIMA** / **LSTM** / **darts** (or similar statistical / deep time-series packages) auto-fit extrapolation  
- **Near-term MA continuation** / near-term return auto-extension as bull | base | bear  
- Any "model score → scenario" black box without mechanism sentences  

Triggered → row changes to hand mechanism **or** Est / Scenario cell `miss`; state above engines not used.

### Method B (fallback · narrow)

Official balance / inventory / curve all `miss`, but Yahoo Last still present:  
- Scenario may be **qualitative only** (liquidity / season / calendar window) + explicit `data: miss`  
- Est ≈ near-term range / 20d mid **band**; **Conf≤L**; mark Method B  
- ❌ use Method B to pretend WASDE / EIA numbers exist

### Method C (weekly footnote)

Same column US vs UK / proxy: **agree / diverge / miss**; disclose each leg; **do not** use UK to fill US price, **do not** silent FX.

---

## Gates (must)

| Gate | Behavior |
|------|------|
| **No invent WASDE / EIA / COT / inventory** | no cite → numeric cell `miss`; mechanism must not use fake % / fake mbbl |
| **Cite-or-miss** | every driver claim needs outlet + as-of or mark `miss` |
| **No FX / DXY Est** | ❌ self-fill; **christina cite** or whole section `miss` |
| **proxy-only** | UK / ETC / SOYB* etc. drive band → **`proxy-only` + Conf≤L** |
| **Est shape** | prefer **band**; fake tick precision → band or `miss` |
| **Calendar near-term** | inside EIA / WASDE window → Conf↓ or wait for confirmation (downstream may `C_WAIT`) |
| **CL vs BZ** | Oil try dual-leg; missing leg → leg `miss` + still write attribution where possible |
| **S-U (grains)** | Weekly: WASDE / PSD auditable → direction / tight-loose sentence required; else `miss` |
| **Headline≠numbers** | ❌ news invents Last / Est / inventory |
| **No score blend (E5)** | ❌ `tm_score` / `valuation_score` / `rates_signal` / `B_*` / `FX_*` changes Est |
| **Anti Method A** | ❌ ARIMA / LSTM / darts / near-term MA continuation as Scenario |
| **Shock→Scenario** | take world shock skeleton: channel + dual-leg → write bull | base | bear **mechanism**; ❌ linear fake Q / equilibrium invent |
| **Calendar** | official windows (EIA / WASDE / Export Sales / COT / softs) unknown → `miss`; ❌ FMP invent dates |

---

## Horizon (hard)

| Cadence | Horizon | Ten columns |
|---------|---------|------|
| Daily | **1–4w** | **Mandatory 10 rows** (Gold…Coffee); missing → cell `miss`, row stays; ❌ skip entire section |
| Weekly | **4–12w** | **Mandatory 10 rows** (Gold…Coffee); missing → cell `miss`, row stays |

When Est / will feed Trade map levels, Horizon required.

---

## Relationship to Trade map (hard)

```text
commodity-direction (DIR_* lean)
  → commodity-forecast (Scenario ± Est band)   ← this skill
  → commodity-signal-table / trunk Trade map (C_* · Obs entry / cut / TP)
```

| Rule | Explanation |
|------|------|
| **Forecast before full Obs levels** | no Scenario / Est cite (Daily + Weekly) → do not fill entry / SL / TP. Full-level rows Obs TP must sit in cited Est band near-term; outside band → row levels `miss` or only `C_WAIT` / `NO_SETUP` |
| **Basis must cite Forecast / Scenario** | e.g. `Basis: … · cite Scenario Oil base + EIA WPSR as-of … · Dominant: micro-led` |
| **Est feeds TP** | Obs TP at near-term band from Est / Scenario; no Est still OK with qualitative Scenario + `C_WAIT` / `NO_SETUP` |
| **This skill ≠ order book** | no quantity / order type / broker routing; Signal vocabulary downstream `C_*` |

Daily downstream still enforces: **full Obs entry + SL + TP ≤3** rows.

---

## Macro · Micro · Market (this skill responsibility)

| Lens | This skill does | Does not |
|----|------------|------|
| **Macro** | world / calendar / christina cite one-liner; Scenario primary narrative | ❌ self-write Rate Δbp / DXY Est |
| **Micro** | inventory / S-U / term / COT / dual-leg **cite-or-miss** → mechanism; Est band | ❌ invent official numbers |
| **Market** | Emily-topic narrative adjusts Conf / Invalidation only | ❌ paid terminal / ads as primary; ❌ headlines override scenario |

Assembly: Macro first → Micro translates mechanism / bands → Market does not override scenario. Conflict → Conf↓ or hand downstream `C_WAIT`.

---

## Output table templates (embed in trunk)

### Daily (mandatory ten-column short table · 1–4w)

```markdown
## Commodity forecast (daily · ten columns mandatory · 1–4w)

**Disclose:** coarse proxy / observation, not execution · Not investment advice · observation only · emily ≠ Emily (broker/M7)

| Commodity | US Last · as-of | Horizon | Bull (mechanism+direction) | Base | Bear | Est band (or miss) | Invalidation | Conf | Notes / cite |
|-----------|-----------------|---------|-----------------|------|------|-----------------|--------------|------|-------------|
| Gold | XAU · gold-api · … | 1–4w | | | | | | H/M/L | LBMA/COMEX/`miss` · christina FX? |
| Silver | XAG · gold-api · … | 1–4w | | | | | | | |
| Copper | HG=F · … | 1–4w | | | | | | | LME/COMEX/`miss` |
| Soy | ZS=F · … | 1–4w | | | | | | | WASDE S-U/`miss` |
| Wheat | ZW=F · … | 1–4w | | | | | | | WASDE S-U/`miss` |
| Corn | ZC=F · … | 1–4w | | | | | | | WASDE S-U/`miss` |
| Oil | CL=F · … | 1–4w | | | | | | | EIA WPSR/`miss` · CL–BZ |
| Cocoa | CC=F · … | 1–4w | | | | | | | ICE/USDA/`miss` |
| Sugar | SB=F · … | 1–4w | | | | | | | USDA circular/`miss` |
| Coffee | KC=F · … | 1–4w | | | | | | | ICO/USDA/`miss` |

(Ten columns complete; missing data → cell `miss`, row not deleted. ❌ skip entire section. Before full Trade map levels: this table must have Scenario / Est cite. **Do not** second-finalize in trunk.)
```

### Weekly (mandatory ten columns · 4–12w)

```markdown
## Commodity forecast (weekly · ten columns mandatory · 4–12w)

**Disclose:** coarse proxy / observation, not execution · Est=band (not fake precision) · miss>invent · ❌ self-write FX/DXY Est (christina cite-or-miss)
**Method:** A (default) / B (fallback row note) / C (US↔UK footnote)

| Commodity | US Last · as-of | Horizon | Bull (mechanism+direction) | Base | Bear | Est band (bull/base/bear or envelope) | Invalidation | Conf | Cite-or-miss fuel |
|-----------|-----------------|---------|-----------------|------|------|----------------------------------------|--------------|------|-------------------|
| Gold | XAU · gold-api · … | 4–12w | | | | | | H/M/L | LBMA/COMEX/`miss` · christina FX? |
| Silver | XAG · gold-api · … | 4–12w | | | | | | | |
| Copper | HG=F · … | 4–12w | | | | | | | LME/COMEX/`miss` |
| Soy | ZS=F · … | 4–12w | | | | | | | WASDE S-U/`miss` |
| Wheat | ZW=F · … | 4–12w | | | | | | | WASDE S-U/`miss` |
| Corn | ZC=F · … | 4–12w | | | | | | | WASDE S-U/`miss` |
| Oil | CL=F · … | 4–12w | | | | | | | EIA WPSR/`miss` · CL–BZ |
| Cocoa | CC=F · … | 4–12w | | | | | | | ICE/USDA/`miss` |
| Sugar | SB=F · … | 4–12w | | | | | | | USDA circular/`miss` |
| Coffee | KC=F · … | 4–12w | | | | | | | ICO/USDA/`miss` |

**Rules:** each cell mechanism not only up/down · missing data → `miss` (row stays) · proxy driven → `proxy-only`+Conf≤L  
**Handoff → Trade map:** Basis must cite this table Scenario / Est; this table **does not** fill Obs entry / cut / TP.
```

### Forecast fuel footnotes (weekly grains + Oil · cite-or-miss required)

```markdown
### Forecast fuel footnotes (cite-or-miss)
| Commodity | Inventory / S-U | Term structure | COT | Christina FX/rates cite |
|-----------|----------------|----------------|-----|-------------------------|
| Soy | WASDE … / miss | Contango/Back/miss | Disagg…/miss | path… / miss |
| Wheat | WASDE S-U / miss | miss | miss | miss |
| Corn | WASDE S-U / miss | miss | miss | miss |
| Oil | EIA … / miss | … | … | … |
```

**Rules:** Soy / Wheat / Corn + Oil one row each; cite when sourced, else whole row `miss`. ❌ pull Later stub into Keep. ❌ invent WASDE / EIA / COT numbers.

---

## Handoff contract

| To | Content |
|------|------|
| ← `commodity-insight` / `commodity-direction` | mechanism / lenses / `DIR_*` lean as Scenario fuel |
| → `commodity-signal-table` | read Scenario + Est band → draft `C_*` / Obs; **Basis: cite Forecast…**; Daily ≤3; this skill **does not write** `C_*` |
| → `commodity-puzzle` | Scenario / Est as puzzle fuel (does not finalize regime) |
| → `commodity-session-report` | embed tables in Commodity scenario / forecast section; Daily + Weekly ten columns (Daily short table) |
| Alice | **do not** full-paste ten-column Est; only via Session summary / regime cite |
| christina | this skill **receive-only** bridge; ❌ reverse-edit `FX_*` / `B_*` |

**Shadow:** do not invent new scores here; downstream still uses `commodity_signal` / `shadow_commodity_score` / `commodity_signal_breakdown` (eval only).

---

## Miss ledger (mandatory when miss · hand to trunk)

```markdown
### Miss ledger (forecast)
| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| ZS=F | WASDE S-U | URL or path | … | no (≤1 retry then) |
| CL=F | EIA WPSR | | | |
| — | FX-cite | christina path | absent | no |
```

Sources footer: `Misses: see Miss ledger`.

---

## Banned

- ❌ invent WASDE / EIA / COT / inventory / S-U / fake term-structure numbers  
- ❌ self-write FX / DXY / DFII Est / Rate Δbp / `FX_*` / `B_*`  
- ❌ bare `BUY` / `WATCH` / quantity / order type / "send to Emily"  
- ❌ near-term momentum auto-continuation as bull / base / bear  
- ❌ **ARIMA / LSTM / darts / near-term MA continuation** as Scenario (anti Method A)  
- ❌ linear fake Q / equilibrium invent to fill Est  
- ❌ FMP / paid calendar invent official window dates  
- ❌ fake precise point price as Est (use band or `miss`)  
- ❌ OilPriceAPI / LSEG / Bloomberg / FactSet / ICE Fundamentals paid API  
- ❌ `XAG-USD`; KC as equity; proxy as London futures without `proxy≠futures≠LSE`  
- ❌ treat this table as broker order book or desk Risk-on/off final call  
- ❌ use `tm_score` / `valuation_score` / `rates_signal` to change Est / Scenario
- `DIR_*` 1D% may only come from GLD / `GC=F` (silver SLV / `SI=F`) previous close, cited in that row; gold-api spot is level only. Missing prev close → `miss`. `BZ=F` row must say ICE Brent financial futures, same source CL–BZ, same pull, same as-of. Missing → `miss`.  

---

## Checklist

- [ ] Daily: 1–4w **ten columns** bull | base | bear ± Est band; missing cell `miss`, row stays; ❌ skip entire section  
- [ ] Weekly: 4–12w **ten columns** bull | base | bear; missing cell `miss`, row stays  
- [ ] Each column mechanism (not only up/down) + Invalidation (recommended)  
- [ ] Est = **band** or `miss`; disclose "**coarse proxy / observation, not execution**"  
- [ ] Gates: no invent official numbers · cite-or-miss · no FX Est · proxy-only→Conf≤L  
- [ ] **Anti Method A:** no ARIMA / LSTM / darts / near-term MA continuation as Scenario  
- [ ] Shock skeleton (if present) → mechanism scenario; ❌ fake Q / equilibrium invent  
- [ ] Grains Weekly: S-U auditable → direction required; Oil: EIA cite-or-miss; term qualitative  
- [ ] LOAD ORDER complete; **Forecast before** signal full Obs levels; Basis **cite Scenario / Est**  
- [ ] This skill **no** `C_*` / `DIR_*` / Obs entry / cut / TP / quantity / bare BUY  
- [ ] christina receive: path or `miss`; ❌ self-fill DXY / DFII  
- [ ] Miss ledger + Sources graded; Not investment advice · emily ≠ Emily (broker/M7)
