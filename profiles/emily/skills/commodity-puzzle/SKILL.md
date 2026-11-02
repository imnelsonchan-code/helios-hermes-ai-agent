---
name: commodity-puzzle
description: >-
  emily commodity-side puzzle: ≥3 blocks (precious/energy/industrial/grains/
  softs) with supports, tensions, missing. Suggests commodity Risk-on/off for
  trunk to finalize; Alice may cite. Does not rewrite C_* signals.
---

# Commodity puzzle

**Owner:** emily · commodities · **Train:** session draft → trunk embed → Alice cite  
**Load after:** `commodity-sources-crawl` → `world-to-commodity` → `commodity-insight` → `commodity-direction` → `commodity-forecast` → `commodity-signal-table` (may absorb insight/direction/forecast)  
**Load before:** `commodity-session-report` (trunk finalizes "Commodity Risk-on/off")  
**Not:** desk-wide final Risk-on/off (Alice) · rewrite `C_*` Trade map · broker Emily / M7  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "**Not investment advice · observation only**". Source grading: `📊 Data` / `📰 News`.

---

## When to use

### Daily lite
- Run **after signal** (and upstream insight/direction/forecast) — ❌ do not skip the three new layers right after world  
- **≥3** short blocks; supports/tensions/missing complete  
- **Cite first** insight/direction/forecast; do not invent a parallel conflict mechanism  
- End with **suggested** Commodity Risk-on/off (pick one of four + one sentence) for trunk

### Weekly depth
- Same structure, thicker: cross-complex tension, dual-leg/proxy divergence, fuller missing-data list  
- Still ≥3 blocks; do not pad with empty micro-blocks

### Not
- Does not replace dual price / Trade map / history / Forecast final call  
- Do not use puzzle to build `tm_score`/`valuation_score`/blended equity score  
- Do not place orders or write bare `BUY`/`DIR_*` in puzzle

---

## Hard rules

1. **Blocks ≥3**, labels only:  
   `precious` · `energy` · `industrial` · `grains` · `softs`  
   (optional more than 3; no duplicate empty shells)  
2. **Each block triad:** supports · tensions · missing (state missing data / missing transmission)  
3. **Puzzle end must suggest** Commodity Risk-on/Neutral/Risk-off/Crisis (pick one of four) + **one-sentence reason** → **trunk** writes formal "Commodity Risk-on/off" section (tag `commodity_regime`)  
4. Alice desk-wide final Risk-on/off **may cite** emily commodities verdict; puzzle itself **must not** pose as desk-wide regime  
5. **Do not rewrite** `C_*` Signal/Obs levels (Trade map belongs to signal-table/trunk)  
6. When citing dual-leg prices and transmission: proxy≠futures≠LSE; silver uses gold-api `XAG`; ❌ `XAG-USD`  
7. Load order: sources → world → insight → direction → forecast → signal → **puzzle** → trunk  
8. **May absorb upstream:** insight Drivers/Complex/Tensions · direction `DIR_*` lean · forecast Scenario; supports/tensions **cite first**, banned to invent conflict final call  
9. **Banned paid:** OilPriceAPI · LSEG · Bloomberg · FactSet · ICE Fundamentals paid APIs

---

## Free data only / ticker SSOT

**Allowed:** upstream sources/world/insight/direction/forecast/signal (precious metals Last = gold-api) · Yahoo · **FX/rates:** prefer cite `shared/reports/christina/…-rates-session.md` (or `miss`) as DFII/GBPUSD/DXY pointer; ❌ invent `FX_*`/`B_*`/Rate Δbp  

**Banned:** OilPriceAPI · LSEG · Bloomberg · FactSet · ICE Fundamentals paid APIs · invent inventory · social heat alone for puzzle story

### Ten-column (universe puzzle must cover)

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

\*proxy≠futures≠LSE. Orange juice/cotton etc. OOU.

**Block ↔ column reference:**

| Block | Typical columns |
|-------|-----------------|
| `precious` | Gold · Silver |
| `energy` | Oil (CL/BZ) |
| `industrial` | Copper |
| `grains` | Soy · Wheat · Corn |
| `softs` | Cocoa · Sugar · Coffee |

---

## Output paths

Embed in session MD:

- Daily: `shared/reports/emily/YYYY-MM-DD-commodity-session.md` ("Commodity puzzle" section)  
- Weekly: `shared/reports/emily/YYYY-Www-commodities-session.md`  

❌ do not write inbox/Jobs main file.

---

## Required sections / tables

### Header stub

- as-of · block count/labels  
- Hard line: puzzle = commodity-side observation; **suggest** regime to trunk; Alice desk may cite; not investment advice

### 1. Puzzle overview

| Block | One-line story | Supports | Tensions | Missing |
|-------|----------------|----------|----------|---------|
| precious | … | … | … | … |
| energy | … | … | … | … |
| … | … | … | … | … |

At least **3** valid block rows.

### 2. Per-block detail (short)

Per block 2–6 bullets:

- **Supports:** which prices/transmission/FRED cites support this story  
- **Tensions:** conflict with other blocks or dual-leg (US vs UK/EU)  
- **Missing:** missing leg, `miss` source, unverified inventory (do not invent fill)

### 3. Cross-block tension

- 3–6 bullets: metals × energy × grains × softs (as written)  
- How trunk should write "Commodity Risk-on/off"

### 4. Suggested Commodity Risk-on/off (mandatory → trunk)

```markdown
### Suggested Commodity Risk-on/off (trunk finalizes)
- **Suggested verdict:** Risk-on / Neutral / Risk-off / Crisis (pick one of four)
- **Reason:** one sentence (aligned with blocks/transmission/dual-leg)
- **Scope:** represents **commodity complex only**; Alice desk final sentence may cite; this section is not Jobs final regime
```

Trunk session **must** have formal "Commodity Risk-on/off" section; puzzle must not leave suggestion empty.

### 5. Sources

```markdown
## Sources (commodity-puzzle)
- 📊 Data: Yahoo dual prints · as-of · path or session cite
- 📰 News / transmission: cite world-to-commodity event # · URL
- 📊 Data: christina rates session cite (DFII/FX pointer) · or miss
- Misses: …
```

---

## Banned

- <3 blocks · empty-shell padding  
- headlines-only (no supports/tensions/missing)  
- puzzle end **without** suggested Commodity Risk-on/off  
- pose as Alice desk regime · rewrite `C_*`/Obs levels  
- broker order language · bare `BUY` · `tm_score`/`valuation_score` blend  
- `XAG-USD` · treat proxy as LSE futures · invent inventory

---

## Checklist

- [ ] Load order: sources → world → insight → direction → forecast → signal → **puzzle** → trunk  
- [ ] Blocks ≥3; labels only precious/energy/industrial/grains/softs  
- [ ] Each block supports + tensions + missing complete  
- [ ] Cross-block tension written  
- [ ] **Has suggestion** Commodity Risk-on/Neutral/Risk-off/Crisis + one-sentence reason (to trunk)  
- [ ] No rewrite of `C_*`; no posing as desk-wide regime  
- [ ] Dual-leg/proxy≠futures≠LSE explained; no `XAG-USD`  
- [ ] Sources/Misses complete; not investment advice  
- [ ] Embed in session; no standalone Jobs
