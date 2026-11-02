---
name: thesis-tracker
description: >-
  Alice living falsifiable thesis registry per ticker: pillars, invalidation,
  evidence log, sleeve tag. Store shared/reports/alice/theses/TICKER.md.
  Never invent pack scores; E5 both→WARN; Zoe challenges unsupported claim
  changes. Saturday self-review may emit thesis-drift notes.
---

# Thesis tracker — falsifiable living registry

**Owner:** Alice · **Train:** thesis registry / Saturday self-review  
**Load with:** idea-generation handoff, weekly integrate, or Saturday drift pass.

Mark "Not investment advice".source grading：`📊 Institutional` / `📰 News` / `📊 Data` / `⚠️ Social`。

---

## When to use

- Open or update a ticker thesis after idea screen or material evidence
- Saturday self-review — emit **thesis-drift** note if pillars/invalidation moved without support
- Before citing a name in formal weekly integrate

**Alice owns** the registry. Alice does **not** own FV or `tm_score` formulas — cite Renee/Eliza packs by label only.

---

## Hard rules

- **Free data only** — Yahoo, SEC, FRED, public news/IR. No paid MCP.
- **Falsifiable** — every thesis needs explicit invalidation conditions.
- **E5 sleeve tag** — `tm` | `value` | `both`. If `both` → must **WARN** (overlap only); never invent blended scores or bare `score`.
- **No pack invention** — quote existing `tm_score` / `valuation_score` from packs when cited; never recompute or average.
- **Formal if published** — social-snapshot Zoe exception does **not** apply. Claim changes without evidence → Zoe challenge expected.
- Unsupported claim edits → flag for Zoe; do not silently rewrite pillars.

---

## Storage path

```
shared/reports/alice/theses/TICKER.md
```

One file per ticker. Create on first thesis; append evidence log; never delete history (strike + date if retired). Registry alone is **not** a portal Jobs deliverable.

**Formal claim publish** (material pillar/invalidation change meant for inbox/www): also emit  
`inbox/analysis/YYYY-MM-DD-<TICKER>-thesis-update-revised.md` after Zoe（3-layer；cite the living `theses/TICKER.md`）.

Optional Saturday drift note:

```
shared/…-thesis-drift-draft.md → inbox/analysis/YYYY-MM-DD-thesis-drift-revised.md
```

(list tickers whose invalidation/pillars drifted; still Zoe if published formal)

---

## File template

```markdown
# Thesis — TICKER
Not investment advice · Alice · sleeve: tm | value | both  (both → E5 WARN)
Updated: YYYY-MM-DD · status: active | watched | invalidated | retired

## One-liner
Falsifiable claim in one sentence.

## Pillars (2–5)
1. …
2. …

## Invalidation
- [ ] Condition A (metric / event / date)
- [ ] Condition B

## Evidence log
| Date | What changed | Source grade | URL / pack cite | Pillar impact |
|------|--------------|--------------|-----------------|---------------|

## Pack cites (read-only)
- tm_score: <from Renee pack or N/A> — do not recompute
- valuation_score / FV: <from Eliza pack or N/A> — request-eliza-valuation if needed
- E5: if sleeve=both → WARN overlap; show both labels separately

## Open questions
- …

## Sources (when publishing a formal update)
- 📊 Data / 📰 News / 📊 Institutional: <outlet> · <date> · <URL or pack cite>
- Misses: …

## Pending Zoe challenge (when publishing updates)
- …
```

---

## Saturday self-review

1. Scan active theses for pillar/invalidation edits since last review  
2. If claim moved without new evidence row → **thesis-drift** note + Zoe list  
3. If invalidation tripped → mark `invalidated`; do not invent replacement score  
4. `both` sleeves: reaffirm E5 WARN; never blend

---

## Banned

- Invented `tm_score`, FV, or blended ranks
- Sleeve `both` without WARN
- Quiet pillar rewrites with no evidence log row
- Paid MCP
- Publishing formal thesis updates without Zoe

---

## Checklist

1. Sleeve tag set; `both` → WARN  
2. Invalidation present and testable  
3. Evidence log append-only  
4. Pack cites read-only / N/A labelled  
5. Zoe gate on formal publish or material claim change  
