# Alice — Hermes refined draft (H-W1)
> Not Helios prompts · Not live Hermes host · Scrubbed for review

# Alice — skills checklist

Mapped from shared `hermes/skills/` (investment / trading / research / reporting / investigation / communication). **Not** a full skill dump — only tasks Alice owns.

Legacy SOUL names (`alice-macro-analysis`, `alice-report-builder`, `alice-market-research`, `alice-risk-framework`, `alice-team-coordination`, `alice-x-influence`, `us-finance-knowledge`) are **conceptual**; use the shared skill paths below when present. Archived `alice-*` skills under `.archive/` are historical format notes only.

**Model:** not pinned in this draft. Select in Hermes setup / `hermes model`.

---

## Cadence (P3a desk-pack · locked)

| Cadence | Alice overall |
|---------|---------------|
| **Daily lite (#5)** | Alice-owned `## Session summary` + News/social + **Four Market insights** + four `## Session summary` cites **or** `miss` + **Macro view (8–15 lines required)** + Relationships (≤2–4 cross-link **sentences**) + desk Risk-on/off + `## Gaps / callbacks`; callback **≤1** with `material_gap: true` |
| **Sun deep-dive (#5)** | Weekly-depth same blocks + **Macro view (~1 page)**; compact specialist cites — ❌ second full specialist session paste; callback ≤4 |
| **Sat S1 / weekly-performance** | Alice-owned `## Session summary` + cite prior 5-pack (or miss) + scoring-eval hit rates; process notes — ❌ do not open a second full weekly overall |
| **Weekly integrate** | One Alice overall draft before Zoe; merge-map per `four-specialist-integrate`; keep P-TM/P-VAL/eval cite |

Skill: `skills/four-specialist-integrate`.

Position-watch comments are not a desk-pack session. Alice only names assignees (`skills/position-plan-dispatch`). The text is appended to that day's `## Position comments`.

---

## Daily

- [ ] **Desk-pack overall #5 (5-pack)** — after four specialist `*-revised.md` **or** explicit `miss`, write overall: Alice-owned `## Session summary` + news/social/macro + **Four Market insights** + four `## Session summary` cites + **Macro view** + Relationships + desk Risk-on/off + `## Gaps / callbacks` + Sources. Skills: `skills/four-specialist-integrate` + `skills/market-close-news-social` + `skills/market-close-report-format`. Zoe after overall draft only. Do not reshuffle T&M ranks or invent FV. **Macro lenses:** `news_macro` (crawl) + `social_discussion` (cite-only snapshot) + `bear_risk`. **Social cite-only:** do **not** re-crawl Top-20/Reddit/StockTwits. Macro regime from institutional/price data — not social heat. **Callback ≤1** card and only if `material_gap: true`. Path note: inbox `daily-social/` companion ≠ `social-watch/` snapshot. Deliver both `daily-social/*-summary-revised.md` and `market-close/*-summary-revised.md`.
- [ ] **Overall revise after Zoe** — receive Zoe challenge on #5 only; address every item; header shows Zoe verdict + reviser `alice`. Enforce via `investment/zoe-challenge-enforcement`. **Not** daily T&M (→ Renee). Shared-only is not deliver.
- [ ] **Source / price sanity** — no NaN prices; free sources only; cross-check (≥2) before promoting signals. Helpers: `investment/yahoo-finance-data-fetch`, `investment/data-quality-audit` as needed.
- [ ] **Social snapshot (Mon–Sat watcher)** — load `skills/social-snapshot`. Single card, no Zoe/no `*-revised.md`. Scan roster `x-finance-leaders.md` (tier-1 daily; rotate if budget). Reddit: ApeWisdom heat screen + ≤2 subs (miss must be labeled). StockTwits thin tape. **Anti-wrap hard ban:** no standalone macro/policy Notes, index/VIX/yield/oil essays — max one-line `regime_chatter`. Social-alone = `weak_signal`.
- [ ] **No daily MOA** — do not trigger `investigation/moa-investigation` on daily Zoe REJECT or daily narrative path.
- [ ] **Saturday integrate — weekly-eval cite** — cite prior-week/latest available `*-weekly-eval.json` Book T/Book V and **separate** `tm_hit_rate`/`value_hit_rate` (two lines); N/A if missing.

---

## Weekly

- [ ] **Macro outlook** — short regime brief (USD, rates, geo, Risk-on/Neutral/Risk-off/Crisis) before valuation width; context only. Skills: conceptual macro + `trading/market-regime` / `trading/macro-filter` as **narrative overlay inputs** (Alice does not own scorer).
- [ ] **Sunday deep-dive overall (5-pack #5)** — Alice-owned `## Session summary` + **Macro view** + news/social rollup + Four Market insights + four Session summary cites (emily/christina/renee/eliza) + Relationships + desk Risk-on/off; follow `skills/four-specialist-integrate` + `skills/alice-weekly-report`. Crash-indicator cite inside Macro view (cite when output exists, else `miss`): `investment/crash-indicator-scanner`. **Commodities/rates:** cite Market insight + Session summaries when present else `miss` — do not invent second essays (`emily` ≠ broker Emily). ❌ second full specialist session paste. Callback ≤4.
- [ ] **Weekly integrate** — merge 5-pack into **one** Alice overall before Zoe IC gate; required section order per `four-specialist-integrate` (including Macro view on weekly path). Never invent scores/FV; mark missing inputs. Callback ≤4.
- [ ] **Weekly revise after Zoe (overall path only)** — Response Tracker/changelog for **Alice overall** draft; **not** weekly T&M (Renee) or valuation width (Eliza) or specialist sessions. Format notes: archived `alice-report-format-rules`.
- [ ] **Self-review (macro/cross-sleeve)** — audit coherence for the week; abstract process lessons only — **do not** dump live MEMORY facts into drafts. Sat S1 portal = `weekly-performance/` overall.
- [ ] **GICS sector relative strength** — sector_screening narrative; Zoe may challenge sector conclusions.
- [ ] **Weekly/governance MOA (optional)** — `investigation/moa-investigation` presets only when path allows (not daily).

---

## Adhoc

- [ ] **Quick-check** — short ticker/theme note; Not investment advice; free sources; still Zoe if treated as formal report.
- [ ] **Deep-dive** — coordinate multi-profile pipeline via `investment/stock-deep-dive`; Alice owns macro/integrate/revise legs, not FV ownership.
- [ ] **News delta** — `investment/company-news-sweep` for “what changed since prior report”.
- [ ] **Screener/theme scan** — candidate watchlist framing only; no guaranteed trade advice. Prefer profile skill `skills/idea-generation` → `…-idea-screen-draft.md` → `inbox/analysis/YYYY-Www-idea-screen-revised.md` with `route: tm | value | both-WARN | drop` (eval-only; never blend scores).
- [ ] **Catalyst calendar** — weekly forward watch via `skills/catalyst-calendar` → draft shared, `inbox/analysis/YYYY-Www-catalysts-revised.md` after Zoe (observation only). Optional close wrap pointer to next-session catalysts.
- [ ] **Thesis tracker** — living falsifiable theses via `skills/thesis-tracker` → `shared/reports/alice/theses/TICKER.md`; material updates also `inbox/analysis/*-thesis-update-revised.md`; Saturday drift → `*-thesis-drift-revised.md`. Sleeve tag `tm`|`value`|`both` (both → E5 WARN).
- [ ] **Request valuation** — `investment/request-eliza-valuation` when FV/DCF/peer needed mid-session; block until Eliza returns; do not fabricate FV.
- [ ] **Risk matrix** — `investment/risk-analysis` (quantified Probability × Impact) on formal recommendations/deep dives.
- [ ] **Callback/discuss (gap-only)** — weekly ≤4 cards per overall train; daily ≤1 + `material_gap: true`; ≤1 retry per gap; owners author notes; Alice cites — not a 6th Jobs light.

---

## Integrate / revise (cross-cutting)

- [ ] **Zoe gate always** — draft stays draft until challenge + revise; Alice revises **overall #5** only; daily/weekly T&M revise stays **Renee**; value revise stays **Eliza**; commodities/rates sessions stay **emily/christina**.
- [ ] **Hard boundaries** — not scorer, not valuator, not broker, not scheduler; **E5 = overlap WARN only · never blend** P-TM/P-VAL packs, scores, or check stacks (Eliza cheapness vs Renee trend).
- [ ] **Delivery** — write scrubbed reports to agreed shared reports location; **omit** host paths, chat/email IDs, holdings, fills, API keys from any checklist example or sample body.

---

## Shared skills Alice commonly loads (name index)

| Shared skill path | Alice use |
|-------------------|-----------|
| `skills/alice-weekly-report` | Weekly deep-dive: same ten sections as daily; GICS/crash-indicator inside Macro view |
| `skills/market-close-report-format` | Daily close ten-section trunk (§4). Legacy twelve-section template retired |
| `skills/market-close-news-social` | Profile skill: news analysis + news/social + four Session summary + Market insight cites + Sources |
| `skills/four-specialist-integrate` | Profile skill: 5-pack overall section order · Alice-owned Session summary · Four Market insights · **Macro view** · Relationships · desk Risk-on/off · callback daily ≤1 + `material_gap`; weekly ≤4 |
| `skills/catalyst-calendar` | Profile skill: weekly forward catalysts → `analysis/*-catalysts-revised.md` |
| `skills/thesis-tracker` | Profile skill: living theses under `alice/theses/` + formal `*-thesis-update-revised.md` / drift |
| `skills/idea-generation` | Profile skill: theme screen + E5 route labels → `*-idea-screen-revised.md` (eval-only) |
| `skills/social-snapshot` | Profile skill: Mon–Sat `social-watch/*-snapshot.md` monitoring feed (no Zoe/no revised) |
| `investment/zoe-challenge-enforcement` | Mandatory Zoe before final |
| `investment/crash-indicator-scanner` | Weekly crash-indicator section |
| `investment/request-eliza-valuation` | Hand off FV/DCF to Eliza |
| `investment/risk-analysis` | Quantified risk matrix |
| `investment/stock-deep-dive` | Adhoc multi-profile deep dive |
| `investment/company-news-sweep` | Adhoc delta news |
| `investment/yahoo-finance-data-fetch` | Free market prints |
| `investment/data-quality-audit` | Source/field sanity |
| `trading/macro-filter` | Publish macro overlay context for T&M (not own scores) |
| `trading/market-regime` | Regime labels for narrative/overlay |
| `investigation/moa-investigation` | Weekly/adhoc MoA only |

---

## Scrub checklist (this agent) / Scrub checklist (this agent)

> Task checkboxes above `[ ]` are **runtime task reminders**, not scrub status.

- [x] No host / home paths (`<hermes-home>/...`, LAN hosts)
- [x] No cron / kanban / job instance IDs
- [x] No API keys, OAuth / tokens, `.env` fragments
- [x] No Telegram / chat IDs, emails, phones
- [x] No broker / account numbers
- [x] No personal holdings, fills, portfolio facts
- [x] No live MEMORY facts
- [x] **E5** stated as WARN only · never blend packs
- [x] Weekly revise scoped to **Alice overall only** (not weekly T&M / value / specialist sessions)
- [x] Daily T&M revise **dropped** (Renee); 5-pack + `four-specialist-integrate` allowed
