---
name: comps-analysis
description: >-
  Eliza peer comps table on top of investment/peer-comparison: peer-set
  rationale, as-of date, EV/EBITDA, P/E, FCF yield, source per cell or row;
  Yahoo misses as omissions. Informs FV context only — never overwrites
  valuation_score or five-factor weights; never emits tm_score.
---

# Comps analysis — Peer comps (context only)

**Owner:** Eliza · **Train:** formal when standalone (Draft → Zoe → Eliza revise)  
**Load with:** `investment/peer-comparison` (base), `investment/yahoo-finance-data-fetch`, Finviz / SEC / public IR as needed  
**Role:** comps **inform** FV / narrative context — **do not** overwrite five-factor `valuation_score` or width weights

Label "Not investment advice". Source grading: `📊 Data` / `📊 Institutional`.

---

## When to use

- Relative-value appendix for width, deep-dive, or standalone analysis file  
- Before arguing "cheap vs peers" in prose — table first, then 3–6 lines of context  
- **Not** a substitute for Sunday width screener; **not** a T&M tool

---

## Free data only

Yahoo Finance · SEC EDGAR · Finviz · public IR · FRED  
**Banned:** FactSet / Bloomberg / LSEG / MCP-first comps · invented peers · invented multiples

---

## Table contract (put near top)

### Meta

| Field | Rule |
|-------|------|
| Subject ticker | Required |
| Peer set | Named list + **rationale** (sector, size, business mix) — max ~6–10 peers |
| As-of | Single date (or per-row if mixed); timezone if intraday |
| Scope | EV/EBITDA · P/E · FCF yield (add columns only if sourced) |

### Comps table

| Ticker | EV/EBITDA | P/E | FCF yield | Source (cell or row) | As-of | Notes |
|--------|-----------|-----|-----------|----------------------|-------|-------|
| SUBJECT | … | … | … | Yahoo / Finviz / … · URL or title | YYYY-MM-DD | … |
| PEER1 | … | … | … | … | … | … |

**Omissions:** Yahoo / Finviz miss → leave cell `miss` or drop peer to Omissions with reason — **never invent** a multiple or peer.

```markdown
### Omissions
- <TICKER or metric>: attempted + miss · <source tried>
```

### Peer-set rationale (required prose)

- Why these peers · who was excluded and why (1 short paragraph)  
- Invented or unexplained peers → **Zoe REJECT** territory

### Context only (after table)

- 3–6 bullets: where subject sits vs median / range  
- Explicit hard sentence:  
  Peer multiples are for FV **context** only; **do not rewrite** `valuation_score`, five-factor weights, or width ranking

---

## Save / deliver

- Standalone: `shared/…-comps-draft.md` → Zoe → `inbox/analysis/YYYY-MM-DD-<TICKER>-comps-revised.md`  
- **Embed** in width / deep-dive appendix → rides **that** train's Zoe gate (same table contract; do not skip Zoe)  
**3-layer save:** draft workspace + shared OK; user-facing revised needs canonical inbox third layer.

---

## Sources

```markdown
## Sources
- 📊 Data: <Yahoo/Finviz> · <date> · <URL or query label> · metrics covered
- 📊 Institutional: <10-K/IR> · <date> · <URL> (if used for peer rationale)
- Misses: …
```

Per-cell or per-row source is enough if the Sources block lists the outlets; do not leave multiples unsourced.

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`
- **Never** blend comps into / overwrite `valuation_score` or factor weights (33/28/19/15/5)  
- Comps do **not** set `width_verdict`  
- Cite published `valuation_score` only if already in revised pack; comps table is independent context  
- Invented peers or invented cell values → **Zoe REJECT**

---

## Banned

- Excel / Office JS automation · vendor "comps sheets" without public URL  
- Using peer median to mint a fake five-factor score  
- Silent peer swaps after Zoe without re-rationale  
- Empty source column on filled metrics
