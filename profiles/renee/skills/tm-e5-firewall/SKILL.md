---
name: tm-e5-firewall
description: >-
  Renee E5 never-blend firewall: never mix tm pack with valuation_score; every
  BUY/WATCH needs tm_score + score_breakdown; no bare score; overlap WARN only;
  Alice callback anti-mix. Load on every T&M narrative/revise.
---

# T&M E5 firewall — never blend two packs

**Owner:** Renee · **Process:** **P-TM** · **Gate:** **E5** / **D-P-SEP**  
**Load with:** every T&M draft／revise（`skills/tm-session-report`）；shared `trading/technical-analysis`、`trading/stock-screener` as needed  
**Not:** Eliza width / F-Score / FV ownership · blended “one top list” · Alice score lock changes on callback

Mark "Not investment advice".Stage-2 **tm** and **value** packs stay separate.

---

## When to use

- Every daily / weekly T&M narrative and revise
- Whenever a ticker appears in both tm and value packs
- Alice callback / gap-only follow-ups that touch T&M narrative
- Mid-session Eliza ask for valuation **context** only（do not import into T&M screen）

---

## Never blend

Do **not**:

- merge rankings, narratives, or exit rules into one blended list
- average / weight `tm_score` with Eliza `valuation_score`（0–100）、`valuation_composite`、or FV upside
- use Eliza `valuation_score` as a T&M input or copy it into T&M tables
- borrow Eliza quality checks（F/Z、earnings quality、🚨 accounting）to promote or kill a T&M BUY
- write a generic bare `score` that could be read as the other sleeve
- use **FINRA short interest**／**SEC FTD**／ChartExchange short data to change `tm_score`, brackets, Option 6 weights, or BUY／WATCH（cite-only overlay OK）

Eliza screens on **cheapness / quality**；Renee screens on **trend / momentum** — **never mix** those scores or those checks. Short／FTD = tape narrative only.

---

## Required score contract

Every selected / **BUY** / **WATCH** row in the T&M pack **must** carry:

| Field | Rule |
|-------|------|
| `tm_score` | **Published** 0–100 guaranteed（Option 6 weighted → hard clip → 1 decimal） |
| `score_breakdown` | 5 sub-scores（MACD / RSI / MA / ADX / Volume） |
| `weighted_total_raw` | Optional audit — uncapped weighted sum（may be >100）；brackets use published `tm_score` only |
| `base_5indicator_total` | Unweighted 5-leg sum（0–100）；not a substitute for `tm_score` |

- ❌ **Bare score**（generic `score` / unlabeled number）— Zoe REJECT territory
- This is the T&M counterpart to Eliza scoring selected value stocks with `valuation_score`（0–100）
- On overlap → **E5 WARN only**；retain **only** `tm_score` + `score_breakdown` in the T&M pack
- Same ticker may have two different sleeve scores — **never** both in Renee’s T&M table

---

## Overlap = WARN only

If a ticker appears in both tm and value packs:

```text
E5 WARN — dual-pack overlap; T&M table keeps tm_score + score_breakdown only
```

Do **not** promote / demote / re-rank from the other sleeve’s score or quality gates.

---

## Alice callback anti-mix

Callback／gap-only follow-ups may request **narrative re-check only**.

❌ Must **not** change:

- Sunday／live `tm_score` lock
- brackets
- ranking

…unless normal Zoe → Renee revise with pack evidence.

Alice overall cites `## Market insight` (priority) + `## Session summary`; does **not** revise T&M or reshuffle scores.

---

## Hard rules checklist

- [ ] No `valuation_score` / FV / F-Score in T&M ranking or gates
- [ ] Every BUY/WATCH has `tm_score` + `score_breakdown`
- [ ] No bare unlabeled score
- [ ] Overlap → WARN only
- [ ] Callback ≠ score unlock
- [ ] No ETF / intraday / broker into score path
- [ ] No VCP / CANSLIM folded into `tm_score`
- [ ] Short interest／FTD cite-only — ❌ cannot change `tm_score`

---

## Banned

- Blended top list from tm + value  
- Averaging sleeve scores  
- Using volume-gate / Option G demotions to rewrite `tm_score`（cite via `tm-signal-funnel` only）  
- Handing T&M score ownership to Alice on callback  
