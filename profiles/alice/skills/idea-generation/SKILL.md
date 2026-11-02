---
name: idea-generation
description: >-
  Alice theme/screen → shortlist 5–10 with one-line thesis, risks, and route
  labels tm | value | both-WARN | drop only. Eval-only first; never change live
  Option 6 or five-factor weights. Hand value to Eliza; note tm for Renee
  context. Zoe gate if published formal.
---

# Idea generation — theme screen → routed shortlist

**Owner:** Alice · **Train:** weekly idea screen / eval funnel  
**Load with:** catalyst calendar themes, sector relative-strength notes, or ad-hoc screen card.

Mark "Not investment advice".source grading:`📊 Institutional` / `📰 News` / `📊 Data` / `⚠️ Social`.

---

## When to use

- Theme or factor screen → shortlist **5–10** names
- Eval / paper path first — may **suggest** feed to prediction or watchlist
- After free-data scan (Yahoo screeners/public lists, SEC themes, FRED macro context, public news/IR)

**Not** for: changing live Option 6 T&M weights, Eliza five-factor weights, inventing FV/`tm_score`, or broker-style Long/Short tickets.

---

## Hard rules

- **Free data only** — Yahoo, SEC, FRED, public news/IR. No paid MCP.
- **E5 routing labels only** — every name gets exactly one of:
  - `route: tm`
  - `route: value`
  - `route: both-WARN`
  - `route: drop`
  Never invent blended scores, unified ranks, or bare `score`.
- **Eval-only first** — suggestions to prediction/watchlist are proposals; **MUST NOT** change live Option 6 or five-factor weights.
- **Handoffs**
  - `route: value` → hand to Eliza via `investment/request-eliza-valuation` (Alice does not invent FV)
  - `route: tm` → note for **Renee context only** (no Alice-side `tm_score` math)
  - `route: both-WARN` → dual cite later; keep sleeves separate
  - `route: drop` → one-line reason; no pack write
- **Formal if published** — social-snapshot Zoe exception does **not** apply.

---

## Output / save

Prefer:

- Draft: `shared/reports/alice/YYYY-Www-idea-screen-draft.md`(+ workspace OK)
- After Zoe: `inbox/analysis/YYYY-Www-idea-screen-revised.md`(canonical third layer)
- Shared copy of revised optional when weekly train expects it

Never resolve `inbox/` under `shared/reports/alice/`.

---

## Required sections

```markdown
# Idea screen — YYYY-Www
Not investment advice · Alice · eval-only · status: draft | revised (Zoe)

## Theme / screen
Hypothesis, universe, as-of, free sources used.

## Shortlist (5–10)

| # | Ticker | One-line thesis | Key risks | route |
|---|--------|-----------------|-----------|-------|
| 1 | … | … | … | tm \| value \| both-WARN \| drop |

## Routing summary
- tm → Renee context (no score invent): …
- value → request-eliza-valuation: …
- both-WARN → E5 overlap WARN; dual labels later: …
- drop: …

## Eval / watchlist suggestions (optional)
- Prediction / paper watch: … (proposal only — no live weight change)

## Live engines (hard)
- Option 6 weights: **unchanged**
- Eliza five-factor weights: **unchanged**

## Misses
- <screen/source>: attempted + miss

## Sources
- 📊 Data: <Yahoo/FRED/screener> · <date> · <URL or query label>
- 📰 News / 📊 Institutional: …(if used)
- Misses: <item>: attempted + miss

## Pending Zoe challenge
- 3–5 points (esp. route choices and unsupported theses)
```


---

## Route decision guide (observation, not scores)

| route | Use when |
|-------|----------|
| `tm` | Setup is trend/momentum narrative; needs Renee pack later |
| `value` | Cheapness / FV / quality story; needs Eliza valuation |
| `both-WARN` | Plausible in both sleeves — **WARN only**; never blend |
| `drop` | Weak thesis, data miss, or out of free-data reach |

Impact language OK (theme strength). No Long/Short positioning tickets.

---

## Banned

- Blended scores; inventing `tm_score` / `valuation_score` / FV
- Editing live Option 6 or five-factor weights
- Paid MCP
- Shipping formal screen without Zoe
- Treating eval suggestions as live book changes

---

## Checklist

1. 5–10 rows; every row has `route:` label from the allowed set  
2. Value names queued via `request-eliza-valuation`  
3. Tm names noted for Renee context only  
4. Explicit “live engines unchanged” block  
5. Zoe gate → Alice revise → `inbox/analysis/*-idea-screen-revised.md`  
