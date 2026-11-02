---
name: earnings-analysis
description: >-
  Eliza post-print note (~1–3 pages markdown): beat/miss, drivers, thesis
  impact, mandatory Sources (release, 10-Q/8-K, transcript if available). May
  flag model-update later — does not auto-change width runner. Cite Sunday
  valuation_score only if published; never invent; never emit tm_score.
---

# Earnings analysis — Post-earnings note

**Owner:** Eliza · **Train:** formal (Draft → Zoe → Eliza revise)  
**Length:** Hermes **~1–3 pages** markdown — **not** 8–12 Word pages  
**Load with:** `investment/yahoo-finance-data-fetch`, `investment/sec-edgar-*`, `investment/financial-analysis`, `investment/earnings-quality` as needed  
**Not:** auto width re-score · inventing `valuation_score` · any `tm_score`

Label "Not investment advice". Source grading: `📊 Institutional` / `📊 Data` / `📰 News`.

---

## When to use

- After earnings release (and ideally 8-K / 10-Q) for a name under value work or adhoc deep-dive  
- Follow-on from `earnings-preview` when print lands  
- **Hook:** may **recommend** a later model-update / deep-dive — **do not** auto-change width runner or five-factor weights

---

## Free data only

Yahoo Finance · SEC EDGAR · Finviz · public IR · FRED · public transcript if linked from IR/SEC  
**Banned:** FactSet / Bloomberg / LSEG / MCP-first vendor dumps · invented beat/miss · invented peers

---

## Output shape (1–3 pages)

### Header

- Ticker · period · print datetime · as-of  
- If value-sleeve / Sunday selected: **cite numeric** published `valuation_score` + as-of pack date **only if already revised/published** — else omit or `N/A (not published)`; **never invent**  
- Hard line: this note **does not auto-change** width runner / `valuation_score` / factor weights

### 1. Beat / miss snapshot

| Metric | Actual | Consensus (source+as-of) | Beat/Miss | Grade |
|--------|--------|--------------------------|-----------|-------|
| EPS / Rev / … | … | … or `miss` | … | 📊 Data |

Consensus missing → `attempted + miss`; do not guess street numbers.

### 2. Drivers (qualitative + verifiable numbers)

- 3–6 drivers: volume/price, mix, opex, tax, one-offs, FCF / WC  
- Point to line items in release or 10-Q; no unsourced numbers

### 3. Thesis impact (observation)

- What strengthens / weakens the prior value thesis (cheapness context only)  
- Guidance / outlook language (quote lightly + URL)  
- Explicit: **does not** overwrite five-factor `valuation_score` or width verdict

### 4. Follow-ups (optional checklist)

- [ ] Flag for later model-update / DCF refresh (manual / Kanban — not auto)  
- [ ] Accounting / earnings-quality dig if red flags  
- [ ] Comps refresh via `comps-analysis` if peer multiples matter

### 5. Sources (mandatory)

At least try: earnings release · 10-Q or 8-K · transcript if available.

```markdown
## Sources
- 📊 Institutional: <earnings release> · <date> · <URL>
- 📊 Institutional: <10-Q or 8-K> · <date> · <EDGAR URL>
- 📊 Institutional: <transcript> · <date> · <URL>  (or attempted + miss)
- 📊 Data / 📰 News: …
- Misses: …
```

---

## Save / deliver

Prefer:

- `inbox/analysis/YYYY-MM-DD-<TICKER>-earnings-analysis-draft.md`
- after Zoe: `…-earnings-analysis-revised.md`

Or a dated section embedded in deep-dive / width appendix (formal → still Zoe).  
**3-layer save:** draft workspace + shared OK; `*-revised.md` needs canonical inbox third layer.

---

## E5 / score hard rules

- **Never** emit or invent `tm_score`
- **Never** blend comps or print surprise into `valuation_score`
- Cite Sunday / A-08 `valuation_score` **only** when already published in revised artifacts  
- Invented actuals, consensus, or thesis numbers → **Zoe REJECT** territory

---

## Banned

- 8–12 page Word dumps · Excel / Office JS  
- Auto-writing width JSON or reshuffling selected rows  
- Using beat/miss to mint a new score or blended sleeve metric  
- Sources section empty when filings exist
