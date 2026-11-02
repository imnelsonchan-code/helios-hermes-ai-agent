---
name: world-to-commodity
description: >-
  emily world-event → channel → dual-venue impact across the locked 10
  commodities. Daily 3–5 verifiable events; weekly thicker. Channels enum
  only. No headlines-only; no desk-wide Risk-on/off; free Yahoo/FRED/news.
---

# World → commodity — world events → commodity transmission

**Owner:** emily · commodities · **Train:** session draft → trunk embed → Alice cite  
**Load after:** `commodity-sources-crawl` (price/miss already complete)  
**Load before:** `commodity-insight` → `commodity-direction` → `commodity-forecast` → `commodity-signal-table` → `commodity-puzzle` → `commodity-session-report` (trunk)  
**Not:** Alice news ledger · social heat alone for transmission · custom desk-wide Risk-on/off · broker Emily / M7 · parallel open Trade map (must wait for forecast)  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "Not investment advice · observation only". Source grading: `📰 News` / `📊 Data` / `📊 Institutional`.

---

## When to use

### Daily lite
- **3–5** verifiable world events (with URL/outlet/date)  
- Per event: mechanism sentence + ≥1 channel + **ten-column × dual-leg** impact (or `N/A`/`miss`)  
- Do not cover only precious metals; oil/grains/softs must be representative or explicit `miss`

### Weekly depth
- Events may be thicker (ag/oil/softs/geo/policy must have coverage or miss reason)  
- Same channel enumeration and ten-column dual-leg matrix

### Not
- Do not write as standalone Jobs report / do not open separate Jobs light  
- Do not use X/Reddit heat **alone** for transmission direction  
- Do not finalize "Commodity Risk-on/off" in this skill (hand off to `commodity-puzzle` suggest → trunk finalize)  
- Do not invent inventory/COT/crop report numbers  
- ❌ Parallel full Obs levels with `commodity-signal-table` (must wait for forecast)

---

## Hard rules

1. **Each event must have:** one mechanism sentence (why it transmits to commodities) + ≥1 **channel** (enumeration below) + ten-column impact matrix (US leg + UK/EU leg)  
2. **Channel enumeration (only these allowed):**  
   `supply` · `demand` · `risk-premium` · `USD` · `real-yield` · `weather` · `policy` · `other`  
   Multiple channels may be listed; custom strings → FAIL  
3. **Ten-column complete:** Gold…Coffee each row must have US/UK-EU cells (no impact → `N/A`; no data → `miss`) — **do not skip columns**  
4. ❌ headlines-only (headings only, no mechanism)  
5. ❌ This section **does not finalize** commodities/desk-wide Risk-on/Neutral/Risk-off/Crisis (puzzle suggest → **trunk must write** formal section)  
6. ❌ Invent inventory, output, COT; missing → `miss` + Sources  
7. Load order: sources → **world** → insight → direction → forecast → signal → puzzle → trunk  
8. **Handoff → `commodity-insight`:** hand off events/channels/ten-column impact; insight **deepens** "what the market is saying", do not recopy headlines-only

---

## Supply–demand shock scenario skeleton (qualitative · feeds forecast)

Each major supply/demand/policy shock (optional but **Weekly suggest ≥1**; Daily when present) follows this skeleton — **qualitative mechanism only**:

```text
Shock type → Channel enum → Dual-leg impact → bull|base|bear mechanism pointer
```

| Step | Content | Hard constraint |
|------|---------|-----------------|
| **1. Shock type** | e.g. supply outage/demand spike/policy ban/weather crop/risk-premium geo | One sentence; needs outlet + date |
| **2. Channel enum** | Only allowed: `supply` · `demand` · `risk-premium` · `USD` · `real-yield` · `weather` · `policy` · `other` | Custom strings → FAIL |
| **3. Dual-leg impact** | Ten-column US + UK/EU: `↑`/`↓`/`flat`/`N/A`/`miss` + half sentence | Skip column not allowed; proxy≠futures≠LSE |
| **4. bull｜base｜bear pointer** | Hand off one **mechanism bias** sentence to `commodity-forecast` (do not finalize Est/`C_*` in this skill) | Qualitative; ❌ fake precise Q |

**❌ Linear fake Q/equilibrium invent (hard):**  
Do not use synthetic supply/demand curves, fake mbbl/fake output Δ%, fake "equilibrium price = a−bQ" fill numbers. No official source → that shock numbers cell **`miss`**; write only channel + dual-leg direction narrative.

**Calendar/official windows (news→impact alignment):**  
Near-term public windows cite only **free official** dates: EIA WPSR · USDA WASDE · Export Sales · CFTC COT · softs official monthly report/circular. **Unknown window → `miss`**. ❌ **FMP/paid calendar invent dates**; ❌ use news to invent report numbers.

---

## Free data only / ticker SSOT

**Allowed:** Upstream sources (incl. **gold-api** precious metals) · Yahoo Finance · public news/official calendar URLs · **FX/rates:** prefer cite `shared/reports/christina/…-rates-session.md` (or missing → `miss`) as DFII/GBPUSD/DXY pointer to explain `USD`/`real-yield`; ❌ invent `FX_*`/`B_*`/Rate Δbp · ❌ this skill self-fetch FRED as rates depth  

**Banned:** OilPriceAPI · LSEG · Bloomberg · FactSet · ICE Fundamentals paid APIs · `XAG-USD` (crypto) · invent inventory

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

\*Ag/softs UK leg: `proxy≠futures≠LSE`; missing → `miss`. Silver: **use only** gold-api `XAG`, ❌ `XAG-USD` · ❌ Yahoo `XAGUSD=X`.

---

## Output paths

Embed in session MD (not standalone Jobs):

- Daily: `shared/reports/emily/YYYY-MM-DD-commodity-session.md` ("world events → commodities" section)  
- Weekly: `shared/reports/emily/YYYY-Www-commodities-session.md`  

Optional draft: same directory `…-world-draft.md` — canonical remains trunk session.

---

## Required sections / tables

### Header stub

- as-of · cadence (daily/weekly) · event count  
- Hard line: this table is transmission observation only; **does not set** commodities/desk-wide Risk-on/off; Not investment advice

### 1. Event list

| # | Event | Date | Outlet / URL | Channel(s) | Grade |
|---|-------|------|--------------|------------|-------|
| 1 | … | YYYY-MM-DD | … | supply · policy | 📰 News |
| … | … | … | … | … | … |

Daily: **3–5** rows (fewer than 3 → explain or FAIL).

### 2. Per event: mechanism + transmission matrix

Each event: write **mechanism (1–3 sentences)** first, then ten-row dual-leg table:

```markdown
#### Event N — <short title>
- **Mechanism:** …
- **Channels:** `supply` / `demand` / …

| Commodity | US leg | UK/EU leg | Note |
|-----------|--------|-----------|------|
| Gold | ↑/↓/flat/N/A/miss · one line | … | spot vs ETC |
| Silver | … | … | ❌ do not use XAG-USD |
| Copper | … | … | …
| Soy | … | … | proxy≠futures≠LSE |
| Wheat | … | … | …
| Corn | … | … | …
| Oil | … | … | WTI vs Brent |
| Cocoa | … | … | …
| Sugar | … | … | … |
| Coffee | … | … | JO name-check |
```

Direction short tags: `↑`/`↓`/`flat`/`N/A`/`miss` + half-sentence reason; no stray spaces.

### 3. Cross-event tensions (bullets)

- 2–5 bullets: which events support/conflict; which columns missing data  
- How to hand off `commodity-puzzle` (do not set regime here)

### 3b. Shock skeleton stub (when shock present · suggest)

```markdown
### Shock skeleton (cite-or-miss)
| Shock type | Channel(s) | Dual-leg focus | → Forecast bull/base/bear pointer | Cite / miss |
|------------|------------|----------------|-----------------------------------|-------------|
| … | supply · policy | Oil CL/BZ · … | base: …; bear if … | outlet · date · URL |
```

❌ Linear fake Q/equilibrium invent. Calendar window unknown → `miss` (❌ FMP invent dates).

### 4. Sources (mandatory)

```markdown
## Sources (world-to-commodity)
- 📰 News: <outlet> · <date> · <URL> · event #
- 📊 Data: Yahoo · <as-of> · <series or ticker> (if any)
- 📊 Data: christina rates session cite (DFII/FX pointer) · <path or miss> · <as-of>
- Misses: <event or leg> · attempted + miss
```

---

## Banned

- Headings-only ledger, no mechanism/no channels  
- This section **does not finalize** commodities/desk-wide Risk-on/off (hand off puzzle suggest → trunk writes `commodity_regime`)  
- Social heat alone for transmission · only Au/Ag while skipping softs/grains (no miss reason)  
- Full body paste into Alice Jobs · separate emily Jobs light  
- OilPriceAPI/LSEG/invent inventory/`XAG-USD`  
- ❌ Linear fake Q/equilibrium invent · ❌ FMP/paid calendar invent official window dates

---

## Checklist

- [ ] Load order: sources → **world** → insight → direction → forecast → signal → puzzle → trunk  
- [ ] Daily 3–5 events (or written explanation); weekly has ag/oil/softs representative or miss  
- [ ] Per event: mechanism sentence + ≥1 **enumerated channel**  
- [ ] Per event ten-column dual-leg matrix complete (`N/A`/`miss` OK; skip column not allowed)  
- [ ] Channels only: `supply`/`demand`/`risk-premium`/`USD`/`real-yield`/`weather`/`policy`/`other`  
- [ ] **Shock skeleton** (when present): Shock type → channel → dual-leg → bull｜base｜bear pointer; ❌ fake Q/equilibrium invent  
- [ ] Calendar: EIA/WASDE/Export Sales/COT/softs official windows; unknown → `miss`; ❌ FMP invent dates  
- [ ] No headlines-only; no this-section Risk-on/off  
- [ ] Ticker SSOT; proxy≠futures≠LSE; no `XAG-USD`  
- [ ] Sources + Misses complete; Not investment advice  
- [ ] Embed session; no standalone Jobs/inbox primary file
