# Helios @ Hermes AI Agent

Multi-specialist **investment desk** for [Hermes](https://github.com/): trend/momentum (P-TM), value/width (P-VAL), rates, commodities, macro integrate, plus Docker templates for reports portal, memory (OpenViking), web search, browserless, and crawl.

**Not investment advice.** Scripts read journals and market data; they do not place broker orders unless you wire that on your host.

## Install path (short)

```text
1. Hermes already installed
2. Bring up web-infra Docker (reports, OpenViking, SearXNG, Browserless, Crawl4AI)
3. Copy .env.example → .env ; set keys
4. Copy profiles + scripts/host → $HERMES_HOME
5. Seed cron from docs/cron-catalog.md
6. Smoke: pytest, portal /reports/, memory sync, chat
```

Full guide: **[`docs/INSTALL.md`](docs/INSTALL.md)**

## Audience / prerequisites

- Requires an **existing Hermes** host (this repo does not bootstrap the gateway).
- Docker Compose for [`web-infra/`](web-infra/).
- Secrets stay in `.env` / `ov.conf` — never commit them.

## What is included vs private

| Included here | Stays on your host only |
|---------------|-------------------------|
| Desk docs, SOUL/skills, workflow YAML | Live cron UUIDs / `jobs.json` |
| `scripts/host/` finance + sync helpers | Real API keys, Telegram chat IDs |
| `web-infra/` Compose **templates** | Filled `ov.conf` / service `.env` |
| Semantic cron catalog | Foreign host job IDs |
| Synthetic pytest fixtures | Live holdings |

## Layout

| Path | Purpose |
|------|---------|
| [`docs/INSTALL.md`](docs/INSTALL.md) | End-to-end install |
| [`docs/cron-catalog.md`](docs/cron-catalog.md) | Schedule jobs (semantic) |
| [`docs/MEMORY.md`](docs/MEMORY.md) | OpenViking memory sync |
| [`web-infra/`](web-infra/) | Docker templates (portal, OV, search, browser, crawl, OmniRoute) |
| `docs/` | Desk contracts, scoring, SL/TP, profiles, glossary |
| `profiles/` | Alice, Christina, Emily, Eliza, Renee, Zoe + desk workflows |
| `scripts/host/` | T&M, risk, desk-pack prompts, portal/memory sync |
| `scripts/tests/` | Unit tests (synthetic fixtures) |
| [`fixtures/cron-catalog.yaml`](fixtures/cron-catalog.yaml) | Machine-readable cron catalog |

## Architecture

```text
Docker: OpenViking · SearXNG · Browserless · Crawl4AI · reports-server
                │
Hermes cron (Sarah) → Kanban specialists → Zoe IC gate → *-revised.md
                │                              │
         sync_memory_to_ov              sync_reports_www → /reports/
```

E5: never blend P-TM (`tm_score`) and P-VAL (`valuation_score`).

## Key docs

- [`docs/INSTALL.md`](docs/INSTALL.md) — install
- [`docs/PROFILES.md`](docs/PROFILES.md) — who drafts / revises
- [`docs/desk-artifact-contracts.md`](docs/desk-artifact-contracts.md) — artifact IDs
- [`docs/cron-catalog.md`](docs/cron-catalog.md) — schedules
- [`docs/MEMORY.md`](docs/MEMORY.md) — memory
- [`docs/failover-concept.md`](docs/failover-concept.md) — model failover (vendor-neutral)
- [`docs/APPLY.md`](docs/APPLY.md) — profile apply hints

## Tests

```bash
python3 -m pip install pytest   # if needed
python3 -m pytest scripts/tests -q
./scripts/run-equity-sleeve-audits.sh
./profiles/desk/tests/run_desk_audit.sh
```

Fixtures use synthetic symbols `TST1.L`, `ACME`, `BETA`.

## License

MIT — see [`LICENSE`](LICENSE).
