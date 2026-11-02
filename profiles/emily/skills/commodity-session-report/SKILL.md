---
name: commodity-session-report
description: >-
  emily trunk: assemble daily lite or weekly depth commodity session MD.
  Dual-venue 10-row price table, Trade map (C_*), weekly history+scenarios all 10,
  Basis after history, required ## Session summary + ## Market insight
  (cite commodity-insight) + commodity_regime. Draft under
  shared/reports/emily/; after Zoe → inbox/commodities-session/*-revised.md.
  Free data only; observation only; emily ≠ Emily broker; never desk Risk-on/off.
---

# Commodity session report — session report (trunk)

**Owner:** emily · commodities · **Train:** draft → Zoe → **emily revise** → `inbox/commodities-session/*-revised.md`  
**Load with:** `commodity-sources-crawl` → `world-to-commodity` → `commodity-insight` → `commodity-direction` → `commodity-forecast` → `commodity-signal-table` → `commodity-puzzle` → **this skill (trunk)**  
**Not:** Alice news ledger · social heat alone for regime · broker Emily / M7 orders · desk-wide Risk-on/off final call  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "Not investment advice · observation only". Source grading: `📊 Data` / `📰 News` / `📊 Institutional`.

---

## When to use

### Daily lite

- After header must have **`## Session summary`**(5–8 bullets + `commodity_regime`)+ **`## Market insight`**(cite `commodity-insight`)
- dual-leg price table ten rows + Trade map Signal  + ≤3 rows full Obs entry/SL/TP
- **Cite:** insight / direction / forecast (ten-column short table or cell miss; ❌ skip entire section) · world 3–5 · puzzle ≥3
- ten-column full history not required (major release exceptions: crop reports, ICE softs, OPEC, etc.)

### Weekly depth

- After header must have **`## Session summary`**
- **Cite forecast** ten-column Scenario ± Est; **cite direction** `DIR_*`; **cite insight**
- ten-column history (1M / 3M / 1Y) — **all ten required**
- Trade map all actionable filled; **Basis align with history / Forecast** (finalize after history written)
- thicker world / puzzle

### Not

- do not write Alice news ledger; do not use social heat to set regime
- do not act as broker Emily / M7 orders
- do not finalize desk Risk-on/off (only write `commodity_regime`; Alice overall may cite)
- ❌ write shared only as deliver (portal requires `inbox/commodities-session/*-revised.md`)
- ❌ in trunk **re-finalize** insight / `DIR_*` / Scenario / Est (must cite upstream skills)

**Required:** **`## Session summary`** + **`## Market insight`** + commodity **Risk-on / Neutral / Risk-off / Crisis** (see "Commodity Risk-on/off") — emily **must write**; Alice desk-wide final sentence may cite / align, but **these sections must not be missing**.

---

## Load order (hard)

```text
commodity-sources-crawl
  → world-to-commodity
  → commodity-insight
  → commodity-direction
  → commodity-forecast
  → commodity-signal-table(Trade map; Basis cite Forecast)
  → commodity-puzzle(suggested Risk-on/off)
  → commodity-session-report(this trunk assembles final)
```

**Weekly extra:** after history written → finalize Trade map **Basis** (cite Forecast / Scenario) → then finalize "Commodity Risk-on/off".

**Trunk slots:** keep News / Lenses / Scenario / Trade map / Insight section positions; body **cites upstream skills** (may embed tables); do not invent a second final version.

---

## Hard rules

- ten columns complete; missing leg → `miss`, do not invent price / inventory / COT / term structure
- Signal only `C_BUY`/`C_WAIT`/`C_HOLD`/`C_REDUCE`/`NO_SETUP`/`miss`
- ❌ bare `BUY` / `WATCH` / `NO_SIGNAL` · ❌ `tm_score` · ❌ quantity / order type / "send to Emily"
- **Basis gate:** no Basis (Dominant tag + **cite Forecast / Scenario / Est**) → **do not fill** Obs entry / cut / TP (Signal only OK); no Forecast / Est cite → no full levels; full-level rows must have Obs TP at cited Est band near-term
- Daily: full Obs entry + SL + TP **at most ≤3** rows (excluding `C_WAIT` / `NO_SETUP` / `miss`); rest Signal (+Invalidation) only
- Weekly: all actionable levels filled; Basis must cite that week history / **Forecast / Commodity scenario**; **Scenario before** full levels
- ❌ anti Method A: do not use ARIMA / LSTM / darts / near-term MA continuation as Scenario (see `commodity-forecast` hard gate)
- primary levels = **US print**; UK / ETC / proxy driven levels tag `proxy-only` + Conf≤L
- **News / Market filter** must pass **before** finalizing Scenario / levels (Daily ≥1 URL≤5; Weekly 2–3 URL≤12; else → `News: miss`)
- **Commodity calendar:** free official windows (EIA / WASDE / Export Sales / COT / softs); unknown → `miss`; ❌ FMP invent dates
- **Lenses:** Macro / Micro / Market + Dominant (`macro-led` | `micro-led` | `market-led` | `mixed`) written into Basis
- **Dual-leg attribution:** do not dump two prices only; Oil try `CL` vs `BZ`
- **Term structure:** Daily = Oil + one other; Weekly = one sentence per ten columns or `miss`
- **`## Session summary` required** (Daily + Weekly; after Header, before price table)
- **`## Market insight` required** (embed / cite `commodity-insight`; Alice cites preferentially)
- **Commodity Risk-on/off required** (pick one of four + one-sentence reason); tag `commodity_regime` (≠ desk Risk-on/off)
- Portal: **draft → Zoe → emily revise → `inbox/commodities-session/*-revised.md`**
- Alice overall: cite **`## Market insight` (preferred)** + Session summary; do not full-paste ten-column history
- Header / footer: Not investment advice · observation only · `emily ≠ Emily (broker/M7)`
- **GFM tables (hard):** each row must have **single** leading `|` (GitHub Flavored Markdown). **Forbidden:** leading `||` (double pipe) — breaks Hermes reports portal preview. Scaffold examples use single `|`; copy unchanged. Zoe: **tables with `||` → REJECT / Major candidate**

---

## Free data / ticker SSOT (ten columns)

**Free only:** **gold-api.com** (Gold / Silver US `XAU` / `XAG`) · Yahoo Finance (non-precious spot)· public calendar / public news URLs · EIA WPSR · USDA WASDE / PSD / Export Sales · CFTC COT · LME / COMEX / LBMA / ICE certified public pages · ICO / USDA softs circular · World Bank Pink Sheet · **FX / rates:** prefer-1 cite same-session `inbox/rates-session/*-revised.md`; if inbox miss and same day / same week may cite `shared/reports/christina/…-rates-session.md`; else whole section `miss`; ❌ T-1 / yesterday shared lock as live cite; ❌ self-write FX Est / Obs / Rate Δbp / `FX_*` / `B_*`  
**Banned:** OilPriceAPI / LSEG / Bloomberg / FactSet / ICE Fundamentals paid APIs · `XAG-USD` (crypto) · Yahoo `XAUUSD=X` / `XAGUSD=X` as primary anchor · invent inventory / COT · paid MCP-first dump

| Commodity | US primary print | UK/EU | Notes |
|-----------|-------------|-------|------|
| Gold | `XAU`(gold-api) | `SGLN.L` | indicative spot vs ETC; `GC=F` footnote only (futures≠spot) |
| Silver | `XAG`(gold-api) | `PHAG.L` | ❌ `XAG-USD` · ❌ Yahoo `XAGUSD=X`;`SI=F`  footnote(futures≠spot) |
| Copper | `HG=F` | `COPA.L` | futures≠spot; tag `futures≠spot` |
| Soy | `ZS=F` | `SOYB`* | CBOT vs proxy |
| Wheat | `ZW=F` | `WEAT`* | … |
| Corn | `ZC=F` | `CORN`* | … |
| Oil | `CL=F` | `BZ=F` | WTI vs Brent; tag futures |
| Cocoa | `CC=F` | `NIB`* | ICE US cocoa |
| Sugar | `SB=F` | `CANE`* | Sugar #11 |
| Coffee | `KC=F` | `JO`* | ❌ do not treat KC as equity; JO name-check |

\*Ag / softs UK leg: US-listed ETF proxy + mandatory `proxy≠futures≠LSE`; missing → `miss`. Orange juice / cotton etc. OOU.

LSE 0 / NaN → `miss`; GBp quotes must be disclosed.

---

## Output paths (P3 portal)

| Cadence | Draft (shared) | Portal revised |
|---------|-----------------|----------------|
| Daily | `shared/reports/emily/YYYY-MM-DD-commodity-session.md` | `inbox/commodities-session/YYYY-MM-DD-commodities-session-revised.md` |
| Weekly | `shared/reports/emily/YYYY-Www-commodities-session.md` | `inbox/commodities-session/YYYY-Www-*-revised.md` |

**Train:** draft → Zoe → **emily revise** → `inbox/commodities-session/*-revised.md` (3-layer).If the revise landed only on the draft filename, run `python3 ~/.hermes/scripts/desk_pack_revised_gate.py`(promotes only when the Zoe challenge file is older than the draft; does not rename an unreviewed draft).  
**Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`.

---

## Required sections / tables

1. Header (Not investment advice · emily≠Emily · as-of)  
2. **`## Session summary`**(;5–8 bullets + `commodity_regime` + Alice pull → Market insight)
3. Dual price table (ten rows; **US↔UK attribution**)  
4. World→commodity(cite)  
5. **`## Market insight`** (required; cite / embed `commodity-insight` — SSOT title; do not use separate `## Commodity insight`)  
6. **News / Market check** (before finalizing Scenario / levels)  
7. **Direction**(cite `commodity-direction` · `DIR_*`)  
8. **Forecast / Scenario** (cite `commodity-forecast`; Daily ten-column short table or cell miss; ❌ skip entire section)  
9. Puzzle(≥3 blocks)  
10. **Lenses + Dominant**  
11. Commodity calendar (near-term public windows)  
12. Cite-or-miss lenses(inventory/term/COT)  
13. History (**weekly mandatory ten columns** 1M / 3M / 1Y; Scenario **cite forecast**, do not rewrite)  
14. Trade map(cite `commodity-signal-table`;**Basis cite Forecast**)  
15. **Commodity Risk-on/off** (required; `commodity_regime`)  
16. FX / rates receive (christina; or miss)  
17. Sources + **Miss ledger** + Footer  

**Note:** Canonical Dual price / Miss ledger / Sources / cite-or-miss lenses = **trunk only** (upstream skills pointer / cite only). MD section order may vary; **EXECUTION** follows 8-skill load; Trade map Basis finalized after history.

### Session summary (required)

Daily and weekly both required (after Header):

```markdown
## Session summary
- … (5–8 bullets; owner voice; not table dump)
- **commodity_regime:** Risk-on / Neutral / Risk-off / Crisis +
- **Alice pull:** Market insight — 1–2 sentence pointer (do not paste full text)
```

Zoe **REJECT** if missing. `commodity_regime` ≠ desk Risk-on/off.

### Market insight (required)

Embed / cite `commodity-insight` skill output. Title **SSOT = `## Market insight`** (do not open `## Commodity insight`).

```markdown
## Market insight
(cite commodity-insight)
- Drivers/complex/dual-leg/tensions/missing …
- ❌ do not write desk Risk-on/off final call; ❌ do not claim desk-wide Macro view (→ Alice · Zoe Z-MI-02)
```

Zoe: **missing this section → REJECT (Z-MI-01)**.

### History columns (plain language)

Weekly must write history compare (1M / 3M / 1Y) for **each of ten commodities**. Scenario / Est **cite `commodity-forecast`**, **do not** rewrite bull | base | bear in History.  
Skipping any history column = missing any commodity (e.g. missing Coffee) → **whole weekly FAIL**.  
If no data, write `miss` in that cell; section / row must still exist.

### Commodity Risk-on/off (required)

Daily and weekly both required:

```markdown
## Commodity Risk-on/off
- **Call:** Risk-on / Neutral / Risk-off / Crisis (pick one)
- **Reason:** one sentence (align puzzle / dual-leg / transmission)
- **Scope:** represents **commodity complex** observation only (`commodity_regime`); Alice desk-wide final may cite this section
```

---

## Blank report template — Daily scaffold (copy-paste)

Copy the block below to `shared/reports/emily/YYYY-MM-DD-commodity-session.md` then fill; after Zoe emily revise → `inbox/commodities-session/YYYY-MM-DD-*-revised.md`.

```markdown
# emily · commodities — Daily commodity session
**As-of:** YYYY-MM-DD · TZ: …
**Cadence:** daily lite
**Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7)

---

## Session summary
- …
- …
- …
- …
- …
- **commodity_regime:** Risk-on / Neutral / Risk-off / Crisis — …
- **Alice pull:** Market insight — …

---

## Dual-venue price table (ten rows)

| Commodity | US print | UK/EU print | US↔UK note |
|-----------|----------|-------------|------------|
| Gold | XAU · gold-api · {px} · {chg} | SGLN.L · {px} · {chg} | |
| Silver | XAG · gold-api · {px} · {chg} | PHAG.L · {px} · {chg} | |
| Copper | HG=F · {px} · {chg} | COPA.L · {px} · {chg} | |
| Soy | ZS=F · {px} · {chg} | SOYB* · {px} · {chg} | |
| Wheat | ZW=F · {px} · {chg} | WEAT* · {px} · {chg} | |
| Corn | ZC=F · {px} · {chg} | CORN* · {px} · {chg} | |
| Oil | CL=F · {px} · {chg} | BZ=F · {px} · {chg} | |
| Cocoa | CC=F · {px} · {chg} | NIB* · {px} · {chg} | |
| Sugar | SB=F · {px} · {chg} | CANE* · {px} · {chg} | |
| Coffee | KC=F · {px} · {chg} | JO* · {px} · {chg} | |

\*proxy≠futures≠LSE; missing leg fill `miss`. US↔UK note must attribute (liquidity / spec / proxy error / FX cite), not price only.

---

## World → commodity(3–5 events)

| # | Event | Date | Channel(s) | Mechanism (one sentence) | Grade |
|---|-------|------|------------|-----------------|-------|
| 1 | | | supply/demand/… | | 📰 News / 📊 Data |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

(Each event also has ten-column dual-leg impact: see `world-to-commodity`; may embed or cite appendix in same file.)

---

## Market insight (cite commodity-insight)

> Embed / cite upstream; **do not** re-finalize Drivers / complex in trunk. Canonical Dual price / Miss / Sources / lenses = trunk only (this section pointer).

- Drivers / Complex / Dual-leg / Tensions / Missing: see `commodity-insight` draft or embed table
- or missing: mark `miss` + reason

---

## News / Market check (Emily-topic · before finalizing Scenario / levels)

| # | Claim (one sentence) | Outlet · URL · as-of | Grade |
|---|--------------|----------------------|-------|
| 1 | | | 📰 News |
| … | or whole section `News: miss` | | |

❌ social heat alone for regime · ❌ paid terminal as primary source

---

## Commodity direction (cite commodity-direction · DIR_*)

> Cite upstream `DIR_*` table; **do not** write `C_*`; Direction ≠ Signal.

- ten-column Direction / Conf / Dominant / Invalidation: cite or embed
- Complex roll-up: cite or embed

---

## Commodity forecast (cite commodity-forecast · ten-column short table — before full Trade map levels)

| Commodity | Horizon | Bull | Base | Bear | Est band | Invalidation |
|-----------|---------|------|------|------|----------|--------------|
| Gold | 1–4w | | | | | |
| Silver | 1–4w | | | | | |
| Copper | 1–4w | | | | | |
| Soy | 1–4w | | | | | |
| Wheat | 1–4w | | | | | |
| Corn | 1–4w | | | | | |
| Oil | 1–4w | | | | | |
| Cocoa | 1–4w | | | | | |
| Sugar | 1–4w | | | | | |
| Coffee | 1–4w | | | | | |

(Ten columns complete; missing data → cell `miss`, row stays. ❌ skip entire section. **Do not** second-finalize in trunk.)

---

## Commodity puzzle(≥3 blocks)

| Block | Supports | Tensions | Missing |
|-------|----------|----------|---------|
| precious / industrial / … | | | |
| grains / energy / … | | | |
| softs / … | | | |

Cross-block tensions: …
Suggested commodity Risk-on/off (puzzle): … (trunk section below finalizes)

---

## Lenses + Dominant

- Macro: …
- Micro: …
- Market: …
- **Dominant:** macro-led / micro-led / market-led / mixed

---

## Commodity calendar (near-term)

| Date | Event | Relevant | Grade |
|------|-------|----------|-------|
| | EIA WPSR / WASDE / Export Sales / COT / softs official / … | Oil / grains / … | 📊 Data |

**Calendar slot (hard):** only **free official windows** — EIA WPSR · USDA WASDE · Export Sales · CFTC COT · softs official monthly / circular (ICO / USDA etc.). Unknown / not auditable date → row **`miss`**. ❌ **FMP / paid calendar invent dates**; ❌ use calendar to invent report numbers. Near window → Conf↓ or lean `C_WAIT`.

---

## Cite-or-miss lenses (daily)

| Lens | Note |
|------|------|
| Inventory | cite official touchpoint when present; else `n/a` |
| Term structure | **Oil + one other** Contango / Back; rest `n/a` |
| COT | usually `n/a` (weekly only) |
| CL vs BZ | one-sentence spread attribution or `miss` |

---

## Trade map (C_* · daily ≤3 full levels · Basis gate)

| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis (+ Dominant) | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|---------------------|------|
| Gold | C_WAIT / … | | cite forecast or miss | | | | 1–4w | | cite Forecast / Scenario / Est · lean: base · Dominant: … | H/M/L |
| Silver | | | | | | | | | | |
| Copper | | | | | | | | | | |
| Soy | | | | | | | | | | |
| Wheat | | | | | | | | | | |
| Corn | | | | | | | | | | |
| Oil | | | | | | | | | | |
| Cocoa | | | | | | | | | | |
| Sugar | | | | | | | | | | |
| Coffee | | | | | | | | | | |

**Daily trim:** full Obs entry+SL+TP rows = (≤3): _______ · _______ · _______  
Remaining rows: Signal (+Invalidation) only; **no Basis (incl. Forecast cite) → do not fill levels**. No Forecast / Est cite → no full Obs levels. Full-level rows must have Obs entry / cut / TP; Obs TP at cited Est band near-term.

---

## Commodity Risk-on/off

- **Call:** Risk-on / Neutral / Risk-off / Crisis (pick one)
- **Reason:** …
- **Scope:** `commodity_regime` — commodity complex observation; Alice desk-wide may cite

---

## FX / rates receive (christina · locked)
- Path: prefer-1 same-session `inbox/rates-session/*-revised.md`; inbox miss and same day / week → `shared/reports/christina/YYYY-MM-DD-rates-session.md` (or Www); else `miss` (❌ T-1 / yesterday shared lock)
- Allowed: one sentence GBPUSD / DXY / DFII **pointer + as-of** (from that session) explaining US/UK leg divergence / Conf adjustment
- ❌ this section self-writes FX Est / Obs TP / Rate Δbp / `FX_*` / `B_*`

---

## Sources

- 📊 Data: …
- 📰 News: … (or `News: miss`)
- 📊 Institutional: …
- Misses: see Miss ledger

### Miss ledger
| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| | | | | |

---

## Footer

Not investment advice · observation only · emily ≠ Emily (broker/M7) · portal `inbox/commodities-session/*-revised.md` · `commodity_regime` ≠ desk Risk-on/off
```

---

## Blank report template — Weekly scaffold (copy-paste)

Copy the block below to `shared/reports/emily/YYYY-Www-commodities-session.md` then fill; after Zoe emily revise → `inbox/commodities-session/YYYY-Www-*-revised.md`.  
**ISO week:** `Www` = week number (e.g. `2026-W38-commodities-session.md`).

```markdown
# emily · commodities — Weekly commodities session
**Week:** YYYY-Www · **As-of:** YYYY-MM-DD · TZ: …
**Cadence:** weekly depth
**Disclaimer:** Not investment advice · observation only · emily ≠ Emily (broker/M7)

---

## Session summary
- …
- …
- …
- …
- …
- **commodity_regime:** Risk-on / Neutral / Risk-off / Crisis — …
- **Alice pull:** Market insight — …

---

## Dual-venue price table (ten rows)

| Commodity | US print | UK/EU print | US↔UK note |
|-----------|----------|-------------|------------|
| Gold | XAU · gold-api · {px} · {chg} | SGLN.L · {px} · {chg} | |
| Silver | XAG · gold-api · {px} · {chg} | PHAG.L · {px} · {chg} | |
| Copper | HG=F · {px} · {chg} | COPA.L · {px} · {chg} | |
| Soy | ZS=F · {px} · {chg} | SOYB* · {px} · {chg} | |
| Wheat | ZW=F · {px} · {chg} | WEAT* · {px} · {chg} | |
| Corn | ZC=F · {px} · {chg} | CORN* · {px} · {chg} | |
| Oil | CL=F · {px} · {chg} | BZ=F · {px} · {chg} | |
| Cocoa | CC=F · {px} · {chg} | NIB* · {px} · {chg} | |
| Sugar | SB=F · {px} · {chg} | CANE* · {px} · {chg} | |
| Coffee | KC=F · {px} · {chg} | JO* · {px} · {chg} | |

\*proxy≠futures≠LSE; missing leg fill `miss`. US↔UK note must attribute; Oil write CL–BZ or `miss`.

---

## World → commodity(fuller)

| # | Event | Date | Channel(s) | Mechanism (one sentence) | Grade |
|---|-------|------|------------|-----------------|-------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| … | | | | | |

(ag + oil + softs must be representative or explicit `miss`.)

---

## Market insight (cite commodity-insight)

> Embed / cite upstream; **do not** re-finalize in trunk. Canonical Dual price / Miss / Sources / lenses = trunk only.

- Drivers / Complex / Dual-leg / Tensions / Missing: cite `commodity-insight` or embed

---

## News / Market check (Emily-topic · 2–3 sentences · URL≤12)

| # | Claim (one sentence) | Outlet · URL · as-of | Grade |
|---|--------------|----------------------|-------|
| 1 | | | 📰 News |
| 2 | | | |
| 3 | | | |

or `News: miss`.

---

## Commodity direction (cite commodity-direction · DIR_*)

> Cite upstream `DIR_*`; **do not** write `C_*`; Direction ≠ Signal.

- ten-column Direction + five complex rows: cite or embed

---

## Commodity forecast (cite commodity-forecast · ten columns mandatory — before full Trade map levels)

> **Cite** `commodity-forecast` table; **do not** second-finalize Scenario / Est in trunk.

| Commodity | Horizon | Bull | Base | Bear | Est band | Invalidation |
|-----------|---------|------|------|------|----------|--------------|
| Gold | 4–12w | | | | | |
| Silver | | | | | | |
| Copper | | | | | | |
| Soy | | | | | | |
| Wheat | | | | | | |
| Corn | | | | | | |
| Oil | | | | | | |
| Cocoa | | | | | | |
| Sugar | | | | | | |
| Coffee | | | | | | |

Missing data → cell `miss`, row stays. Or whole table: `cite commodity-forecast draft path`.

---

## Commodity puzzle(richer · ≥3 blocks)

| Block | Supports | Tensions | Missing |
|-------|----------|----------|---------|
| | | | |
| | | | |
| | | | |

Cross-block tensions: …
Suggested commodity Risk-on/off (puzzle): …

---

## Lenses + Dominant

- Macro: …
- Micro: …
- Market: …
- **Dominant:** macro-led / micro-led / market-led / mixed

---

## Commodity calendar

| Date | Event | Relevant | Grade |
|------|-------|----------|-------|
| | EIA WPSR / WASDE / Export Sales / COT / softs official | | 📊 Data |

free official windows only; unknown → `miss`; ❌ FMP invent dates; ❌ invent report numbers.

---

## Cite-or-miss lenses (weekly)

| Commodity | Inventory cite-or-miss | Term structure | COT (Disagg) | Notes |
|-----------|------------------------|----------------|---------------|-------|
| Gold | | Contango/Back/`miss` | | LBMA/COMEX |
| Silver | | | | |
| Copper | | | | LME/COMEX |
| Soy | | | | WASDE S-U |
| Wheat | | | | WASDE S-U |
| Corn | | | | WASDE S-U |
| Oil | EIA WPSR/`miss` | | | CL–BZ |
| Cocoa | | | | ICE/USDA |
| Sugar | | | | USDA circular |
| Coffee | | | | ICO/USDA |

Grains: WASDE / PSD auditable → **stocks-to-use** direction sentence required.

---

## History (ten columns mandatory 1M / 3M / 1Y — missing one commodity = FAIL)

> Scenario / Est: **cite Forecast table** — **do not** rewrite bull | base | bear in History.

### Gold
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | 📊 Data | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Gold) — do not rewrite.

### Silver
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Silver) — do not rewrite.

### Copper
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Copper) — do not rewrite.

### Soy
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Soy) — do not rewrite.

### Wheat
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Wheat) — do not rewrite.

### Corn
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Corn) — do not rewrite.

### Oil
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Oil) — do not rewrite.

### Cocoa
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Cocoa) — do not rewrite.

### Sugar
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Sugar) — do not rewrite.

### Coffee
| Horizon | Move / level | Source | Note |
|---------|--------------|--------|------|
| 1M | | | |
| 3M | | | |
| 1Y | | | |
| 5Y (opt) | | | |

**Scenario:** cite Forecast table (Coffee) — do not rewrite.

---

## Trade map (C_* · weekly full levels; Basis aligned with history / Forecast · Basis gate)

| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis (+ Dominant) | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|---------------------|------|
| Gold | | | cite forecast | | | | 4–12w | | cite Forecast / Scenario · history · lean: base · Dominant: … | H/M/L |
| Silver | | | | | | | | | | |
| Copper | | | | | | | | | | |
| Soy | | | | | | | | | | |
| Wheat | | | | | | | | | | |
| Corn | | | | | | | | | | |
| Oil | | | | | | | | | | |
| Cocoa | | | | | | | | | | |
| Sugar | | | | | | | | | | |
| Coffee | | | | | | | | | | |

primary levels = US print; proxy-only → Conf≤L + tag `proxy-only`. **No Basis (incl. Forecast cite) → do not fill levels.** finalize Basis after history. Basis must include lean: base|bull|bear|two-way. Obs TP at cited Est band near-term; Est value paste band verbatim or `miss`.

---

## Commodity Risk-on/off

- **Call:** Risk-on / Neutral / Risk-off / Crisis (pick one)
- **Reason:** …
- **Scope:** `commodity_regime` — commodity complex observation; Alice desk-wide may cite

---

## FX / rates receive (christina · locked)
- Path: prefer-1 same-session `inbox/rates-session/*-revised.md`;inbox miss / → `shared/reports/christina/…-rates-session.md`;else `miss`(❌ T-1/yesterday shared lock)
- Allowed: one paragraph GBPUSD / DXY / DFII **pointer + as-of** explaining US/UK leg divergence / Conf adjustment
- ❌ this section self-writes FX Est / Obs TP / Rate Δbp / `FX_*` / `B_*`

---

## Sources

- 📊 Data: …
- 📰 News: … (or `News: miss`)
- 📊 Institutional: …
- Misses: see Miss ledger

### Miss ledger
| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| | | | | |

---

## Footer

Not investment advice · observation only · emily ≠ Emily (broker/M7) · portal `inbox/commodities-session/*-revised.md` · `commodity_regime` ≠ desk Risk-on/off
```

---

## Embed contract (Alice overall)

- Alice overall: **cite** `## Market insight` (preferred) + `## Session summary` + `commodity_regime` from `inbox/commodities-session/*-revised.md`  
- Jobs overall may also excerpt: compact price table + short trade map  
- Full history + full SL/TP **stay in** emily session MD  
- emily session **is** portal light (`commodities-session/`); not Alice-only embed  
- ❌ do not write desk Risk-on/off final call (Alice Macro view only)

---

## Banned

- OilPriceAPI / LSEG / Bloomberg · bare BUY · `tm_score`  
- broker order language / quantity / order type / "send to Emily"  
- **weekly missing history for any of ten commodities** (use `miss` but section must exist)  
- invent inventory / invent levels · social heat alone for commodity regime  
- missing `## Session summary` or `## Market insight` · shared-only deliver · treat `commodity_regime` as desk Risk-on/off
- full-paste ten-column history into Alice overall (budget blowout)
- Markdown table leading `||` (double pipe; must be single `|`; portal preview breaks)
- `DIR_*` 1D% may only come from GLD / `GC=F` (silver SLV / `SI=F`) previous close, cited in that row; gold-api spot is level only. Missing prev close → `miss`. `BZ=F` row must say ICE Brent financial futures, same source CL–BZ, same pull, same as-of. Missing → `miss`.

---

## Checklist

- [ ] Load order: sources → world → insight → direction → forecast → signal → puzzle → trunk  
- [ ] Header / footer: Not investment advice · emily ≠ Emily (broker/M7)  
- [ ] **`## Session summary`** (after Header; 5–8 bullets + `commodity_regime`; Alice pull → Market insight)
- [ ] **`## Market insight`** (cite commodity-insight; no desk Risk-on/off final call)
- [ ] Dual price ten rows; proxy / futures / miss disclosed  
- [ ] Tables: single `|` per row (GFM); ❌ leading `||` (Zoe REJECT / Major)  
- [ ] **Insight / Direction / Forecast** sections non-empty (Daily Forecast ten-column short or cell miss; ❌ skip entire section); cite upstream, no second finalize  
- [ ] Trade map ten rows `C_*` (no `DIR_*`); Last / Est / Horizon; daily ≤3 full Obs levels; weekly Basis↔history / **cite Forecast**  
- [ ] Puzzle ≥3; world daily 3–5 (or explained)  
- [ ] **Commodity calendar:** official windows cite-or-miss; ❌ FMP invent dates  
- [ ] **Commodity Risk-on/off** pick one of four + reason (`commodity_regime`; ≠ desk)  
- [ ] Weekly: history×10 (1M / 3M / 1Y); Scenario cite Forecast (no rewrite); if missing that section `miss`, do not drop whole commodity  
- [ ] FX / rates cite (christina path or `miss`); ❌ self-write FX Est / Obs / Rate Δbp  
- [ ] Train: draft → Zoe → emily revise → `inbox/commodities-session/*-revised.md`  
- [ ] Sources + Misses complete  
- [ ] Output paths correct: draft `…-commodity-session.md` / `…-commodities-session.md`; revised inbox  
