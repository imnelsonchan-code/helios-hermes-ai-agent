---
name: rates-session-report
description: >-
  christina trunk: assemble daily lite or weekly depth rates session MD.
  Required ## Session summary + ## Market insight (rates-domain roll-up);
  Rate scenario, Macro/Micro/Market lenses, Christina-topic News/Market check,
  gov ladder + LQD/HYG (Ccy, Obs entry/cut/TP), FX majors tape + FX forecast
  (Range on all 8 FX rows; FX_*; Daily full Obs≤2; Weekly Obs only LONG/SHORT),
  Fed calendar, FX→emily bridge, Miss ledger, optional rates_regime. Draft
  under shared/reports/christina/; after Zoe → inbox/rates-session/*-revised.md.
  Free data only; NO_DB; never desk Risk-on/off.
---

# Rates session report — rates session report (trunk)

**Owner:** christina · rates · **Train:** draft → Zoe → **christina revise** → `inbox/rates-session/*-revised.md` 
**Load with:** `curve-watch` → `real-rates` → `fedwatch-consume` → `bond-etf-tape` → `fx-us-uk-bridge` → **this skill (trunk)** 
**Not:** Alice equity news ledger · desk final Risk-on/off · broker/M7 orders · DB · FedWatch cron-run · 7th crawl skill 
**Firewall:** display **"christina · rates"**; observation only · ETF ≠ cash bond · `rates_regime` ≠ desk Risk-on/off

State "Not investment advice · observation only". Source grading: `📊 Data` / `📰 News` / `📊 Institutional`. 

---

## When to use

### Daily lite

- After header, required **`## Session summary`** (5–8 bullets; optional `rates_regime`)+ **`## Market insight`**
- Short curve + **News/Market ≥1 Christina-topic sentence** (URL≤5)+ Rate scenario(1–4w)+ FedWatch cite-or-miss 
- Bond ETF: **all Last+Ccy**; full Obs entry+cut+Est+Obs TP **≤3** rows (across Gov+Other) 
- FX majors eight rows; **FX forecast all eight rows must include range**; full Obs ≤2 (DXY first, second slot GBPUSD); Fed near-term; FX→emily ≥1 sentence 
- Lenses: Macro+Micro primary, Market one line 
- Miss ledger: list every miss 

### Weekly depth

- After header, required **`## Session summary`** + **`## Market insight`**
- Full curve/real + News 2–3 sentences (URL≤12)+ Rate scenario (4–12w)+ **Lenses stub + Dominant** 
- **Gov bond ETF view** full ladder (incl. TLT/LSE/gilts)+ **Other(LQD/HYG)** 
- FX tape + **FX forecast view** (**all eight rows must include range**; DXY/EURUSD/GBPUSD/USDJPY Range cannot be omitted; full Obs only on LONG/SHORT) + bridge paragraph; Fed calendar fuller 

### Not

- Do not set desk Risk-on/off (optional `rates_regime` one line for Alice cite) 
- No FedWatch cron-run, no DB, no invented OAS/DV01/LSE missing peer 
- ❌ shared-only is not deliver (portal requires `inbox/rates-session/*-revised.md`)

**Required:** **`## Session summary`** + **`## Market insight`** — christina **must write**; Alice overall cites Market insight first; **cannot be missing**.

---

## Load order (hard)

```text
curve-watch
 → real-rates
 → fedwatch-consume
 → bond-etf-tape (Method A · Gov + Other)
 → fx-us-uk-bridge
 → rates-session-report (this trunk assembles final)
```

**Weekly extra:** Rate scenario final → Lenses Dominant → FX handoff → finalize Bond ETF **Est/Obs/Basis** → Footer literacy.

---

## Hard rules

- **Before forecast finalize** must pass News/Market check (Christina topic allowlist/denylist); Each News line **outlet + full URL (with path; ❌ bare domain homepage) + date**; list counter material (❌ one-sided; or `News: miss`) (M3)
- **FedWatch degenerate-source gate:** read `cross_check.citation` from `latest.json` only. `miss`, a missing key, an `a_primary` hike probability at 0% or 100%, or a calibration `range_pct` outside 0–100 → the whole `## FedWatch` section is `miss` plus `degenerate_zq_sole_source`. Do not quote that probability. `primary_only` quotes a non-bound a_primary only and sets the c_sentiment cell to `miss`. `b_backup_zq` is the same `ZQ=F` instrument and is not a second source. Copy `c_sentiment` only from `layers.c_sentiment.summary` when `freshness.layers.c_sentiment` is fresh and the value is not 0 or 100. Otherwise that cell is `miss`. A 15–56% band is `miss`. This artifact has no news layer, so the news cell is `miss`. Do not cron-run, re-fetch, or fill a number to avoid miss. Consume-only cron `<job-id>`.
- **Pre-publish DQ** (before Zoe): every row Ccy; proxy≠cash disclose; FX polarity; Est/TP miss if FX large move/no Basis; as-of per FRED/Yahoo/FedWatch/NY Fed SOFR; miss>invent 
- **Calendar gate:** high-impact Fed/BoE/ECB/BoJ → trim Daily full Obs/Conf↓; **calendar miss ≠ empty/"no high impact"** (fail-closed) 
- **Est-after-FX:** bond full Obs/Est final after FX handoff (or FX `miss`); Last+Ccy may be early 
- Every bond ETF row **Ccy**; Last/Est/Obs levels **same currency** 
- Bond Signal only `B_*`/`NO_SETUP`/`miss`; FX only `FX_LONG`/`FX_SHORT`/`FX_HOLD`/`FX_WAIT`/`NO_SETUP`/`miss` 
- ❌ bare `BUY` · ❌ `C_*`↔`B_*`↔`FX_*` · ❌ quantity/order type · ❌ silent FX · ❌ fake OAS/DV01 
- Daily: bond full levels **≤3**; **FX all eight rows must include range**; full Obs ≤2 (independent; DXY first, second slot GBPUSD) 
- Weekly: Gov table → Other table; **FX forecast: all eight rows must include range** (DXY/EURUSD/GBPUSD/USDJPY cannot omit; if unknown `miss`; rows do not vanish); full Obs only on LONG/SHORT 
- Obs TP/entry/cut **require Basis**; no Basis → do not fill levels 
- Conf: TLT≤M; proxy-only≤L; both → **`min()`=≤L** 
- Method A: scenario first; ❌ yield-continuation auto Est 
- Gates: R²→miss; HYG spread-led; FX/cross-ccy gate; FW conflict→bond/FX **no TP** 
- ****`## Session summary` required** (Daily+Weekly; after Header, before Curve); **must include `FX range:` bullet (hard gate · M2; do not delete for brevity)** 
- **`## Market insight` required** (rates-domain insight roll-up; Alice cites first) 
- Optional `rates_regime` ≠ desk Risk-on/off 
- Portal: **draft → Zoe → christina revise → `inbox/rates-session/*-revised.md`** 
- Alice overall: cite **`## Market insight` (first)** + Session summary; no full-paste full ladder 
- Header/footer: Not investment advice · observation only · **ETF proxy ≠ cash bond/gilt** · NO_DB 

---

## Output paths (P3 portal)

| Cadence | Draft (shared) | Portal revised |
|---------|-----------------|----------------|
| Daily | `shared/reports/christina/YYYY-MM-DD-rates-session.md` | `inbox/rates-session/YYYY-MM-DD-*-revised.md` |
| Weekly | `shared/reports/christina/YYYY-Www-rates-session.md` | `inbox/rates-session/YYYY-Www-*-revised.md` |

**Train:** draft → Zoe → **christina revise** → `inbox/rates-session/*-revised.md`(3-layer) 
**Inbox resolve (hard):** logical `inbox/<category>/<file>` expands to `$REPORTS_INBOX/<category>/<file>` and MUST keep `<category>`. ❌ `$REPORTS_INBOX/YYYY-MM-DD-rates-session-revised.md` (inbox root)· ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`. ❌ no DB writes.

---

## Required sections/tables

1. Header (Not investment advice · as-of · cadence) 
2. **`## Session summary`**(required; 5–8 bullets; optional `rates_regime` + Alice pull → Market insight) 
3. **`## Market insight`**(required; rates-domain roll-up; may absorb News/Market + Lenses conclusions) 
4. Curve(short/full) 
5. Real yields 
6. FedWatch-or-`miss` 
7. **News/Market check**(Christina-topic; Daily≥1/Weekly 2–3) 
8. **Rate scenario**(Δbp table) 
9. **Lenses**(Weekly stub required; Daily may compact) 
10. **Gov bond ETF view**(full ladder + Ccy + Obs entry/cut/TP/Basis) 
11. **Other bond ETF view**(LQD/HYG) 
12. FX majors tape(eight rows) 
13. **FX forecast view** (Range/Obs/`FX_*`/Basis) 
14. Fed calendar 
15. FX→commodity(emily bridge) 
16. Optional `rates_regime` 
17. Sources+**Miss ledger**+Footer(literacy) 

### Session summary(required)

Daily and weekly both required (after Header):

```markdown
## Session summary
- …(5–8 bullets; owner voice; not table dump)
- **rates_regime (optional):** easing/tightening/mixed/… + one line
- **Alice pull:** Market insight — 1–2 line pointer (no full paste)
```

Zoe **REJECT** if missing.`rates_regime` ≠ desk Risk-on/off. 

### Market insight(required)

Rates/FX comments & insight roll-up (curve/real rates/Fed narrative). **Do not delete** downstream News/Market and Lenses sections — this section is Alice’s primary cite surface.

```markdown
## Market insight
- … 3–6 bullets: what the market is saying(rates/FX lens)
- May absorb News/Market check + Lenses Dominant conclusion
- ❌ no desk Risk-on/off final; ❌ no self-declared desk-wide Macro view (→ Alice · Zoe Z-MI-02)
```

Zoe: **missing this section → REJECT (Z-MI-01)**.

## Blank report template — Daily scaffold(copy-paste)

Copy the block below to `shared/reports/christina/YYYY-MM-DD-rates-session.md` and fill; after Zoe christina revise → `inbox/rates-session/YYYY-MM-DD-*-revised.md`. 

```markdown
# christina · rates — Daily rates session
**As-of:** YYYY-MM-DD · TZ: …
**Cadence:** daily lite
**Disclaimer:** Not investment advice · observation only · ETF proxy ≠ cash bond/gilt · NO_DB

---

## Session summary
- …
- …
- …
- …
- …
- **FX range:** (hard gate · must list, must not delete)DXY low–high; second slot (GBPUSD preferred)low–high. or fx_range: miss
- **rates_regime (optional):** easing/tightening/mixed/… — …
- **Alice pull: ** Market insight — …

---

## Market insight
- …
- …
- …
- ❌ desk Risk-on/off → Alice Macro view only

---

## Curve(short)

| Series | Level | Δ (1d/1w) | As-of | Note |
|--------|-------|-----------|-------|------|
| DGS2 | | | | |
| DGS10 | | | | |
| DGS30 | | | | |
| T10Y2Y | | | | |
| T10Y3M | | | | |

Shape one-liner:…

---

## Real yields(+ SOFR cite-or-miss)

| Series | Level | As-of | Note |
|--------|-------|-------|------|
| DFII5 | … or `miss` | | |
| DFII10 | … or `miss` | | |
| SOFR | … or `miss` | | NY Fed · funding/liquidity |

❌ do not invent breakeven/SOFR; SOFR does not substitute DGS/DFII.
Real/TIPS: only FRED DFII5/DFII10 (10y real = DFII10); level must be that series print. Nominal 10y: only FRED DGS10. Cannot pull DFII print, or level is DGS* → cell miss.do not fill DFII cells with nominal levels. 

---

## FedWatch(consume-only · cron <job-id>)

| Item | Value | As-of | Note |
|------|-------|-------|------|
| Artifact path/cite | … or `miss` | | no file = miss; ❌ cron-run |
| a_primary | `miss` unless gate passes | | 0%/100% → entire `miss` + `degenerate_zq_sole_source`; ❌ quote |
| c_sentiment | summary or `miss` | | fresh and not 0/100; 15–56% band = `miss` |
| news | `miss` | | artifact has no news layer |

---

## News/Market check(Christina-topic · before forecast finalize)

- 📰 News (≤5 URL): rates/CB/sovereign credit/FX ≥1 line + outlet/**full URL (with path; ❌ bare domain homepage)**/date; counter material required (❌ one-sided) · or `News: miss`
- 📊 Market tape: bond ETF/FX volume or 20d range one line
- ❌ equity/commodity inventory headlines as main narrative; oil/gold at most one line and only adjust FX Conf/emily bridge
- Alice close/social: cite-first or `miss` (no re-crawl)

---

## Rate scenario(1–4w)

| Tenor | Horizon | Bull Δbp | Base Δbp | Bear Δbp | FedWatch cite | Invalidation | As-of |
|-------|---------|----------|----------|----------|---------------|--------------|-------|
| DGS2 | 1–4w | | | | path or miss | yield leaves envelope | |
| DGS10 | 1–4w | | | | | | |
| DGS30 | 1–4w | | | | | | |

world/risk one line: … 
❌ OIS/forwards/ML path/invent FW probabilities. 

---

## Lenses(daily compact)

- Macro: Rate scenario cite · world/FW one line
- Micro: ETF Ccy/Last/coarse proxy disclose · peer/spread
- Market: volume/range or narrative one line · Conf effect
- Dominant: macro-led | micro-led | market-led | mixed

---

## Gov bond ETF view(Last+Ccy all rows; **full Obs ≤3** across both tables combined)

| Bucket | ETF | Venue | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|--------|-----|-------|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| ~1–3y | SHY | US | USD | | | | | | B_* / … | | | |
| ~3–7y | IEI | US | USD | | | | | | | | | |
| ~7–10y | IEF | US | USD | | | | | | | | | |
| ~10–20y | TLH | US | USD | | | | | | | | | |
| ~20y+ | TLT | US | USD | | | | | | | | | ≤M |
| 1–3y | IBTA.L | LSE | USD | | | | | | | | | |
| 3–7y LSE | — | LSE | — | `miss` | — | — | — | — | miss | — | no SSOT peer · do not invent | — |
| 7–10y | IDTM.L | LSE | USD* | | | | | | | | | |
| 10–20y LSE | — | LSE | — | `miss` | — | — | — | — | miss | — | no SSOT peer · do not invent | — |
| 20y+ | IDTL.L | LSE | USD* | | | | | | | | | |
| Gilt short | IGLS.L | LSE | GBP | | | | | | | | | |
| Gilt all | IGLT.L | LSE | GBP | | | | | | | | | |
| IL (opt) | INXG.L | LSE | GBP | Last-only or `miss` | — | — | — | — | | | | |

\*When using `IBTM.L`/`IBTL.L` label **actual** Ccy (often GBP). GBp quotes must disclose. 
Coarse proxy ≠ DV01. TLT Conf≤M. 
**Budget:** Daily bond full Obs **≤3** (Gov+Other). Est/TP wait for FX handoff (or FX-gate pending/miss).

---

## Other bond ETF view(LQD/HYG)

| ETF | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|-----|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| LQD | USD | | | | | | B_* | | credit+rates+as-of | |
| HYG | USD | | | | | | | | **spread-led**+as-of | |

**Daily trim:** full Obs entry+cut+Est+Obs TP rows = (≤3 across both tables): _______ · _______ · _______ 
Rest: Last+Ccy+Signal only.

---

## FX majors

| Pair | Yahoo | Last | Chg | As-of | Note |
|------|-------|------|-----|-------|------|
| DXY | DX-Y.NYB | | | | |
| EURUSD | EURUSD=X | | | | |
| GBPUSD | GBPUSD=X | | | | |
| USDJPY | USDJPY=X | | | | |
| USDCHF | USDCHF=X | | | | |
| USDCAD | USDCAD=X | | | | |
| AUDUSD | AUDUSD=X | | | | |
| USDCNH | USDCNH=X | | | | offshore; ❌ invent onshore |

Missing → `miss`. ❌ forwards/NDF/IV. Quote convention: EURUSD/GBPUSD/AUDUSD = USD per 1 foreign unit. 

---

## FX forecast view

| Pair/Index | Yahoo | Quote | Last | Range | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|------------|-------|-------|------|------|-----------|---------|--------|--------|---------|-------|------|
| DXY | DX-Y.NYB | index | | | | | | FX_* | | macro+micro+as-of | |
| EURUSD | EURUSD=X | USD/EUR | | | | | | | | Fed vs ECB+as-of | |
| GBPUSD | GBPUSD=X | USD/GBP | | | | | | | | | |
| USDJPY | USDJPY=X | JPY/USD | | | | | | | | | |
| USDCHF | USDCHF=X | CHF/USD | | | | | | | | | |
| USDCAD | USDCAD=X | CAD/USD | | | | | | | | | |
| AUDUSD | AUDUSD=X | USD/AUD | | | | | | | | | |
| USDCNH | USDCNH=X | CNH/USD | | | | | | | | | |

**Daily trim:** all eight rows must include `Range` = `low–high` (that row's quote convention; low < high) or cell exactly `miss`; no blank, dash, or single point. 
Range does not consume Daily full Obs ≤2 slots. full Obs entry+cut+TP still only for `FX_LONG`/`FX_SHORT`, DXY first, second slot GBPUSD. 
`FX_HOLD`/`FX_WAIT`/`NO_SETUP` still need Range; do not fill entry/cut/TP. 
If Obs TP filled, must lie inside Range (inclusive); else drop TP or Range → `miss`. ❌ forwards/NDF/IV. 

---

## Fed calendar(near-term · fail-closed)

| Date | Event | Relevance | Grade |
|------|-------|-----------|-------|
| | FOMC/CPI/NFP/… | | 📊 / 📰 |
| | | | |

Cannot pull/verify → write **`calendar: miss`** + reason — ❌ empty table as "no high impact". High-impact window → trim bond/FX full Obs budget/Conf↓.

---

## FX → commodity(emily bridge)

One line: how GBPUSD/DXY/real yields explain US/UK commodity leg divergence (cite emily path or `miss`). 
❌ rewrite ten columns/`C_*`.

---

## Optional rates_regime

- **Call (optional):** easing/tightening/mixed/… 
- **Rationale:** …
- **Scope:** rates observation only; Alice desk Risk-on/off may cite, **not** finalized here

---

## Sources

- 📊 Data: FRED · Yahoo · NY Fed SOFR (https://www.newyorkfed.org/markets/reference-rates/sofr · as-of … or `miss`)· …
- 📰 News: … or `News: miss`
- 📊 Institutional: FedWatch artifact/official calendar URL (or miss); NY Fed SOFR may classify as Data or Institutional (cite-or-miss)
- Misses: see Miss ledger

### Miss ledger

| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| | FRED/ETF/FX/FW/SOFR | | | no |

---

## Footer

Not investment advice · observation only · **ETF proxy ≠ cash bond/gilt** · quote currency marked Ccy · coarse proxy ≠ DV01 · NO_DB · portal `inbox/rates-session/*-revised.md` · FedWatch consume-only (❌ cron-run)· `rates_regime` ≠ desk Risk-on/off · ❌ `C_*`↔`B_*`↔`FX_*`
```

---

## Blank report template — Weekly scaffold(copy-paste)

Copy the block below to `shared/reports/christina/YYYY-Www-rates-session.md` and fill; after Zoe christina revise → `inbox/rates-session/YYYY-Www-*-revised.md`. 
**ISO week:** `Www` = week number (e.g. `2026-W38-rates-session.md`). 

```markdown
# christina · rates — Weekly rates session
**Week:** YYYY-Www · **As-of:** YYYY-MM-DD · TZ: …
**Cadence:** weekly depth
**Disclaimer:** Not investment advice · observation only · ETF proxy ≠ cash bond/gilt · NO_DB

---

## Session summary
- …
- …
- …
- …
- …
- **FX range:** (hard gate · must list, must not delete)DXY, EURUSD, GBPUSD, USDJPY each low–high. or fx_range: miss
- **rates_regime (optional):** … — …
- **Alice pull: ** Market insight — …

---

## Market insight
- …
- …
- …
- ❌ desk Risk-on/off → Alice Macro view only

---

## Curve

| Series | Level | Δ (1w/1m) | As-of | Note |
|--------|-------|-----------|-------|------|
| DGS2 | | | | |
| DGS10 | | | | |
| DGS30 | | | | |
| T10Y2Y | | | | |
| T10Y3M | | | | |

Shape/slope narrative:…

---

## Real yields(+ SOFR cite-or-miss)

| Series | Level | Δ | As-of | Note |
|--------|-------|---|-------|------|
| DFII5 | … or `miss` | | | |
| DFII10 | … or `miss` | | | |
| SOFR | … or `miss` | | | NY Fed · funding/liquidity |

❌ do not invent breakeven/SOFR; SOFR does not substitute DGS/DFII.
Real/TIPS: only FRED DFII5/DFII10 (10y real = DFII10); level must be that series print. Nominal 10y: only FRED DGS10. Cannot pull DFII print, or level is DGS* → cell miss.do not fill DFII cells with nominal levels. 

---

## FedWatch(consume-only · cron <job-id>)

| Item | Value | As-of | Note |
|------|-------|-------|------|
| Artifact cite | … or `miss` | | ❌ cron-run |
| a_primary | `miss` unless gate passes | | 0%/100% → entire `miss` + `degenerate_zq_sole_source`; ❌ quote |
| c_sentiment | summary or `miss` | | fresh and not 0/100; 15–56% band = `miss` |
| news | `miss` | | artifact has no news layer |

---

## News/Market check(Christina-topic · before forecast finalize)

- 📰 News (≤12 URL): 2–3 lines rates/CB/sovereign credit/FX + outlet/**full URL (with path; ❌ bare domain homepage)**/date; counter material (❌ one-sided) · or `News: miss`
- 📊 Market tape: volume/20d range · Conf effect
- Denylist: drop equity/commodity inventory; oil/gold adjust FX Conf/emily bridge only; HYG uses credit spread language
- Alice close/social: cite-first or `miss`

---

## Rate scenario (4–12w)

| Tenor | Horizon | Bull Δbp | Base Δbp | Bear Δbp | FedWatch cite | Invalidation | As-of |
|-------|---------|----------|----------|----------|---------------|--------------|-------|
| DGS2 | 4–12w | | | | path or miss | yield leaves envelope | |
| DGS10 | 4–12w | | | | | | |
| DGS30 | 4–12w | | | | | | |
| UK 10y (opt) | 4–12w | | | | local cite or miss | | |

World/credit risk appetite one line:…

---

## Lenses

- Macro: Rate scenario cite · world/FW one line
- Micro: ETF Ccy/Last/Est method disclose · peer/spread
- Market: volume/range · narrative one line · Conf effect
- Dominant: macro-led | micro-led | market-led | mixed

---

## Gov bond ETF view (full ladder · rows do not vanish)

| Bucket | ETF | Venue | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|--------|-----|-------|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| ~1–3y | SHY | US | USD | | band or miss | | | | B_* | 4–12w | | |
| ~3–7y | IEI | US | USD | | | | | | | | | |
| ~7–10y | IEF | US | USD | | | | | | | | | |
| ~10–20y | TLH | US | USD | | | | | | | | | |
| ~20y+ | TLT | US | USD | | | | | | | | | ≤M |
| 1–3y | IBTA.L | LSE | USD | | | | | | | | | |
| 3–7y LSE | — | LSE | — | `miss` | — | — | — | — | miss | — | no SSOT peer | — |
| 7–10y | IDTM.L (or IBTM.L) | LSE | *actual* | | | | | | | | | |
| 10–20y LSE | — | LSE | — | `miss` | — | — | — | — | miss | — | no SSOT peer | — |
| 20y+ | IDTL.L (or IBTL.L) | LSE | *actual* | | | | | | | | | |
| Gilt short | IGLS.L | LSE | GBP | | | | | | | | | |
| Gilt all | IGLT.L | LSE | GBP | | | | | | | | | |
| IL | INXG.L | LSE | GBP | | | | | | | | | |

Method A: scenario translation; coarse proxy ≠ DV01; Est prefers band. Peer check (Method C) may footnote.

---

## Other bond ETF view (LQD/HYG · required)

| ETF | Ccy | Last | Est | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|-----|-----|------|-----|-----------|---------|--------|--------|---------|-------|------|
| LQD | USD | | | | | | B_* | 4–12w | rates+credit+as-of | |
| HYG | USD | | | | | | | | **spread-led**/mixed+as-of | |

Low R²/no spread narrative → HYG Est=`miss`.

---

## FX majors

| Pair | Yahoo | Last | Chg | As-of | Note |
|------|-------|------|-----|-------|------|
| DXY | DX-Y.NYB | | | | |
| EURUSD | EURUSD=X | | | | USD per 1 EUR |
| GBPUSD | GBPUSD=X | | | | USD per 1 GBP |
| USDJPY | USDJPY=X | | | | |
| USDCHF | USDCHF=X | | | | |
| USDCAD | USDCAD=X | | | | oil→FX Conf only |
| AUDUSD | AUDUSD=X | | | | commodity→FX Conf only |
| USDCNH | USDCNH=X | | | | offshore |

---

## FX forecast view(Weekly · DXY Range mandatory)

| Pair/Index | Yahoo | Quote | Last | Range | Obs entry | Obs cut | Obs TP | Signal | Horizon | Basis | Conf |
|------------|-------|-------|------|------|-----------|---------|--------|--------|---------|-------|------|
| DXY | DX-Y.NYB | index | | | | | | FX_* | 4–12w | Fed/real+as-of | |
| EURUSD | EURUSD=X | USD/EUR | | | | | | | | Fed vs ECB | |
| GBPUSD | GBPUSD=X | USD/GBP | | | | | | | | Fed vs BoE | |
| USDJPY | USDJPY=X | JPY/USD | | | | | | | | Fed vs BoJ | |
| USDCHF | USDCHF=X | CHF/USD | | | | | | | | | |
| USDCAD | USDCAD=X | CAD/USD | | | | | | | | | |
| AUDUSD | AUDUSD=X | USD/AUD | | | | | | | | | |
| USDCNH | USDCNH=X | CNH/USD | | | | | | | | | |

**Weekly trim:** all eight rows must include `Range` = `low–high` (that row's quote convention; low < high) or cell exactly `miss`; no blank, dash, or single point. 
Range does not consume Daily full Obs ≤2 slots. full Obs entry+cut+TP still only for `FX_LONG`/`FX_SHORT`, DXY first, second slot GBPUSD. 
`FX_HOLD`/`FX_WAIT`/`NO_SETUP` still need Range; do not fill entry/cut/TP. 
If Obs TP filled, must lie inside Range (inclusive); else drop TP or Range → `miss`. ❌ forwards/NDF/IV. 
Weekly extra: DXY, EURUSD, GBPUSD, USDJPY Range cannot be omitted (if unknown `miss` + reason). 

---

## Fed calendar(fuller · fail-closed)

| Date | Event | Relevance | Grade |
|------|-------|-----------|-------|
| | | | |
| | | | |
| | | | |

Cannot pull → **`calendar: miss`** — ❌ treat as "no high impact". High-impact window → Conf↓/full Obs trim.

---

## FX → commodity(emily bridge)

One paragraph: how DXY/GBPUSD/DFII drive emily US/UK leg divergence (cite `shared/reports/emily/…` or `miss`). 
❌ rewrite ten columns.

---

## Optional rates_regime

- **Call (optional):** … 
- **Rationale:** … 
- **Scope:** rates observation only; Alice desk may cite

---

## Sources

- 📊 Data: … · NY Fed SOFR (official URL · as-of … or `miss`)
- 📰 News: … or `News: miss`
- 📊 Institutional: FedWatch/official calendar; NY Fed SOFR cite-or-miss
- Misses: see Miss ledger

### Miss ledger

| Symbol | Leg | Attempted | Reason | Retry? |
|--------|-----|-----------|--------|--------|
| | FRED/ETF/FX/FW/SOFR | | | no |

---

## Footer

Not investment advice · observation only · **ETF proxy ≠ cash bond/gilt** · Ccy marked · coarse proxy ≠ DV01 · Method A scenario first (❌ yield-continuation) · NO_DB · portal `inbox/rates-session/*-revised.md` · FedWatch consume-only (❌ cron-run)· `rates_regime` ≠ desk Risk-on/off · ❌ `C_*`↔`B_*`↔`FX_*`
```

---

## Embed contract (Alice overall)

- Alice overall: **cite** `## Market insight`(first)+ `## Session summary` + optional `rates_regime` from `inbox/rates-session/*-revised.md` 
- Jobs overall may excerpt at most: short curve + compact ETF table + one FX line 
- Full ladder + full Obs levels **stay in** christina session MD 
- christina session **is** portal light (`rates-session/`); not Alice-only embed 
- ❌ no desk Risk-on/off final (Alice Macro view only) 

---

## Forbidden

- LSEG/Bloomberg/Tradefeeds · bare BUY · `tm_score` · fake OAS/DV01/CTD 
- DB · FedWatch cron-run 
- silent FX · peer fill prices · invent LSE 3–7/10–20 ticker 
- yield-continuation auto Est/Obs TP 
- missing `## Session summary` or `## Market insight` · shared-only as deliver · treat `rates_regime` as desk Risk-on/off 
- full-paste full ladder into Alice overall 

---

## Checklist

- [ ] Load order: curve → real → fedwatch → bond-etf → fx → trunk 
- [ ] Header/footer: Not investment advice · ETF≠cash · NO_DB 
- [ ] **`## Session summary`** (after Header; 5–8 bullets; **must include `FX range:` bullet**; optional `rates_regime`; Alice pull → Market insight) 
- [ ] **`## Market insight`** (rates roll-up; no desk Risk-on/off final) 
- [ ] News/Market check passed (Christina-topic; real URL+date; not one-sided) 
- [ ] Rate scenario table complete; Lenses (weekly) 
- [ ] Gov full ladder + Other LQD/HYG; every row Ccy 
- [ ] Daily bond ≤3 full Obs; **FX all eight rows must include range**; full Obs ≤2 (DXY first, second slot GBPUSD); Basis complete 
- [ ] Daily: `B_WAIT`/`FX_WAIT` **do not consume** full Obs TP slots (WAIT Signal only; no entry/cut/TP)
- [ ] Weekly FX forecast: **all eight rows must include range**; DXY/EURUSD/GBPUSD/USDJPY Range cannot be omitted; full Obs only on LONG/SHORT 
- [ ] Method A/gates (R²/HYG/TLT/FX/FW) 
- [ ] **DQ gate** passed; **calendar fail-closed**; **Est-after-FX** 
- [ ] FX eight-row tape; Fed calendar; FX→emily 
- [ ] Miss ledger; Sources Data/News/Institutional (incl. NY Fed SOFR cite-or-miss) 
- [ ] FedWatch consume-only; no cron-run; degenerate-source gate (0%/100%/missing key/`range_pct` out of bounds → entire `miss` + `degenerate_zq_sole_source`; ❌ quote; news cell = `miss`) 
- [ ] Train: draft → Zoe → christina revise → `inbox/rates-session/*-revised.md` 
- [ ] ❌ `C_*`↔`B_*`↔`FX_*`; `rates_regime` ≠ desk Risk-on/off 
- [ ] Paths: draft `…-rates-session.md`; revised inbox 
