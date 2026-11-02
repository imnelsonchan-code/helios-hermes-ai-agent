---
name: commodity-sources-crawl
description: >-
  emily first-load crawl: all 10 commodities US+UK/EU, miss ledger + Sources.
  Precious US Last = gold-api XAU/XAG (Yahoo XAUUSD=X/XAGUSD=X dead).
  Miss recipes: LSE zero→miss; ban XAG-USD; JO name-check; proxy≠futures≠LSE;
  GBp disclose. Free Yahoo + gold-api only; never invent prints.
---

# Commodity sources crawl — first gate price/miss pull

**Owner:** emily · commodities · **Train:** session **first gate** → hand off world → insight → … → trunk  
**Load before:** `world-to-commodity` · `commodity-insight` · `commodity-direction` · `commodity-forecast` · `commodity-signal-table` · `commodity-puzzle` · `commodity-session-report`  
**Not:** Trade map / `C_*` / `DIR_*` · Risk-on/off · Jobs / inbox primary file · broker Emily / M7  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "Not investment advice · observation only". Source grading: `📊 Data` / `📰 News`.

---

## When to use

- **Every** daily / weekly session start: **must run before the price table**  
- Refresh miss ledger; hand available prints / as-of downstream  
- Softs / grains UK proxy, LSE ETC, JO and other trap symbols — this skill blocks them

### Not
- Do not output Trade map / Obs entry / SL / TP / `DIR_*` / Scenario  
- Do not use paid sources to fill gaps  
- Do not write crawl results as standalone Jobs

---

## Hard rules

1. **Ten columns × dual-leg all attempted** (20 cells intended); missing → `miss`, **do not invent**  
2. Softs / grains UK: mandatory tag **`proxy≠futures≠LSE`** (`SOYB` / `WEAT` / `CORN` / `NIB` / `CANE` / `JO`)  
3. ❌ **`XAG-USD`** (crypto) — Silver US = **`XAG` via gold-api**  
4. ❌ Yahoo **`XAUUSD=X` / `XAGUSD=X`** as primary anchor (dead / delisted) — do not silently use as Last  
5. ❌ Treat **`KC=F`** as equity narrative; Coffee US = ICE Arabica futures  
6. **`JO` name-check:** Yahoo name / description must look like coffee / softs ETF proxy; fail → that leg `miss` (do not hard-fill)  
7. **LSE zero / NaN / empty bar** (e.g. `SGLN.L` / `PHAG.L` / `COPA.L`) → that leg **`miss`**; ❌ stale value / old cache backfill  
8. **GBp / GBX:** if LSE quotes in pence, Sources / price table **must disclose** (GBp → GBP×0.01 or label not converted)  
9. miss > invent; at most **1 retry** per symbol, then Miss ledger  
10. Load order: sources → **world** → insight → direction → forecast → signal → puzzle → trunk  
11. **Handoff hard order (never skip):** prints → **world → insight → direction → forecast → THEN signal-table** → puzzle → trunk. ❌ crawl then hand straight to `commodity-signal-table`; ❌ skip insight / direction / forecast

---

## Free data only / ticker SSOT

**Allowed:** Yahoo Finance (non-precious spot) · **gold-api.com** (Gold / Silver US spot) · **FX / rates:** prefer cite `shared/reports/christina/…-rates-session.md` (or `miss`) as DFII / GBPUSD / DXY pointer; ❌ invent `FX_*` / `B_*` / Rate Δbp · ❌ this skill self-pulls FRED as rates depth  

**Banned:** OilPriceAPI · LSEG · Bloomberg · FactSet · ICE Fundamentals paid APIs · MCP-first vendor · metals-api paid · invent inventory / COT

### Precious metals US Last (hard · 2026-10)

Yahoo `XAUUSD=X` / `XAGUSD=X` **dead** (chart 404 / delisted). US Gold / Silver **primary anchor**:

| Leg | Endpoint | Cite fields |
|-----|----------|-------------|
| Gold US | `GET https://api.gold-api.com/price/XAU` | `price` + `updatedAt` (ISO) |
| Silver US | `GET https://api.gold-api.com/price/XAG` | `price` + `updatedAt` (ISO) |

- Disclose: **indicative spot** (≠ LBMA fix · ≠ COMEX futures)  
- Optional same-feed one-call: `https://xaus.com/api/v1/spot?compact=1` (upstream=gold-api; disclose both)  
- Fallback ladder: gold-api → Kitco HTML Bid+as-of (cite) → **`miss`**  
- ❌ use `GC=F` / `SI=F` to silent-fill US Last; **footnote** only + tag `futures≠spot`  
- ❌ invent mid / estimate price

### Ten-column dual-leg map (locked)

| Commodity | US | UK/EU | UK type |
|-----------|-----|-------|---------|
| Gold | `XAU` (gold-api) | `SGLN.L` | LSE ETC |
| Silver | `XAG` (gold-api) | `PHAG.L` | LSE ETC |
| Copper | `HG=F` | `COPA.L` | LSE ETC |
| Soy | `ZS=F` | `SOYB`* | US ETF proxy |
| Wheat | `ZW=F` | `WEAT`* | US ETF proxy |
| Corn | `ZC=F` | `CORN`* | US ETF proxy |
| Oil | `CL=F` | `BZ=F` | futures vs futures |
| Cocoa | `CC=F` | `NIB`* | US ETF proxy |
| Sugar | `SB=F` | `CANE`* | US ETF proxy |
| Coffee | `KC=F` | `JO`* | US ETF proxy — **name-check** |

\*Always disclose `proxy≠futures≠LSE`. `GC=F` / `SI=F` may footnote only; do not replace gold-api `XAU` / `XAG` spot. Orange juice / cotton OOU.

### Miss recipes (SSOT)

| Situation | Action |
|------|------|
| LSE print = 0 / NaN / no bar | That leg `miss`; log attempted symbol + as-of |
| gold-api / Kitco no `price`+as-of (after 1 retry) | That precious US leg `miss`; may footnote `GC=F` / `SI=F` (tag futures≠spot); ❌ silent as Last |
| Wrong Yahoo `XAUUSD=X` / `XAGUSD=X` as primary anchor | **Reject**; use gold-api or US `miss` |
| Wrong pull `XAG-USD` | **Reject**; pull gold-api `XAG` or silver US `miss` |
| `JO` name not coffee / softs-like | UK Coffee leg `miss` |
| Proxy written as "London futures" | FAIL — retag proxy≠futures≠LSE |
| GBp not disclosed | FAIL — add GBp / GBX note |
| Yahoo timeout after 1 retry still no data (non-precious) | `miss` + ledger |

---

## Post-crawl QA checklist (hard · data quality checker)

**Timing:** Dual-leg pull **after**, handoff to world **before** must pass. Any FAIL → that cell / leg goes to **Miss ledger only**; ❌ stale value / old cache / complex "guess" backfill; **never invent / backfill**.

`DIR_*` 1D% may only come from GLD / `GC=F` (silver SLV / `SI=F`) previous close, cited in that table row; gold-api spot is level only. Missing prev close → `miss`. `BZ=F` row must say ICE Brent financial futures, same source CL–BZ, same pull, same as-of. Missing → `miss`.

| # | Check | Pass | Fail → |
|---|-------|------|--------|
| 1 | **Ticker SSOT** | Ten columns use only table above; Gold / Silver US=`XAU` / `XAG` (gold-api) | Wrong symbol → fix or `miss` + ledger |
| 2 | **Yahoo XAU / XAG ban** | Primary anchor does not use dead `XAUUSD=X` / `XAGUSD=X` | Use gold-api or US `miss` |
| 3 | **`XAG-USD` ban** | Zero hits on crypto `XAG-USD` in body | Reject; use gold-api `XAG` or silver US `miss` |
| 4 | **GBp / GBX** | LSE pence disclosed (GBp→GBP×0.01 or label not converted) | FAIL → add note or leg `miss` |
| 5 | **proxy≠futures≠LSE** | `SOYB` / `WEAT` / `CORN` / `NIB` / `CANE` / `JO` tagged; not as London futures | FAIL → retag or `miss` |
| 6 | **LSE zero → miss** | `SGLN.L` / `PHAG.L` / `COPA.L` if 0 / NaN / empty bar → `miss` | ❌ stale backfill |
| 7 | **as-of required** | Every cell with a print has as-of (date / time; gold-api=`updatedAt`) | No as-of → cell `miss` |
| 8 | **`data_delay` (optional)** | May tag `realtime` | `delayed` | `stalled` | `miss` (per leg or whole table) | `stalled` / unclear → lean Conf↓ on handoff; do not guess price |

**QA result stub (embed before Sources):**

```markdown
### Post-crawl QA
- Ticker SSOT: pass / fail→miss
- Yahoo XAU/XAG ban: pass
- XAG-USD ban: pass
- GBp disclosed: pass / n/a / miss
- proxy≠futures≠LSE: pass / miss
- LSE zero→miss: pass
- as-of present: pass / miss
- data_delay (opt): realtime | delayed | stalled | miss
- Failures → Miss ledger only (no invent backfill)
```

---

## Output paths

- Miss ledger + dual-leg results + Sources → **embed** in session:  
  - `shared/reports/emily/YYYY-MM-DD-commodity-session.md`  
  - `shared/reports/emily/YYYY-Www-commodities-session.md`  
- Prints / miss **only** hand off to `world-to-commodity` (then insight → direction → forecast → **THEN** `commodity-signal-table`). ❌ after crawl jump to signal-table draft  
- ❌ `inbox/` · ❌ separate Jobs light

---

## Crawl budget

| Cadence | Price legs | News (optional) | History raw |
|---------|------------|--------------|-------------|
| Daily | All ten-column legs attempted | ≤5 public URLs | not required |
| Weekly | same as daily | ≤12 URLs | optional 1M / 3M / 1Y raw prints to trunk history |

---

## Required sections / tables

### 1. Dual-leg pull results

```markdown
| Commodity | US symbol | US print | US as-of | UK/EU symbol | UK/EU print | UK as-of | Ccy note | Grade |
|-----------|-----------|----------|----------|--------------|-------------|----------|----------|-------|
| Gold | XAU · gold-api | … or miss | … | SGLN.L | … or miss | … | GBp? | 📊 Data |
| Silver | XAG · gold-api | … | … | PHAG.L | … | … | … | … |
| Copper | HG=F | … | … | COPA.L | … | … | … | … |
| Soy | ZS=F | … | … | SOYB | … | … | proxy≠futures≠LSE | … |
| Wheat | ZW=F | … | … | WEAT | … | … | proxy≠futures≠LSE | … |
| Corn | ZC=F | … | … | CORN | … | … | proxy≠futures≠LSE | … |
| Oil | CL=F | … | … | BZ=F | … | … | futures≠spot | … |
| Cocoa | CC=F | … | … | NIB | … | … | proxy≠futures≠LSE | … |
| Sugar | SB=F | … | … | CANE | … | … | proxy≠futures≠LSE | … |
| Coffee | KC=F | … | … | JO | … or miss | … | proxy≠futures≠LSE · name-check | … |
```

### 2. Miss ledger (mandatory if any miss)

```markdown
### Miss ledger
| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| SGLN.L | UK Gold | Yahoo | LSE zero/NaN | 1× done |
| JO | UK Coffee | Yahoo | name-check fail | 1× done |
| XAG-USD | — | blocked | crypto ban; use gold-api XAG | n/a |
| XAUUSD=X | US Gold | blocked | Yahoo dead; use gold-api XAU | n/a |
```

### 3. Sources

```markdown
## Sources (commodity-sources-crawl)
- 📊 Data: gold-api · XAU / XAG · <price> · <updatedAt> (indicative spot)
- 📊 Data: Yahoo · <non-precious symbols> · <as-of> · dual-leg pull
- 📊 Data: christina rates session cite (DFII / FX pointer) · <path or miss> · <as-of>
- 📰 News: <outlet> · <date> · <URL> (if crawl budget pulled news)
- Misses: see Miss ledger
- Disclosure: proxy≠futures≠LSE (ag/softs UK); GBp on LSE where applicable; GC=F / SI=F footnote only (futures≠spot)
```

### 4. Handoff note (one sentence)

Hand off **world → insight → direction → forecast → THEN signal-table → puzzle → trunk** (SSOT; **never** crawl→signal skip): which legs `miss`, which need Conf≤L (proxy-only).

---

## Banned

- Paid sources to fill gaps (OilPriceAPI / LSEG / Bloomberg)  
- LSE 0 / NaN stale-value backfill  
- Write `SOYB` / `JO` etc. as London futures  
- Output Trade map / `C_*` / Risk-on/off  
- `XAG-USD` · Yahoo `XAUUSD=X` / `XAGUSD=X` as primary anchor · KC as equity · JO name-check fail still filled with price  
- `GC=F` / `SI=F` silent-fill US Last (footnote only)  
- Invent prints · write inbox / Jobs  
- ❌ after crawl direct handoff / skip handoff to `commodity-signal-table` (must run world → insight → direction → forecast first)

---

## Checklist

- [ ] Session first gate; ten columns × dual-leg (10×2) all attempted  
- [ ] Miss ledger complete; miss > invent; ≤1 retry per symbol  
- [ ] Softs / grains UK: `proxy≠futures≠LSE` tagged  
- [ ] Gold / Silver US = gold-api `XAU` / `XAG` + `updatedAt`; ❌ Yahoo `XAUUSD=X` / `XAGUSD=X` primary; ❌ `XAG-USD`  
- [ ] ❌ KC not as equity; `JO` name-checked (fail → miss)  
- [ ] LSE zero / NaN → miss (no stale backfill)  
- [ ] GBp / GBX disclosed (when applicable)  
- [ ] **Post-crawl QA** all pass (ticker SSOT · Yahoo XAU/XAG ban · XAG-USD ban · GBp · proxy≠futures≠LSE · LSE zero→miss · as-of · optional data_delay); failures → Miss ledger only; ❌ invent backfill  
- [ ] Precious: gold-api (+ Kitco fallback); other: Yahoo (+ public news URLs); **FX / rates:** christina cite or `miss` (❌ self-pull FRED DFII / DXY as rates depth); no LSEG / OilPriceAPI  
- [ ] Sources complete; no Trade map / Jobs / inbox  
- [ ] Load order: sources → world → insight → direction → forecast → signal → puzzle → trunk  
- [ ] Handoff: **world → insight → direction → forecast → THEN signal → puzzle → trunk** (❌ crawl→signal skip)
