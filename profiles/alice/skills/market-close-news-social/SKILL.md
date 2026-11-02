---
name: market-close-news-social
description: >-
  Alice market-close subsections for financial news analysis, news-vs-social
  market comments, inline Sources, and required four Session-summary cites
  (emily · christina · renee · eliza) or explicit miss. Use on desk-pack overall
  #5 with skills/market-close-report-format and four-specialist-integrate.
  Cite-only social from same-day social-watch snapshot; three sub-agent lenses
  on Alice's macro card.
---

# Market-close — news analysis + news/social comments + four summary cites

**Owner:** Alice · **Train:** daily market-close overall (desk pack #5) · **Not** the Mon–Sat social snapshot  
**Load with:** `skills/market-close-report-format` (ten-section trunk) + `skills/four-specialist-integrate` (section order / Relationships / desk Risk-on/off). This skill fills **named subsections inside** those ten headings — do not invent an 11th top-level template. A = news analysis, B = news vs social → both under `## News / social / macro`. C/C2 → top-level `## Four Market insights` and `## Four Session summaries`. D → `## Sources`.

Mark "Not investment advice". Source grading throughout: `📊 Institutional` / `📰 News` / `📊 Data` / `⚠️ Social`.

---

## When to use

- Alice **overall** card (desk pack Leg 5) after four specialist sessions are `*-revised.md` **or** explicit `miss`
- After same-day `social-watch/*-snapshot.md` exists (or N/A if missing)
- **Not** for Social watcher (`*-snapshot.md` stays lean / anti-wrap)
- **Not** a 6th Jobs light — news/social stays inside overall #5

---

## Macro card — three lenses (max ~3; one Kanban card)

| Lens | Job | Crawl? |
|------|-----|--------|
| `news_macro` | Public financial news → ledger material | Yes — WSJ / FT / Bloomberg / Reuters / Yahoo Finance public pages; **1–2 pages per outlet** |
| `social_discussion` | Interpret today’s social pulse for comments | **No** — read `social-watch/*-snapshot.md` only |
| `bear_risk` | Contrarian / stress / news–social divergence | No extra crawl; uses the other two outputs |

**Hard rules**

- Do **not** dispatch live `x_influence` / Reddit / StockTwits on this path (cite-only).
- Do **not** dispatch `technical` / `fundamentals` here (Renee / Eliza own session files).
- Synthesize **one** Alice brief — do not paste three essays.
- Lens miss → label `miss` / `attempted + miss`; never invent.

---

## Required subsections (paste into close wrap)

### A. Financial news analysis / Financial news analysis

**A1. Headline ledger (5–10 rows)**

| # | Outlet | Date | One-line fact | Public URL or title | Grade |
|---|--------|------|---------------|---------------------|-------|
| 1 | … | YYYY-MM-DD | … | … | 📰 News |

Prefer tape-movers, policy/catalysts, names already in today’s snapshot.  
Do **not** run full-universe `company-news-sweep`. Paywall / block → `attempted + miss` for that outlet.

**A2. Alice analysis (required — not headlines-only)**

- 2–4 **themes** (policy, sector, mega-cap, rates/geo as applicable)
- Per theme: **bull** vs **bear**
- What the tape implies for regime **context** only — does **not** override institutional / price regime
- Near-term watch / catalysts (observation only — not trade advice)
- Length guide: ~½–1 page after the ledger

### B. News vs social — market analysis comments

- ~8–12 lines or 5–7 bullets
- How **news tape** and **20:30 social pulse** agree or diverge + `bear_risk` pushback
- Label every material claim: `📰 News` vs `⚠️ Social`
- Social-alone → `weak_signal`; upgrade only with news or another independent source
- Overlap tickers/catalysts → fold into this block; else one-line pointer + news-only comments (still include bear_risk)
- **Hard sentence (required):**  
  Social detail is in today’s social-watch snapshot; this wrap does **not** re-run Top-20 / Reddit / StockTwits
- **Boundary:** this section = Alice **owned** news/social lens. Four specialist comments/insights → `four-specialist-integrate` **`## Four Market insights`** + **`## Macro view`** (do not mix those names into this section).

### C. Four Market insights (required — cite or miss · priority · Macro view fuel)

Alice overall **must** cite each specialist’s **`## Market insight`**, **or** explicit `miss` + reason. Zoe **REJECT** if omitted without `miss` (Z-MI-03).

| # | Owner | Cite path (daily) | Required |
|---|-------|-------------------|----------|
| 1 | emily | `inbox/commodities-session/YYYY-MM-DD*-revised.md` | Market insight bullets **or** `miss` |
| 2 | christina | `inbox/rates-session/YYYY-MM-DD*-revised.md` | Market insight bullets **or** `miss` |
| 3 | renee | `inbox/daily-trend-momentum/YYYY-MM-DD*-revised.md` | Market insight bullets **or** `miss` |
| 4 | eliza | `inbox/value-session/YYYY-MM-DD*-revised.md` | Market insight bullets **or** `miss` |

Compact only (3–5 bullets each). ❌ full-paste insight body / second specialist essay.  
Citing unre-challenged or T-1 lock fuel → Header four-path `pending-rechallenge` or that leg `miss` / `as-of T-1 + gap` — **do not** treat as live 3–5 bullets.

### C2. Four Session summaries (required — cite or miss)

Alice overall **must** also cite each specialist’s `## Session summary` from the revised inbox path, **or** write an explicit `miss` line for that leg. Zoe REJECT if any of the four is omitted without `miss`.

Compact only (3–5 bullets each). Do **not** full-paste session bodies. Do **not** invent scores / FV / `B_*` / `FX_*` / `C_*`.

**Then:** `## Macro view` (daily + weekly **required**) + Relationships / desk Risk-on/off / gaps → `skills/four-specialist-integrate` (order: insights → summaries → Macro view).

### D. Sources (inline capture)

Sources live **in this markdown file** (no separate DB):

```markdown
## Sources
- 📰 News: <outlet> · <date> · <title or public URL>
- ⚠️ Social: cite `social-watch/YYYY-MM-DD*-snapshot.md` (grades from snapshot only)
- 📊 Institutional / 📊 Data: <as used for regime prints>
- Market insight cites: commodities-session | rates-session | daily-trend-momentum | value-session (path or miss)
- Session cites: same paths · Session summary
- Misses: <outlet or leg>: attempted + miss
```

Deliver with the close wrap to:

- `inbox/daily-social/YYYY-MM-DD-summary-revised.md`
- `inbox/market-close/YYYY-MM-DD-summary-revised.md`

**Inbox resolve (hard):** on-disk ONLY under `$REPORTS_INBOX/`. Logical `inbox/…` = stem-only shorthand. ❌ `~/.hermes/shared/inbox/` · ❌ `shared/reports/<profile>/inbox/`.

---

## Banned on this path

- Using social heat to set Risk-on / Neutral / Risk-off / Crisis
- Second X / Reddit / StockTwits crawl
- Blending `tm_score` and `valuation_score`
- Headlines-only with no Alice analysis
- Citing unre-challenged / T-1 fuel as live 3–5 bullets (must be `pending-rechallenge` or `miss` / `as-of T-1 + gap`)
- Overall without Alice's own `## Session summary` after Header
- Overall without four Market insight cites **and** four summary cites (or explicit `miss` per leg)
- Overall without `## Macro view` (daily or weekly)
- Overall without `## Gaps / callbacks`
- Invented outlets, URLs, or snapshot impact grades
- Extra Kanban card for news (lenses stay under Alice overall)
- Treating news/social as a separate Jobs light
- Confusing §B “news vs social” with Four Market insights / Macro view

---

## Integrate checklist

1. Paste A + B into `## News / social / macro`, C into `## Four Market insights`, C2 into `## Four Session summaries`, D into `## Sources` (section order per `four-specialist-integrate`)  
2. Keep the ten `##` headings from `skills/market-close-report-format` (including Alice-owned `## Session summary`)  
3. Juxtapose four Market insights + Session summaries without reshuffling scores  
4. Write **Macro view** (daily + weekly required) via `four-specialist-integrate`  
5. Relationships + desk Risk-on/off via `four-specialist-integrate`; callbacks per that skill (daily ≤1 + `material_gap`; weekly ≤4)
6. Zoe gate → Alice revise → dual inbox copy  
