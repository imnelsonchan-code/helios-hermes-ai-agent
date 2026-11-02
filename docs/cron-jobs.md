# Cron jobs (concepts)

Desk schedule **concepts** for this install pack. For the full semantic catalog
(schedules, owners, scripts), use:

- [`cron-catalog.md`](cron-catalog.md)
- [`fixtures/cron-catalog.yaml`](../fixtures/cron-catalog.yaml)
- Install path: [`INSTALL.md`](INSTALL.md)

Live job IDs are **host-local**. Never commit foreign 12-hex cron UUIDs.

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

## Desk Pack trains

- **Daily (Mon–Fri):** one Sarah job — Wave1 christina ∥ renee → Wave2 emily ∥ eliza → Alice → `daily_tm_with_exits.sh`.
- **Weekly (Sun):** one Sarah job — christina → emily → weekly T&M → width → Alice.
- **Saturday S1:** serial self-review; portal = Alice overall.

See workflow YAML under `profiles/desk/workflows/` and prompt modules under `scripts/host/desk_pack_*.py`.
