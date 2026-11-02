---
name: commodity-insight
description: >-
  emily deep commodity insight: what the market is telling us via physical
  balance, inventory, term structure, positioning narrative (cite-or-miss).
  Drivers / complex / dual-leg / tensions / missing evidence. No C_* signals;
  no invented inventory/COT/curves. No DIR_*/C_*/Obs. Feeds direction → forecast → puzzle → trunk.
---

# Commodity insight — market insight (what the market is saying)

**Owner:** emily · commodities · **Train:** session draft → trunk embed title **`## Market insight`** → Alice cite (preferred)  
**Load after:** `commodity-sources-crawl` → `world-to-commodity`  
**Load before:** `commodity-direction` → `commodity-forecast` → `commodity-signal-table` → `commodity-puzzle` → `commodity-session-report` (trunk)  
**Not:** Trade map / `C_*` / `DIR_*` · Obs entry / SL / TP · bare `BUY` · invent inventory / COT / fake curves · broker Emily / M7 · desk-wide Risk-on/off / Macro view  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**  
**Embed title SSOT:** trunk uses `## Market insight` (cite this skill); do not open separate `## Commodity insight` as Alice cite surface.

**Insight =** deep read of structure and narrative (physical ↔ curve ↔ positioning ↔ narrative) — **not** a trading signal, **not** an invent engine.

Label "Not investment advice · observation only". Source grading: `📊 Data` / `📰 News` / `📊 Institutional`.

---

## When to use

### Daily lite
- After world; **before** direction / forecast / signal / puzzle / trunk (LOAD ORDER SSOT)  
- **Drivers insight** 3–5 mechanism sentences (not headlines)  
- **Complex insight** ≥3 blocks (`precious` / `energy` / `industrial` / `grains` / `softs`)  
- **Dual-leg insight** at least Oil (CL vs BZ) + one other column; rest may be `N/A` / `miss`  
- **Tensions** + **Missing evidence** short table  
- Inventory / term structure / COT: **cite official touchpoint when present**; else `n/a` / `miss` (❌ invent)

### Weekly depth
- Same skeleton, thicker: dual-leg try all ten columns (else `miss`)  
- Five complexes try complete or written miss reason  
- Inventory / term / COT / (grains) stocks-to-use: **cite-or-miss** aligned with SOUL lens depth  
- Still **do not** fill `C_*` / `DIR_*` / Est / Obs levels / finalize `commodity_regime`

### Not
- Do not replace dual price / Trade map / history / Commodity scenario (trunk)  
- Do not write `C_*` / `DIR_*` / Est band or Obs entry / cut / TP in this skill  
- Do not invent EIA / WASDE / COT / LME / COMEX numbers or fake Contango / Back curves  
- Do not use paid terminals to fill gaps; do not write standalone Jobs report  
- Do not finalize commodity / desk Risk-on/off (puzzle **suggests** → trunk **finalizes**)  
- Do not treat insight as entry rationale written into Basis levels (may **hand off one sentence** for trunk / signal to cite)

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

## Handoff

| To / from | Content |
|------|------|
| ← `world-to-commodity` | Take events / channels / ten-column impact; insight **deepens** what the market is saying, do not recopy headline ledger |
| → `commodity-direction` | Drivers / Complex / Tensions / Missing → Direction lean fuel (**do not** write `DIR_*` in this section) |
| → `commodity-forecast` | Mechanism / lens pointers → Scenario fuel (**do not** finalize Est / bull | base | bear) |
| → `commodity-puzzle` | Drivers / Complex / Tensions / Missing → puzzle supports / tensions / missing |
| → `commodity-session-report` | Mechanism sentences + cite-or-miss lens pointers; **do not** ghost-write Scenario / Trade map / `commodity_regime` |
| ↛ signal-table / direction | **Do not write** `C_*` / `DIR_*` / Obs levels (insight only) |

---

## Hard rules

1. **Insight ≠ signal / direction / forecast:** ❌ any `C_*` / `DIR_*`, bare `BUY` / `WATCH`, Obs entry / SL / TP, Est band, quantity / order type in this section  
2. **miss > invent:** inventory Δ, stocks-to-use, COT net, term-structure shape — **write only with auditable source**; else `miss` / `n/a` + Miss ledger row  
3. **cite-or-miss:** every data / direction claim needs outlet + date / as-of + URL or path; paywall / missing / stale not auditable → `miss`  
4. **Paid blacklist (hard · Zoe REJECT candidate):** OilPriceAPI · LSEG / Refinitiv · Bloomberg · FactSet · **ICE Fundamentals paid APIs** (public Report Center manual pull excepted) · enterprise-licensed live LME / COMEX feeds  
5. **Google AI Mode / paid terminals** ❌ as primary source  
6. **Framework layers (align when writing mechanism, do not skip layers to invent):**  
   physical balance → inventory (scoreboard) → term structure (scarcity / storage) → positioning (confirmation only) → narrative (Market mirror; do not override Micro)  
7. **Positioning ≠ intraday signal:** COT weekly only, classification clear (Disagg Managed Money etc.); ❌ weekly COT as intraday direction command  
8. **Dual-leg attribution (hard):** beyond two prints must attribute (liquidity / contract spec / inventory location / proxy error / FX channel cite christina); forbid price dump only  
9. **E5 no score blend:** ❌ `tm_score` / `valuation_score` / `rates_signal` / `B_*` / `FX_*` rewriting commodity insight; ❌ self-fill DXY / DFII Est / Rate Δbp  
10. **emily ≠ broker Emily:** observation only; Not investment advice; **`commodity_regime` not finalized here**  
11. LOAD ORDER: sources → world → **insight** → direction → forecast → signal → puzzle → trunk  

---

## Free data only / ticker SSOT

**Allowed (cite-or-miss only · cite when present, else miss):**

| Use | Free / public source | Use in insight |
|------|-------------|----------------|
| Oil weekly inventory | **EIA WPSR** (Weekly Petroleum Status Report / Open Data) | energy Drivers / inventory direction sentence; else `miss` |
| Grains balance | **USDA WASDE** / **PSD Online** / **Export Sales** | grains balance / stocks-to-use direction; else `miss` |
| Positioning | **CFTC COT** (Disaggregated preferred; weekly) | positioning confirmation; ❌ intraday signal |
| Metals / softs stocks | **LME** / **COMEX** / **LBMA** vault / **ICE certified stocks** public pages | inventory path; do not treat single warehouse as global buffer |
| Coffee / Sugar balance | **ICO** free pages · **USDA** Sugar / Coffee circulars | softs; preferred over paid ICCO / ISO full-year subscription |
| Monthly benchmark | **World Bank Pink Sheet** | weekly cross-check (not intraday) |
| Dual-leg prints | precious US = gold-api; other Yahoo (ToS) + upstream sources-crawl | dual-leg insight |
| FX / real rates / curves | **christina cite only** rates session | Macro one-liner; missing → `miss` |

**Banned:** OilPriceAPI · LSEG · Bloomberg · FactSet · ICE Fundamentals paid APIs · `XAG-USD` (crypto) · invent inventory / COT / fake curves · social heat alone for insight

### Ten-column dual-leg (same as trunk)

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

\*Ag / softs UK: `proxy≠futures≠LSE`; missing → `miss`. Silver: **only** gold-api **`XAG`**, ❌ `XAG-USD` · ❌ Yahoo `XAGUSD=X`. `GC=F` / `SI=F` footnote only (futures≠spot).

**Complex ↔ columns:**

| Complex | Typical columns |
|---------|--------|
| `precious` | Gold · Silver |
| `energy` | Oil (CL / BZ) |
| `industrial` | Copper |
| `grains` | Soy · Wheat · Corn |
| `softs` | Cocoa · Sugar · Coffee |

---

## Output paths

Embed in session MD (not standalone Jobs / inbox primary file):

- Daily: `shared/reports/emily/YYYY-MM-DD-commodity-session.md` (Market insight section)  
- Weekly: `shared/reports/emily/YYYY-Www-commodities-session.md`  

Optional draft: same directory `…-insight-draft.md` — canonical remains trunk session.

---

## Required sections / tables

### Header stub

- as-of · cadence (daily / weekly) · complex coverage  
- Hard line: **Insight = what the market is saying** (balance / inventory / curve / positioning / narrative); **not** Trade map / `C_*`; do not finalize commodity / desk Risk-on/off; Not investment advice · emily ≠ Emily (broker)

### 1. Drivers insight (market drivers)

Write **3–7** mechanism sentences (Daily shorter; Weekly thicker). Each row should carry a layer tag:

| # | Layer | Insight (mechanism) | Cite / miss | Macro·Micro·Market |
|---|-------|-------------------|-------------|---------------------|
| 1 | physical-balance / inventory / term-structure / positioning / narrative / transmission | … | EIA / WASDE / COT / Yahoo / christina / News · as-of · URL or `miss` | macro / micro / market |
| … | … | … | … | … |

**Hard:**
- ❌ only "up / down" two words; write **why** (tight/loose / season / policy channel / dual-leg gap)  
- inventory / curve / COT no source → cell `miss`, rewrite as missing evidence, do not guess numbers  
- narrative (Market) **must not override** cited Micro facts; conflict → Tensions + Conf↓ pointer (hand to trunk)

### 2. Complex insight (precious / energy / industrial / grains / softs)

```markdown
### Complex insight

| Complex | One-line insight | Balance / inventory | Term structure | Positioning | Missing |
|---------|------------------|---------------------|----------------|-------------|---------|
| precious | … | cite-or-miss | Contango / Back / n/a / miss | COT / n/a / miss | … |
| energy | … | EIA … or miss | CL / BZ curve … or miss | … | … |
| industrial | … | LME / COMEX … or miss | … | … | … |
| grains | … | WASDE / S-U … or miss | … | … | … |
| softs | … | USDA / ICO / ICE certified … or miss | … | … | … |
```

- Daily: **≥3** valid complexes; unwritten tagged `skipped` + one-line reason  
- Weekly: five categories try complete; grains with auditable WASDE / PSD **must** have stocks-to-use **direction sentence** (loose / tight / flat) or `miss`  
- Every cell number / direction: **cite-or-miss**; ❌ blank treated as "normal"

Optional 2–4 bullets per complex (Supports-style mechanism; do not paste full puzzle).

### 3. Dual-leg insight (what US / UK-EU legs are saying)

```markdown
### Dual-leg insight

| Commodity | US leg read | UK/EU leg read | Attribution (diverge / converge) | Cite / miss |
|-----------|-------------|----------------|------------------------------|-------------|
| Oil | … | … | logistics / quality / geo / spread channel | Yahoo · as-of · … |
| … | … | … | proxy≠futures≠LSE / FX cite / … | … or miss |
```

- Daily: at least **Oil + one other**; rest may omit or `n/a`  
- Weekly: try ten columns; missing leg → leg `miss` + still write attribution where possible  
- ❌ two prices only with no mechanism; ❌ proxy written as LSE futures

### 4. Tensions

- **3–6** bullets: physical vs curve, inventory vs price, positioning vs balance, US vs UK/EU, complex × complex, world event channels colliding  
- Each tagged: `tension-type` (short label OK) + how direction / forecast / puzzle / trunk should use (Conf↓ / Scenario contrast) — **this section does not write** `C_*` / `DIR_*`

### 5. Missing evidence

| Item | Attempted source | Reason | Retry? | Handoff |
|------|------------------|--------|--------|---------|
| Oil inventory Δ | EIA WPSR | paywall / not released / stale | no (≤1) | trunk cite-or-miss lens |
| Soy S-U | WASDE | … | … | puzzle missing |
| COT MM net | CFTC Disagg | … | … | weekly only |
| LME copper stocks | LME public | … | … | … |
| FX / real-yield bridge | christina session | miss | … | Rates receive |

Sources footer: `Misses: see Missing evidence / Miss ledger`.

### 6. Handoff stub (mandatory)

```markdown
### Handoff
- **→ commodity-direction:** Drivers / Complex / Tensions / Missing (lean fuel; no DIR_* in this section)
- **→ commodity-forecast:** mechanism / lens pointers (no Est / Scenario finalize here)
- **→ commodity-puzzle:** Drivers #… · Complex … · Tensions … · Missing … (for puzzle)
- **→ commodity-session-report:** mechanism / lens pointers (inventory·term·COT); **do not** ghost-write Scenario / Trade map / commodity_regime
- **↛ commodity-signal-table:** no C_* / DIR_* / Obs levels in this section
- **← world-to-commodity:** digested event #…; insight does not recopy headlines-only
```

### 7. Sources (mandatory)

```markdown
## Sources (commodity-insight)
- 📊 Data: EIA WPSR · <as-of> · <URL or miss> · Oil inventory lens
- 📊 Data: USDA WASDE / PSD / Export Sales · <as-of> · <URL or miss> · grains / softs
- 📊 Data: CFTC COT Disagg · <week> · <URL or miss> · positioning (weekly)
- 📊 Data: LME / COMEX / LBMA / ICE certified public · <as-of> · <URL or miss>
- 📊 Data: Yahoo dual prints · <as-of> · session / sources-crawl cite
- 📊 Data: christina rates session cite (DFII / FX / DXY pointer) · <path or miss> · <as-of>
- 📰 News: <outlet> · <date> · <URL> · narrative only (do not invent Micro numbers)
- 📊 Institutional: World Bank Pink Sheet / ICO / USDA circular · <as-of> · or miss
- Misses: see Missing evidence
```

---

## Insight method (short · aligned with public framework)

When writing Drivers / Complex use this check (**all cite-or-miss**):

1. **Physical balance** — surplus/deficit direction one sentence (official balance / circular; else miss)  
2. **Inventory scoreboard** — level / direction / seasonal compare (EIA / exchange stocks / WASDE; else miss)  
3. **Term structure** — Contango / Backwardation one sentence (Daily: Oil+1; Weekly: try ten columns or miss)  
4. **Positioning** — COT etc. as **confirmation**, does not replace 1–3; intraday ❌  
5. **Narrative** — Emily-topic news / Market one sentence; ❌ headlines invent inventory  
6. **Consistency check** — five layers agree on scarcity / abundance / distortion; conflict → Tensions  

Classic crosses (use only with source, do not formula-fill without source):  
inventory↓ + price↑ ≈ demand-led; inventory↑ + price↓ ≈ soft demand; inventory↑ + price↑ ≈ unstable / flow; Contango ≈ loose storage; Back ≈ near-term tight — **all need cite or mark miss**.

---

## Term structure + convenience yield (cite-or-miss · qualitative)

**Cadence:** Daily = **Oil + one other** Contango / Back one sentence; rest may be `n/a`. Weekly = **try one sentence per ten columns** Contango / Backwardation; not auditable → row **`miss`** (row stays).

### Contango / Back qualitative checklist

| Check | Pass | Fail |
|-------|------|------|
| Shape label | Contango / Backwardation / flat / `miss` (dated / near-far auditable or public curve cite) | ❌ guess shape without source |
| Cadence coverage | Daily Oil+1; Weekly try-10 or miss | skip column / fake complete |
| Mechanism | one sentence: loose / tight / season / storage narrative (align inventory cite or miss) | only up/down |
| **Carry formula ban** | ❌ synthetic F−S, roll yield%, fake DV01 / fake storage cost numbers | formula without cite → `miss` |
| **Convenience yield** | **qualitative lens only**: outlet + as-of (or public curve narrative cite) → one sentence near-term tight/loose; else `n/a` / `miss` | ❌ invent CY numeric / formula |

**Convenience yield:** scarcity / storage **qualitative lens only**; not Est / `C_*` / `DIR_*` engine.

---

## COT crowdedness (cite-or-miss · Weekly Disagg Managed Money)

| Cadence | Behavior |
|---------|------|
| **Daily** | usually **`n/a`**; ❌ weekly COT as intraday signal / Direction / Est primary engine |
| **Weekly** | **CFTC Disagg Managed Money** (or auditable Disagg class) cite-or-miss: net direction / weekly change / crowding narrative one sentence; outlet + week / as-of + URL; paywall / missing → `miss` |

**Hard:**
- Positioning = **confirmation only**; does not replace physical / inventory / term  
- ❌ **never** rely on COT alone to fill `C_*`, Est band, or finalize lean in this section (this section also does not write `C_*` / `DIR_*`)  
- ❌ invent net position / fake percentile / fake crowding score  

---

## Banned

- This section contains `C_*` / `DIR_*` / Est band / Obs levels / bare `BUY` / `WATCH` / `NO_SIGNAL`  
- Invent inventory / COT / WASDE / term-structure numbers or fake curves  
- ❌ carry / convenience-yield **formula invent numbers** (qualitative lens + cite or n/a / miss only)  
- ❌ COT alone to imply `C_*` / Est (this section does not write them; handoff also forbidden)  
- OilPriceAPI / LSEG / Bloomberg / FactSet / ICE Fundamentals paid API as primary source  
- headlines-only (no mechanism / no layers)  
- social heat alone for insight · impersonate Alice desk regime · finalize `commodity_regime` here  
- `tm_score` / `valuation_score` / `B_*` / `FX_*` blend · self-fill DXY / DFII Est  
- `XAG-USD` · KC as equity · proxy as London futures (untagged `proxy≠futures≠LSE`)  
- full paste into Alice Jobs · separate emily Jobs / inbox primary file  

---

## Checklist

- [ ] Load order: sources → world → **insight** → direction → forecast → signal → puzzle → trunk  
- [ ] Drivers insight has mechanism + layer + cite-or-miss  
- [ ] Complex ≥3 (daily) / five categories try complete (weekly); labels only precious / energy / industrial / grains / softs  
- [ ] Dual-leg: Daily Oil+1; Weekly try ten columns; attribution present; proxy≠futures≠LSE  
- [ ] **Term structure:** Daily Oil+1; Weekly try-10 or miss; Contango / Back qualitative; ❌ carry formula invent; convenience yield = qualitative + outlet / as-of or n/a  
- [ ] **COT:** Daily usually n/a; Weekly Disagg Managed Money cite-or-miss; ❌ COT alone to fill C_* / Est  
- [ ] Tensions 3–6; Missing evidence table complete  
- [ ] Handoff stub complete (direction / forecast / puzzle / trunk; ↛ signal)  
- [ ] No `C_*` / `DIR_*` / Obs levels / bare BUY; no invent inventory / COT / fake curves  
- [ ] Paid blacklist zero hits; Sources Data / News / Institutional + Misses  
- [ ] Ticker SSOT; no `XAG-USD`; christina FX / rates cite only or miss  
- [ ] Embed in session; Not investment advice; emily ≠ Emily (broker)
