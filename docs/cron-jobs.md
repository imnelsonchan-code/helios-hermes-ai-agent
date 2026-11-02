# Cron jobs (public snapshot)

This document summarizes desk cron concepts for the scrubbed public repo. Live job IDs live on the Hermes host only.

## Social watcher (Mon–Sat)

- **tier-1 X leaders** roster: `profiles/alice/x-finance-leaders.md` (rotate when budget-limited).
- Output: `social-watch/*-snapshot.md` — monitoring feed; **no Zoe**; not a portal `*-revised.md`.
- Desk overall / market-close path is **social cite-only** — do **not** re-crawl Top-20/Reddit/StockTwits on the close card.
- Inbox path **`daily-social/`** is the **market-close companion** deliverable; **`path ≠ `social-watch/`** (companion ≠ snapshot).

## Market close / Alice overall

- Template skill: `profiles/alice/skills/market-close-news-social` (`news_macro`, `social_discussion`, `bear_risk`).
- Requires Alice **financial news analysis** (headline ledger + themes), news vs social comments, and inline **Sources**.
- **hard anti-wrap:** no standalone macro/policy Notes essays in the snapshot feed.

## FedWatch mirror (christina consume-only)

- Host cron artifact `<job-id>` — christina **consume-only**; see `profiles/christina/skills/fedwatch-consume`.
