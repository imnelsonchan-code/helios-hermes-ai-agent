---
name: earnings-preview
description: >-
  Eliza pre-earnings one-pager: consensus (source+as-of or miss), what-to-watch,
  bull/base/bear table, catalyst checklist. Optional A-08 / adhoc. Free data
  only; does not change valuation_score; never emits tm_score. Formal train
  Draft → Zoe → Eliza revise; Not investment advice + Sources.
---

# Earnings preview — Pre-earnings one-pager

**Owner:** Eliza · **Train:** formal (Draft → Zoe → Eliza revise) · Optional **A-08** / adhoc  
**Load with:** `investment/earnings-calendar` (timing), `investment/yahoo-finance-data-fetch`, `investment/sec-edgar-*` as needed  
**Not:** width re-score · model-update · T&M / `tm_score`

Label "Not investment advice". Source grading: `📊 Data` / `📰 News` / `📊 Institutional` (public IR / SEC).

---

## When to use

- Pre-print brief for a value-sleeve or watchlist name (A-08 Monday follow-up, adhoc Kanban, or deep-dive prep)
- After earnings date is known (Yahoo / IR calendar) — if date miss → label `miss`; do not guess
- **Not** for post-print (use `earnings-analysis`); **not** Sunday width runner

---

## Free data only

Yahoo Finance · SEC EDGAR · Finviz · public IR · FRED  
**Banned:** FactSet / Bloomberg terminal / LSEG / MCP-first vendor dumps · invented consensus · invented peers

---

## Output shape (~1 page markdown)

### Header

- Ticker / name · fiscal period · expected print date (TZ) · as-of timestamp  
- Sleeve context if any (Sunday lock name / A-08) — **cite** published `valuation_score` only if already in revised pack; **never invent**  
- Hard line: this preview **does not change** `valuation_score`, five-factor weights, or width verdict

### 1. Consensus (or miss)

| Metric | Consensus | Source | As-of | Grade |
|--------|-----------|--------|-------|-------|
| EPS / Revenue / other | … or `miss` | Yahoo / IR | YYYY-MM-DD | 📊 Data |

No street number → `attempted + miss`; **never invent**.

### 2. What to watch

- 3–6 bullets: margins, guidance, segment KPIs, balance-sheet / FCF, one-offs  
- Tie to prior 10-Q / 8-K themes when filed (SEC URL)

### 3. Bull / base / bear

| Scenario | What would confirm | Thesis impact (observation) |
|----------|--------------------|-----------------------------|
| Bull | … | … |
| Base | … | … |
| Bear | … | … |

Qualitative only — **not** a new FV or score.

### 4. Catalyst checklist

- [ ] Print date / AH vs RTH confirmed  
- [ ] Prior-year comps / one-time items noted  
- [ ] Guidance language watch  
- [ ] Post-print path: hand off to `earnings-analysis` (do not auto-change width)

### 5. Sources

```markdown
## Sources
- 📊 Data: <outlet> · <date> · <URL>
- 📰 News: … (if used)
- Misses: <item>: attempted + miss
```

---

## Save / deliver

Prefer:

- `inbox/analysis/YYYY-MM-DD-<TICKER>-earnings-preview-draft.md`
- after Zoe: `…-earnings-preview-revised.md`

Or embed a short block in width / deep-dive appendix (still Zoe if formal).  
**3-layer save:** draft may live workspace + shared; user-facing `*-revised.md` needs canonical inbox third layer (do not write to shared only).

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`
- **Never** blend with / overwrite `valuation_score` or five-factor weights
- Preview **informs context only** — no width re-rank, no verdict change
- Invented consensus / invented numbers → **Zoe REJECT** territory

---

## Banned

- Excel / Office JS automation  
- Auto-updating Sunday pack or width runner  
- FactSet/Bloomberg/LSEG language or paywalled scrape as "consensus" without public URL  
- Headlines-only with empty bull/base/bear
