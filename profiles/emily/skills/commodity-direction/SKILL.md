---
name: commodity-direction
description: >-
  emily directional bias / regime lean per commodity and complex. DIR_*
  vocabulary only (not C_*, not bare BUY/SELL, not tm_score). Feeds Scenario,
  signal-table, and commodity_regime lean; never invents inventory/COT/curve
  numbers or Obs levels. Observation only; emily ≠ Emily broker.
---

# Commodity direction — directional bias (regime lean)

**Owner:** emily · commodities · **Train:** draft → trunk (`commodity-session-report`) embed  
**Load after:** `commodity-sources-crawl` → `world-to-commodity` → `commodity-insight`; cite-or-miss lenses (inventory / term structure / COT) **cite when present, else `miss` / `n/a`**  
**Load before / feeds:** `commodity-forecast` (Scenario) · `commodity-signal-table` (`C_*` draft) · `commodity-puzzle` (complex lean → suggested `commodity_regime`) · trunk finalize  
**Not:** replace Trade map Obs levels · replace `C_*` Signal · invent inventory / COT / fake curves · broker Emily / M7 orders · desk-wide Risk-on/off (Alice)  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "Not investment advice · observation only". Source grading: `📊 Data` / `📰 News` / `📊 Institutional`.

---

## When to use

### Daily lite
- One **Direction** line per ten columns (short rationale OK)  
- Complex roll-up: **≥3** complexes one-sentence lean (among precious / energy / industrial / grains / softs touched)  
- Term-structure touch: align SOUL — **Oil + one other**; rest may be `n/a`  
- Inventory: cite official touchpoint when present; else `n/a` / `miss`  
- COT: **usually `n/a`** (not the daily Direction primary engine)

### Weekly depth
- **All ten columns** Direction + one mechanism sentence (supply-demand / structure / transmission / calendar)  
- Complex roll-up: **five complexes** one row each (no touch → that row `n/a` + reason, do not delete row)  
- Inventory / term-structure / COT: **cite-or-miss** (ten columns or auditable rows); grains WASDE / PSD → stocks-to-use **direction sentence** when present  
- Output feeds Scenario bull | base | bear and puzzle suggested regime

### Not
- ❌ standalone Jobs / inbox primary file  
- ❌ use Direction to fill Obs entry / SL / TP directly  
- ❌ write Direction as `C_*` or bare `BUY` / `SELL`  
- ❌ invent numbers to support lean

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

### Direction ≠ Signal (hard separation)

| Layer | Skill / column | Vocabulary | Role |
|----|-----------|------|------|
| **Direction** | **this skill** | `DIR_*` only | directional bias / regime lean (mechanism + confidence) |
| **Signal** | `commodity-signal-table` | `C_*` / `NO_SETUP` / `miss` | observation setup; may take Direction **hints**, **not** auto-equal |
| **Obs levels** | signal-table / trunk | entry / cut / TP | **Basis gate**; this skill **never** invents / fills levels |
| **Regime** | puzzle suggest → trunk | `commodity_regime` | Risk-on / Neutral / Risk-off / Crisis; Direction complex lean **may feed**, **do not** impersonate final call |

**Mapping (hint only, not equivalence):**
- `DIR_BULLISH` (Conf≥M, Invalidation present) → may hint `C_BUY` / `C_HOLD` candidates; still need Yahoo features / Basis / trim  
- `DIR_BEARISH` → may hint `C_REDUCE` candidate  
- `DIR_NEUTRAL` / `DIR_TWO_WAY` → lean `C_WAIT` / `NO_SETUP`  
- `DIR_UNCLEAR` / `miss` → `NO_SETUP` / `miss`; Conf↓  
- ❌ `DIR_*` → bare `BUY` / `SELL` · ❌ use `tm_score` / `valuation_score` to change Direction · ❌ Direction as quantity / order

### DIR_* enum (namespaced — prevent C_* / equity bleed)

| Direction | Meaning (observation lean) |
|-----------|-------------------|
| `DIR_BULLISH` | bullish / upside bias (not an order) |
| `DIR_BEARISH` | bearish / downside bias (not an order) |
| `DIR_NEUTRAL` | no clear direction; range / balance |
| `DIR_TWO_WAY` | two-way risk side-by-side (pre/post event / conflicting structure); do not force one side |
| `DIR_UNCLEAR` | insufficient / unresolved conflict (tend toward `miss` touchpoints later) |
| `miss` | data / source insufficient; **do not** guess lean |

**Banned labels:**  
❌ bare `BUY` / `SELL` / `WATCH` / `NO_SIGNAL` · ❌ unprefixed `BULLISH` / `BEARISH` in Signal column · ❌ `C_BUY` etc. in **Direction** column · ❌ `tm_score` · ❌ bare `score`

### Required triad per row

1. **Conf:** `H` / `M` / `L` — proxy-only or single-leg driven → ≤`L`; conflicting sources → ≤`M` or `DIR_TWO_WAY` / `DIR_UNCLEAR`  
2. **Invalidation:** one observation failure (event / structure / dual-leg attribution break); recommended  
3. **Dominant lens tag:** only `macro-led` / `micro-led` / `market-led` / `mixed` (align SOUL Basis tag)

### Cite-or-miss lenses (not an invent engine)

**miss > invent (hard).** Direction **only** leans on auditable sources; missing → that dimension `miss` / `n/a`, **do not** fill fake inventory / COT / curves.

| Dimension | Role | Daily | Weekly |
|------|------|-------|--------|
| Supply–demand / transmission | primary direction | world channel one-liner | thicker mechanism |
| Inventory | rhythm | cite official touch when present | ten-column cite-or-miss |
| Term structure | confirm / disconfirm | Oil + one other Contango / Back | ten-column one-liner or `miss` |
| COT (Disagg) | crowding / weekly filter | usually `n/a` | cite-or-miss; ❌ not daily primary signal |
| Stocks-to-use (grains) | tight/loose sentence | not required | WASDE / PSD → direction sentence when present |

**Practical read (do not apply without source):** tight balance + destock + backwardation + non-extreme crowding → lean `DIR_BULLISH`; surplus + build + contango + crowded longs → lean `DIR_BEARISH`; lenses contradict → `DIR_TWO_WAY` / `DIR_NEUTRAL` + Conf↓.

### Term structure + convenience yield (cite-or-miss · feeds lean, do not invent)

| Cadence | Term structure | Convenience yield |
|---------|----------------|-------------------|
| **Daily** | **Oil + one other** Contango / Back one-liner; rest `n/a` | qualitative one-liner or `n/a`; need outlet / as-of or mark miss |
| **Weekly** | **try ten columns** Contango / Back one-liner; not auditable → `miss` | same; ❌ fake CY numbers |

**Checklist:** Contango / Back / flat / `miss` label + half-sentence mechanism; ❌ **carry formula** (F−S / fake roll% / fake storage cost) invent numbers as lean evidence. Convenience yield = **qualitative lens only** (near-term tight / loose narrative); cite when present, else `n/a` / `miss`.

### COT crowdedness (cite-or-miss)

| Cadence | Behavior |
|---------|------|
| **Daily** | **usually `n/a`**; ❌ weekly COT as daily Direction primary engine |
| **Weekly** | **Disagg Managed Money** (or auditable Disagg) cite-or-miss: crowding / weekly change one-liner; outlet + week + URL; missing → `miss` |

**Hard:** ❌ **never** rely on COT alone to fill / imply this table's `DIR_*` then auto-map to `C_*` or Est (COT only adjusts Conf / Invalidation / lens touch); ❌ invent net position. **`C_*` / Est never written in this skill.**

### Other hard constraints

- Ten columns complete; missing → row `miss`, **row does not disappear**  
- ❌ quantity · ❌ order type · ❌ "send to Emily" · ❌ invent Obs entry / SL / TP  
- FX / real rates / curves: **christina cite only**; ❌ self-fill `FX_*` / `B_*` / DXY Est / Rate Δbp  
- Real-rate sentences may only verbatim cite same-day christina revised DFII5 / DFII10 (with as-of). Series name is DGS* or level equals DGS10 in same doc → that sentence `miss`.  
- `DIR_*` 1D% may only come from GLD / `GC=F` (silver SLV / `SI=F`) previous close, cited in that row; gold-api spot is level only. Missing prev close → `miss`.  
- `BZ=F` row must say ICE Brent financial futures, same source CL–BZ, same pull, same as-of. Missing → `miss`.  
- Silver: gold-api `XAG` (❌ `XAG-USD` · ❌ Yahoo `XAGUSD=X`); KC ≠ equity; proxy≠futures≠LSE  
- E5: do not mix `tm_score` / `valuation_score` / `rates_signal`

---

## Free data only / ticker SSOT

**Allowed:** upstream sources dual-leg (precious = gold-api) · world transmission · Yahoo · EIA WPSR / USDA WASDE·PSD·Export Sales / CFTC COT Disagg / LME·COMEX·LBMA·ICE certified **public pages** / ICO / USDA softs circular / World Bank Pink Sheet (weekly scenario cross-check) · christina rates session cite  

**Banned:** OilPriceAPI · LSEG / Bloomberg / FactSet · ICE Fundamentals paid APIs · invent inventory / COT / term structure

### Ten columns

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

\*proxy≠futures≠LSE. Orange juice / cotton etc. OOU.

### Complex ↔ columns (roll-up)

| Complex | Typical columns |
|---------|--------|
| `precious` | Gold · Silver |
| `energy` | Oil (CL / BZ) |
| `industrial` | Copper |
| `grains` | Soy · Wheat · Corn |
| `softs` | Cocoa · Sugar · Coffee |

Roll-up Direction = **narrative lean** weighted within complex (state which columns dominate); conflict → `DIR_TWO_WAY` / `DIR_NEUTRAL`, not fake consensus vote.

---

## Output paths

Optional draft (review before trunk embed):

| Cadence | Path |
|---------|------|
| Daily | `shared/reports/emily/YYYY-MM-DD-commodity-direction-draft.md` |
| Weekly | `shared/reports/emily/YYYY-Www-commodity-direction-draft.md` |

Canonical embed:

- Daily: `shared/reports/emily/YYYY-MM-DD-commodity-session.md` ("Commodity direction" section)  
- Weekly: `shared/reports/emily/YYYY-Www-commodities-session.md`  

❌ do not write inbox / Jobs light

---

## Required sections / tables

### 1. Meta

- As-of · cadence (daily / weekly) · data grade  
- Hard line: Direction ≠ Signal · observation only · emily ≠ Emily (broker/M7) · Not investment advice  
- One line: **this table does not fill Obs levels or place orders**

### 2. Per-commodity Direction table (ten rows · mandatory)

```markdown
| Commodity | Direction | Conf | Dominant | Invalidation | Lean note (mechanism) | Lens touch (inv / TS / COT / S-U) |
|-----------|-----------|------|----------|--------------|----------------------|--------------------------------|
| Gold | DIR_* / miss | H/M/L | macro-led / micro-led / market-led / mixed | {break / event / structure} | {supply-demand / transmission / structure; not only up/down} | cite · n/a · miss |
| Silver | | | | | | |
| Copper | | | | | | |
| Soy | | | | | | |
| Wheat | | | | | | |
| Corn | | | | | | |
| Oil | | | | | | |
| Cocoa | | | | | | |
| Sugar | | | | | | |
| Coffee | | | | | | |
```

### 3. Complex roll-up (mandatory)

```markdown
| Complex | Direction | Conf | Dominant | Drivers (which columns) | Tensions / missing |
|---------|-----------|------|----------|-------------------|--------------------|
| precious | DIR_* / n/a / miss | H/M/L | … | Gold · Silver | … |
| energy | | | | Oil | … |
| industrial | | | | Copper | … |
| grains | | | | Soy · Wheat · Corn | … |
| softs | | | | Cocoa · Sugar · Coffee | … |
```

Daily: at least **3** valid complexes; Weekly: **all five rows** (no touch → `n/a` + reason).

### 4. Map → Scenario / Signal / Regime (handoff box · mandatory)

```markdown
### Handoff
- ← **commodity-insight:** take Drivers / Complex / Tensions / Missing as lean fuel
- → **commodity-forecast:** per-column Direction as bull | base | bear **bias hints** (does not replace scenario sentences / Est; Forecast still needs mechanism)
- → **commodity-signal-table:** Direction hints `C_*` candidates only; Signal / Obs levels / Daily ≤3 trim **still signal-table**; this skill has no levels, **does not write** `C_*`
- → **commodity-puzzle / trunk regime:** complex lean feeds "suggested commodity Risk-on/off"; formal `commodity_regime` **trunk finalizes**; Alice desk-wide may cite
- → **do not:** quantity / orders / bare BUY·SELL / Obs levels / rewrite finalized `C_*`
```

### 5. Daily / Weekly depth note

```markdown
### Cadence note
- Daily: TS = Oil + <Commodity>; COT = n/a (unless exception cite); mechanism sentences may be short; convenience yield = qualitative or n/a
- Weekly: TS try-10 or miss; Inventory / COT Disagg MM cite-or-miss; grains S-U when present; five complexes complete; ❌ carry formula invent
```

### 6. Omissions / Miss ledger touchpoints

```markdown
### Omissions
- <Commodity or lens>: attempted + miss · <source tried>
```

### 7. Sources + Footer

```markdown
## Sources (commodity-direction)
- 📊 Data: Yahoo dual prints · as-of · symbols
- 📊 Data / Institutional: EIA / WASDE / COT / vault — cite or miss
- 📰 News: Emily-topic only (filter before Scenario finalize; URL budget per trunk)
- 📊 Data: christina rates cite (FX / real-rate pointer) · or miss
- Misses: …

## Footer
Not investment advice · observation only · emily ≠ Emily (broker/M7)
Direction = DIR_* only · ≠ C_* · no bare BUY/SELL · no tm_score · no Obs levels · no quantity
```

---

## Blank scaffold (copy-paste)

```markdown
# emily · commodities — Commodity direction draft
**As-of:** YYYY-MM-DD · **Cadence:** daily / weekly
**Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7)
**Hard:** Direction ≠ Signal · no Obs levels · no quantity / orders

## Direction table (ten columns)

| Commodity | Direction | Conf | Dominant | Invalidation | Lean note (mechanism) | Lens touch (inv / TS / COT / S-U) |
|-----------|-----------|------|----------|--------------|----------------------|--------------------------------|
| Gold | | | | | | |
| Silver | | | | | | |
| Copper | | | | | | |
| Soy | | | | | | |
| Wheat | | | | | | |
| Corn | | | | | | |
| Oil | | | | | | |
| Cocoa | | | | | | |
| Sugar | | | | | | |
| Coffee | | | | | | |

## Complex roll-up

| Complex | Direction | Conf | Dominant | Drivers (which columns) | Tensions / missing |
|---------|-----------|------|----------|-------------------|--------------------|
| precious | | | | | |
| energy | | | | | |
| industrial | | | | | |
| grains | | | | | |
| softs | | | | | |

### Handoff
- → commodity-forecast (Daily + Weekly must have ten-column table): …
- → commodity-signal-table (C_* only; this table has no levels): …
- → puzzle / trunk `commodity_regime` (suggested lean; final in trunk): …

### Cadence note
- …

### Omissions
- …

## Sources
- 📊 Data: …
- Misses: …

## Footer
Not investment advice · observation only · emily ≠ Emily (broker/M7) · DIR_* only · ≠ C_* · no bare BUY/SELL · no tm_score
```

---

## Handoff with Scenario / Signal / Puzzle / Trunk

| Item | commodity-direction | Downstream |
|------|---------------------|------|
| Per-column lean | `DIR_*` + Conf + Invalidation + Dominant | → forecast Scenario bias hints; **does not** replace bull | base | bear / Est |
| Signal | **does not write** `C_*` (only `DIR_*`) | `commodity-signal-table` produces Signal / shadow / Daily ≤3 |
| Obs levels | **never fill** | signal-table / trunk; **Basis gate** |
| Complex lean | roll-up table | puzzle suggests Risk-on/off; trunk writes formal `commodity_regime` |
| Lenses | cite-or-miss touchpoints | trunk Inventory / TS / COT sections may cite same as-of |
| Risk-on/off final | **does not write formal section** | trunk required; this skill handoff only |

**LOAD ORDER (repeat):** sources → world → insight → **direction** → forecast → signal → puzzle → trunk.  
Direction hints downstream `C_*` / Scenario only; **do not** edit Trade map directly in this skill.

---

## Banned

- bare `BUY` / `SELL` / `WATCH` / `NO_SIGNAL` · unprefixed BULLISH as Signal  
- Direction column `C_*` · or `C_*` column with `DIR_*` mixed in same cell  
- `tm_score` / `valuation_score` / bare `score` / live sleeve blend  
- invent inventory / COT / term structure / WASDE numbers · invent Obs entry / SL / TP  
- ❌ carry / CY **formula invent**; ❌ COT alone to fill / imply `C_*` / Est  
- quantity / order type / "send to Emily"  
- `XAG-USD` · KC as equity · proxy as LSE futures (untagged)  
- self-fill DXY / `FX_*` / `B_*` / Rate Δbp  
- impersonate Alice desk regime · output inbox / second Jobs file  
- weekly COT as daily Direction primary engine

---

## Checklist

- [ ] Ten Direction rows; only `DIR_BULLISH` / `DIR_BEARISH` / `DIR_NEUTRAL` / `DIR_TWO_WAY` / `DIR_UNCLEAR` / `miss`  
- [ ] Each row Conf (H / M / L) + Invalidation + Dominant (`macro-led` | `micro-led` | `market-led` | `mixed`)  
- [ ] Complex roll-up present; Daily ≥3 / Weekly five rows (or `n/a`)  
- [ ] Lean note has mechanism (not only up / down); lens touch cite-or-miss / n/a  
- [ ] **Explicit:** Direction ≠ Signal; no Obs levels; no quantity / orders  
- [ ] Daily: TS Oil + one other; COT usually n/a · Weekly: TS try-10 or miss; Disagg MM COT cite-or-miss; grains S-U; ❌ carry invent; CY qualitative or n/a  
- [ ] ❌ COT alone to fill / imply C_* / Est  
- [ ] LOAD ORDER complete; Handoff: insight← / forecast→ / signal / puzzle·trunk complete  
- [ ] No bare BUY / SELL · no `tm_score` · no invent inventory / COT / curves  
- [ ] Dual-leg / proxy≠futures≠LSE; no `XAG-USD`  
- [ ] Sources / Misses / Not investment advice footer; emily ≠ Emily (broker/M7)  
- [ ] Hand off to trunk embed; not standalone Jobs
