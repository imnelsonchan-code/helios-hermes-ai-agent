---
name: catalyst-calendar
description: >-
  Alice weekly forward catalyst calendar: earnings dates, Form 4 clusters
  (cite Eliza/SEC if present), FOMC/CPI from public calendars, IR events.
  Observation only — no trade recommendations. Free data only; Zoe gate if
  published as formal report.
---

# Catalyst calendar — weekly forward watch

**Owner:** Alice · **Train:** weekly calendar / integrate  
**Load with:** weekly integrate or standalone calendar card. Observation desk — **not** broker positioning.

Mark "Not investment advice".source grading：`📊 Institutional` / `📰 News` / `📊 Data` / `⚠️ Social`(social rare here).

---

## When to use

- Weekly forward calendar (ISO week `YYYY-Www`)
- Optional one-line pointer from market-close **next-session watch** → this file
- After free-source pulls (Yahoo earnings, SEC Form 4 / Eliza cite, FRED/public FOMC·CPI calendars, company IR)

**Not** for: Option 6 / five-factor weight changes, FV math, `tm_score` formulas, Long/Short “positioning” language.

---

## Hard rules

- **Free data only** — Yahoo Finance, SEC EDGAR, FRED, public news / IR pages. No paid MCP.
- **Observation only** — dates, facts, impact H/M/L. No trade recommendations; no “Long/Short positioning”.
- **Misses labelled** — `miss` / `attempted + miss`; never invent dates or filings.
- **Form 4** — cite Eliza SEC pack or public EDGAR if present; else `miss` for that name.
- **E5** — do not invent blended scores; calendar is not a score sheet.
- **Formal if published** — social-snapshot Zoe exception does **not** apply. Draft → Zoe → revise → deliver.

---

## Sources to pull

| Block | Free source | Notes |
|-------|-------------|-------|
| Earnings | Yahoo Finance calendar / IR | Confirm ticker + session (BMO/AMC) when public |
| Form 4 clusters | SEC EDGAR or Eliza SEC cite | Cluster = ≥2 same-issuer filings in window; else skip |
| Macro | FOMC / CPI public calendars (Fed, BLS, FRED release tables) | Date + event name only |
| IR / corp | Company IR, 8-K headlines, public press | Conference, guidance, product — fact only |

---

## Output / save

Prefer:

- Draft: `shared/reports/alice/YYYY-Www-catalysts-draft.md`（+ workspace OK）
- After Zoe: `inbox/analysis/YYYY-Www-catalysts-revised.md`（canonical third layer — portal needs `*-revised.md`）
- Optional shared copy of revised same basename for weekly train

Optional market-close pointer: one line under next-session watch → inbox revised path.  
Never resolve `inbox/` under `shared/reports/alice/`.

---

## Required sections

```markdown
# Catalyst calendar — YYYY-Www
Not investment advice · Alice · status: draft | revised (Zoe)

## Window
ISO week, timezone, as-of timestamp.

## Macro / policy
| Date | Event | Impact H/M/L | Source grade | Notes |
|------|-------|--------------|--------------|-------|

## Earnings
| Date | Ticker | Session | Impact H/M/L | Source | Miss? |
|------|--------|---------|--------------|--------|-------|

## Form 4 / insider clusters
| Window | Issuer | Cluster summary | Cite (Eliza/SEC URL) | Miss? |
|--------|--------|-----------------|----------------------|-------|

## IR / other
| Date | Ticker/Theme | Event | Impact H/M/L | Public URL |

## Misses
- <item>: attempted + miss

## Sources
- 📊 Data / 📰 News / 📊 Institutional: …

## Pending Zoe challenge
- 3–5 uncertainty points
```

Impact **H/M/L** = expected tape relevance only — not a score or sleeve rank.

---

## Banned

- Long / Short / “position for” language
- Invented earnings dates, Form 4s, or FOMC weeks
- Blended `tm`+`value` scores; bare `score` field
- Paid data / paid MCP
- Shipping without Zoe when treated as formal report

---

## Integrate checklist

1. Fill all tables; label every miss  
2. Draft → shared；Zoe → `*-revised.md` in canonical `inbox/analysis/`  
3. Optional close-wrap pointer (one line → revised path)  
4. Zoe gate → Alice revise → final  
