# christina — Skills checklist (rates/bonds/FX)
> Scrubbed · Display **christina · rates** · observation only · ETF proxy ≠ cash bond · NO_DB

| Field | Value |
|-------|-------|
| **Profile** | `christina` |
| **Git source of truth** | `SOUL.md` + this checklist + `profiles/christina/skills/*/SKILL.md` |
| **Inventory date** | 2026-09-20 (P3 unlock) |

---

## 1. How to use

- **Keep** = required on christina session load  
- **Exclude** = equity/commodity sleeve/broker/desk Risk-on/off/P2 cron patch/DB  

---

## 2. Profile skills (P2 · 6 + position comment)

| Skill (folder) | Purpose | Status |
|----------------|---------|--------|
| `curve-watch` | FRED `DGS2/10/30` · `T10Y2Y` · `T10Y3M`; **Rate scenario draft** handoff | **Keep** |
| `real-rates` | `DFII5`/`DFII10` + **NY Fed SOFR** cite-or-miss; missing → `miss`; do not invent BE/SOFR | **Keep** |
| `fedwatch-consume` | **read-only** cron `<job-id>`; path: `~/.hermes/shared/reports/alice/fedwatch/latest.json` · `YYYY-MM-DD-fedwatch.json`; missing → `miss`; ❌ cron-run | **Keep** |
| `bond-etf-tape` | Gov ladder + LQD/HYG; Ccy; Method A; Obs entry/cut/TP; gates | **Keep** |
| `fx-us-uk-bridge` | Eight majors tape + **FX range** (Daily + Weekly all eight rows need `low–high` or `miss`) + full Obs still Daily≤2/Weekly DXY + emily bridge | **Keep** |
| `rates-session-report` | **Trunk**: assemble; `## Market insight` consolidate; News filter; Lenses; scaffolds (Header then Session summary + Market insight); Fed calendar; portal path | **Keep** |
| `position-plan-rates` | If assigned, write rates comment and analysis in that day's `## Position comments` even when rates-session has no row. Not in the daily rates load. | **Keep** |

**Load order (hard):**  
`curve-watch` → `real-rates` → `fedwatch-consume` → `bond-etf-tape` → `fx-us-uk-bridge` → `rates-session-report` (trunk)

---

## 3. Cadence map

| Cadence | Must |
|---------|------|
| **Daily** | **`## Session summary`** · short curve · News≥1 · Rate scenario · Last+Ccy full universe · bond full Obs levels **≤3** · FX eight rows · **FX range** (eight rows `low–high` or `miss`) · FX full Obs **≤2** · Fed near-term · FX→emily ≥1 sentence · Miss ledger · Footer · portal revised |
| **Weekly** | same + fuller · Lenses · **Gov full ladder** · **LQD/HYG** · **FX range** (eight rows; DXY+EUR+GBP+JPY must not omit) · full Obs only on LONG/SHORT · Fed calendar · News 2–3 sentences · **`## Session summary`** |
| **Adhoc** | may use trunk scaffold; still obey Ccy/Method A/firewall/Session summary |

**IC reject (Zoe):** Daily bond full Obs levels **>3** or FX full Obs **>2**.

---

## 4. Exclude

| Item | Why |
|------|-----|
| Renee `tm_score`/bare `BUY` | Equity T&M |
| Eliza `valuation_score` | P-VAL |
| Broker Emily/M7 orders | Out of scope |
| emily ten-column rewrite | FX bridge only |
| LSEG/Bloomberg/Tradefeeds | Paid/OOU |
| Invented LSE 3–7/10–20 tickers | no SSOT peer → `miss` |
| Desk-wide Risk-on/off final | Alice overall (may cite optional `rates_regime`) |
| Cron 5-arm/FedWatch cron-run | P3b/ops |
| SQLite/memory_store | NO_DB P2 |
| Yield-continuation auto Est | Backtest ~50% |

---

## 5. Deliverable paths (P3)

- Draft daily: `shared/reports/christina/YYYY-MM-DD-rates-session.md`  
- Draft weekly: `shared/reports/christina/YYYY-Www-rates-session.md`  
- **Portal revised:** `inbox/rates-session/*-revised.md`  
- **Train:** draft → Zoe → **christina revise** → `$REPORTS_INBOX/rates-session/YYYY-MM-DD-rates-session-revised.md` (logical `inbox/<category>/<file>` expands to `$REPORTS_INBOX/<category>/<file>` and MUST keep `<category>`; ❌ `$REPORTS_INBOX/YYYY-MM-DD-rates-session-revised.md` inbox root · ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`; 3-layer; do not deliver shared only)  
- Alice overall: cite **Market insight** (prefer) + Session summary; do not paste full body  

---

## 6. Acceptance smoke

- [ ] Daily: `## Session summary` + Last+Ccy full universe + bonds ≤3 full Obs + **FX range** (eight rows `low–high` or `miss`) + FX ≤2 full Obs (DXY first, second slot GBPUSD) + Rate scenario + News≥1 + FX eight rows + Footer  
- [ ] Weekly: same + Gov ladder (incl. TLT) + Other (LQD/HYG) Ccy every row; **FX range** (eight rows or `miss`; DXY+EUR+GBP+JPY must not omit); full Obs only on LONG/SHORT; Lenses; Rate scenario; News filter  
- [ ] Prefer `IDTM.L`/`IDTL.L`; no invented 3–7/10–20 LSE  
- [ ] Method A disclose rough proxy≠DV01; HYG spread-led; TLT Conf≤M; Conf `min()`  
- [ ] FedWatch consume-only; no file=`miss`; no cron-run; locked path in `fedwatch-consume`/SOUL  
- [ ] **DQ gate:** Ccy every row; proxy≠cash disclose; FX polarity correct; Est/TP miss if large FX move/no Basis; as-of per FRED/Yahoo/FedWatch/**SOFR**; miss>invent  
- [ ] **SOFR:** NY Fed official print + as-of **or** Miss ledger `SOFR: miss`; ❌ invent; ❌ substitute DGS/DFII  
- [ ] **Calendar gate:** high-impact window → trim Obs/Conf↓; calendar miss ≠ “no high impact”  
- [ ] **Est-after-FX:** bond Est/Obs full levels only after FX handoff (or FX miss); Last+Ccy may fill early  
- [ ] Miss ledger lists every miss; Sources include Data/News/Institutional (incl. NY Fed SOFR cite-or-miss)  
- [ ] ❌ `C_*`↔`B_*`↔`FX_*`; no Basis → no TP  
- [ ] Trunk skill includes copy-paste blank daily/weekly scaffolds (both have `## Session summary`; Daily reminds ≤3 bond/≤2 FX)  
- [ ] Revised lands in `inbox/rates-session/*-revised.md`  
- [ ] No `tm_score`/broker qty/DB; `rates_regime` ≠ desk Risk-on/off  
- [ ] ❌ 7th Keep skill (obs-backtest if any = Eval/Sat only; not in load)  
