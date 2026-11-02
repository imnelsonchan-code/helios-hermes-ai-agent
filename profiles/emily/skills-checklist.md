# emily — Skills checklist (commodities)
> Scrubbed · Display **"emily · commodities"** · `emily` ≠ Emily (broker/M7) · Inventory **2026-09-22** (insight/direction/forecast + ADAPT patches)

| Field | Value |
|-------|-------|
| **Profile** | `emily` |
| **Git source of truth** | `SOUL.md` + this checklist + `profiles/emily/skills/*/SKILL.md` |
| **Inventory date** | 2026-09-22 (Keep **8** + Eval/Sat `commodity-obs-backtest` + Receive/optional `christina-macro-bridge`) |

---

## 1. How to use

- **Keep** = emily session mandatory load (8-skill load)  
- **Eval/Sat** = Saturday/adhoc hygiene; **not** in daily/weekly load  
- **Receive/optional** = trunk Rates/FX receive helper; **not in** Keep 8 load (same optional pattern as Eval)  
- **Exclude** = equity sleeve/broker/cron ops/desk Risk-on/off/paid APIs/SimpleFX/IB/Alpaca/RL  
- **Peer cite** = christina rates session (shared draft or `inbox/rates-session/`; missing → `miss`; do not self-write FX/rate depth)  
- **Embed trunk** = calendar + inventory/term/COT cite-or-miss; News/Lenses/Scenario/Trade map **slots cite upstream skills**

---

## 2. Profile skills (Keep · 8)

| Skill (folder) | Purpose | Status |
|----------------|---------|--------|
| `commodity-sources-crawl` | Ten-column dual-leg; precious US = **gold-api**; miss ledger; **post-crawl QA**; proxy/LSE | **Keep** |
| `world-to-commodity` | Events → channels → ten-column; **shock skeleton**; official calendar windows | **Keep** |
| `commodity-insight` | **Insight**: Drivers/complex/dual-leg; term/COT/CY cite-or-miss; no `C_*`/`DIR_*`/Obs | **Keep** |
| `position-plan-commodity` | If assigned, write commodity comment and analysis in that day's `## Position comments` even when daily and weekly sessions have no row. Not in Keep-8 daily load. | **Keep** |
| `commodity-direction` | **Direction**: `DIR_*` lean; term/COT crowdedness; ≠ Signal | **Keep** |
| `commodity-forecast` | **Forecast**: Scenario ± Est (Method A; **anti ARIMA/LSTM/darts/MA**) | **Keep** |
| `commodity-signal-table` | Trade map (`C_*`); Obs; shadow + **named breakdown**; Basis cite Forecast | **Keep** |
| `commodity-puzzle` | ≥3 blocks; suggest Commodity Risk-on/off | **Keep** |
| `commodity-session-report` | **Trunk**: assemble; calendar/cite-or-miss; Session summary; regime; portal | **Keep** |

Load order:
```text
sources → world → insight → direction → forecast → signal → puzzle → trunk
```

---

## 2b. Eval/Sat

| Skill (folder) | Purpose | Status |
|----------------|---------|--------|
| `commodity-obs-backtest` | Sat/adhoc observation-only: prior `C_*`/`DIR_*`/regime vs next-day Yahoo Last; lean hit/miss · regime stability · dual-leg attribution rate · Basis-gate pass; ❌ PnL/orders/SimpleFX/IB/Alpaca/RL/ARIMA | **Eval/Sat** |

Output: `shared/reports/emily/self-review/YYYY-Www-emily-obs-backtest.md`  
❌ insert into 8-skill load above.

---

## 2c. Receive/optional (not in Keep 8)

| Skill (folder) | Purpose | Status |
|----------------|---------|--------|
| `christina-macro-bridge` | Read-only christina rates/FX; SOUL §8 receive three locks hard-coded; trunk Rates/FX receive handoff stub; ❌ invent `FX_*`/`B_*`/Rate Δbp/DXY Est; ❌ rewrite dual-leg `C_*` | **Receive/optional** |

Cite: `shared/reports/christina/*-rates-session.md` or `inbox/rates-session/*-revised.md` or `miss`.  
❌ insert into 8-skill load (**not in** Keep).

---

## 3. Cadence map

| Cadence | Must |
|---------|------|
| **Daily** | Dual-10 · Insight (Drivers≥3/complex≥3/Oil+1 dual-leg) · Direction ten-column `DIR_*` · Forecast **ten-column short table** (cell miss; ❌ skip entire section) · Signal-10 · ≤3 Obs (full-level rows must have Obs TP at Est near band; Basis lean: base\|bull\|bear\|two-way; **no Basis → do not fill**) · puzzle ≥3 · **`## Session summary`** · **Commodity Risk-on/off** · portal revised |
| **Weekly** | Same + Forecast ten-column Scenario±Est · Direction complex five rows · thicker Insight · history×10 · full Trade map · Basis↔history/Forecast · Obs TP at Est near band · Basis lean: base\|bull\|bear\|two-way · **`## Session summary`** · **Commodity Risk-on/off** |
| **Sat/Eval** | May run `commodity-obs-backtest` (cite-only hygiene); do not rewrite full session |
| **Adhoc** | May use trunk scaffold; still obey ten-column/firewall/three-layer insight→direction→forecast/Session summary |

---

## 4. Later backlog (consume-or-miss · not in Keep load)

| Future skill | Purpose | Status |
|--------------|---------|--------|
| `eia-wpsr` | EIA WPSR → Oil (official https://www.eia.gov/petroleum/supply/weekly/; cite-or-miss) | **Stub/Later** (folder exists; not in Keep-8) |
| `usda-wasde-psd` | WASDE/PSD/Export Sales | **Stub/Later** (folder exists) |
| `cftc-cot-disagg` | weekly Disagg COT | **Stub/Later** (folder exists) |
| `exchange-inventory-snapshot` | LME/COMEX/LBMA/ICE certified | **Later** (not stubbed) |
| `term-structure-basis` | Contango/Back | **Later** (not stubbed) |
| `ag-weather-enso` | crop window/ENSO | **Later** (not stubbed) |

P1 stubs: `profiles/emily/skills/{eia-wpsr,usda-wasde-psd,cftc-cot-disagg}/SKILL.md` — cite-or-miss · miss > invent · no paid APIs · handoff insight/direction/forecast · ❌ invent cron IDs · Status=Later until host artifact exists.

---

## 5. Exclude

| Item | Why |
|------|-----|
| Renee `tm_score`/bare `BUY` | Equity T&M |
| Eliza `valuation_score` | P-VAL |
| Broker Emily/M7 orders | Out of scope |
| **SimpleFX/IB/Alpaca/RL** | Execution/agents — EXCLUDE |
| OilPriceAPI/LSEG/Bloomberg/FactSet/ICE Fundamentals paid APIs | Paid blacklist |
| ARIMA/LSTM/darts as Scenario/backtest engine | Anti Method A |
| OJ/cotton etc. unlisted softs | OOU |
| Desk-wide Risk-on/off final call | Alice overall |
| Invent inventory/COT/term-structure/WASDE numbers | miss > invent |
| `DIR_*` written into Signal column · `C_*` written into Direction column | Namespace isolation |
| FMP invent official window dates · carry/CY formula invent | cite-or-miss only |

### External-skill ADAPT (short)

Pricing Engine/term/COT/shock/calendar **concept ADAPT** → emily cite-or-miss. **SimpleFX/IB/Alpaca/RL EXCLUDE.** ARIMA-class EXCLUDE as Scenario.

---

## 6. Deliverable paths (P3)

- Draft daily: `shared/reports/emily/YYYY-MM-DD-commodity-session.md`  
- Draft weekly: `shared/reports/emily/YYYY-Www-commodities-session.md`  
- **Portal revised:** `inbox/commodities-session/*-revised.md`  
- **Train:** draft → Zoe → **emily revise** → inbox (3-layer)  
- Alice overall: cite Session summary; do not paste full text  
- **Obs-backtest (Sat):** `shared/reports/emily/self-review/YYYY-Www-emily-obs-backtest.md`

---

## 7. Acceptance smoke

### Three new skills (insight/direction/forecast)
- [ ] **insight:** Drivers + complex≥3 + dual-leg Oil+1 + Tensions + Missing; no `C_*`/`DIR_*`/Obs  
- [ ] **direction:** ten-column uses only `DIR_BULLISH`/`DIR_BEARISH`/`DIR_NEUTRAL`/`DIR_TWO_WAY`/`DIR_UNCLEAR`/`miss`; each row Conf + Invalidation + Dominant; Direction ≠ Signal  
- [ ] **forecast:** Weekly ten-column bull|base|bear ± Est **band** (or miss); disclose "coarse proxy/observation, not execution"; no Obs levels/quantity; ❌ self-write FX Est; ❌ ARIMA/LSTM/darts/near MA continuation; Daily same ten-column short table (1–4w) or cell `miss`; ❌ skip entire section  

### ADAPT gates (2026-09-22 patches)
- [ ] **Post-crawl QA:** ticker SSOT · XAG-USD ban · GBp · proxy≠futures≠LSE · LSE zero→miss · as-of · optional data_delay; failures → Miss ledger only; ❌ invent backfill  
- [ ] **Term structure:** Daily Oil+1; Weekly try-10 or miss; Contango/Back qualitative; ❌ carry formula invent; convenience yield = qualitative + outlet/as-of or n/a  
- [ ] **COT crowdedness:** Daily usually n/a; Weekly Disagg Managed Money cite-or-miss; ❌ COT-only fill for `C_*`/Est  
- [ ] **Shock skeleton:** Shock type → channel enum → dual-leg → bull|base|bear mechanism; ❌ fake linear Q/equilibrium invent  
- [ ] **Calendar:** EIA/WASDE/Export Sales/COT/softs official windows; unknown → `miss`; ❌ FMP invent dates  
- [ ] **Shadow breakdown:** if shadow used → `commodity_signal_breakdown` named factors; Signal has no `DIR_*`; Basis cite Forecast  

### Chain / trunk
- [ ] Load: sources → world → insight → direction → forecast → signal → puzzle → trunk (**obs-backtest not in load**)  
- [ ] Daily: dual-10 + ten-column Forecast short table + ≤3 levels (full-level rows must have Obs TP at Est near band; Basis cite Forecast) + **`## Session summary`** + Risk-on/off  
- [ ] Softs `CC=F`/`SB=F`/`KC=F`; no `XAG-USD`; Oil try CL vs BZ  
- [ ] Revised lands in `inbox/commodities-session/*-revised.md`  
- [ ] No `tm_score`/broker qty/paid API; `commodity_regime` ≠ desk Risk-on/off  
- [ ] **puzzle ≥3** blocks  
- [ ] **shadow 3 keys:** `commodity_signal` · `shadow_commodity_score` · `commodity_signal_breakdown`  
- [ ] **Weekly history×10** (1M/3M/1Y; Scenario cite Forecast)  
- [ ] **christina cite-or-miss** (FX/rates receive)  
- [ ] **Insight/Direction sections non-empty** (required)  
- [ ] **Basis cite Forecast** (when Obs levels present)

### Eval/Sat (optional)
- [ ] **obs-backtest:** prior revised cite + Yahoo Last; lean hit/miss · regime stability · dual-leg attribution rate · Basis-gate pass; ❌ PnL/SimpleFX/IB/Alpaca/RL/ARIMA; path `…/self-review/YYYY-Www-emily-obs-backtest.md`

### Receive/optional
- [ ] **christina-macro-bridge:** SOUL §8 three locks; cite rates path or miss; ❌ invent FX/Rate Est; ❌ rewrite `C_*`; **not in** Keep-8 load
