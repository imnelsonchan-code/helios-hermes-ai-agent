# Install — Helios @ Hermes AI Agent

End-to-end path to run this finance desk on an **existing Hermes** host.
This repository does **not** install Hermes itself (gateway, models, Telegram).

```text
Hermes installed → Docker web-infra → env + memory → copy profiles/scripts → seed cron → smoke
```

## 0. Prerequisites

- Working Hermes install (`hermes` CLI, gateway, at least one chat channel).
- Docker Engine + Compose plugin.
- Python 3.11+ for host scripts / pytest.
- API keys you already use for models / embeddings (never commit them).

## 1. Clone and layout on the host

```bash
git clone <this-repo-url> helios-hermes-ai-agent
cd helios-hermes-ai-agent
cp .env.example .env   # edit locally; keep gitignored
```

Suggested host paths (override via `.env`):

| Variable | Typical value |
|----------|----------------|
| `HERMES_HOME` | `$HOME/.hermes` |
| `REPORTS_INBOX` | `$HOME/workspace/reports/inbox` |
| `REPORTS_WWW` | `$HOME/web-infra/reports-server/www` |
| `OPENVIKING_ENDPOINT` | `http://127.0.0.1:1933` |

## 2. Docker web infra

See [`web-infra/README.md`](../web-infra/README.md).

```bash
# Example: OpenViking
cp web-infra/openviking/ov.conf.example web-infra/openviking/ov.conf
# edit root_api_key + embedding/vlm keys
mkdir -p web-infra/openviking/data
(cd web-infra/openviking && docker compose up -d)

# SearXNG / Browserless / Crawl4AI / reports-server — same pattern
mkdir -p web-infra/reports-server/{www,archive}
(cd web-infra/reports-server && docker compose up -d)
```

Smoke:

| Check | Expect |
|-------|--------|
| `curl -fsS -H "X-API-Key: $OPENVIKING_API_KEY" http://127.0.0.1:1933/health` | 200 |
| `curl -fsS http://127.0.0.1:8888/healthz` | OK |
| `curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/reports/` | 200 |
| Browserless / Crawl4AI health with their tokens | 200 |

## 3. Memory (OpenViking)

1. Put `OPENVIKING_API_KEY` (same as `server.root_api_key`) in Hermes `.env` and this repo `.env`.
2. Copy [`scripts/host/sync_memory_to_ov.py`](../scripts/host/sync_memory_to_ov.py) and [`scripts/host/sync_memory_ov_cron.sh`](../scripts/host/sync_memory_ov_cron.sh) into `$HERMES_HOME/scripts/`.
3. Schedule the memory sync job from [`docs/cron-catalog.md`](cron-catalog.md) (`memory-sync-ov`).

Details: [`docs/MEMORY.md`](MEMORY.md).

## 4. Web search + browser + crawl

Point Hermes tools / skills at:

| Service | Endpoint (default) | Env |
|---------|--------------------|-----|
| SearXNG | `http://127.0.0.1:8888` | (Hermes search config) |
| Browserless | `http://127.0.0.1:9222` | `BROWSERLESS_TOKEN` |
| Crawl4AI | `http://127.0.0.1:11235` | `CRAWL4AI_API_TOKEN` |

Exact Hermes config keys depend on your Hermes version — set them via `hermes` setup / profile config, not by committing secrets here.

## 5. Copy desk profiles and scripts

```bash
# Scripts pool
cp -a scripts/host/*.py scripts/host/*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
mkdir -p "$HERMES_HOME/scripts/backtest" "$HERMES_HOME/scripts/renee"
cp -a scripts/host/backtest/* "$HERMES_HOME/scripts/backtest/" 2>/dev/null || true
cp -a scripts/host/renee/* "$HERMES_HOME/profiles/renee/workspace/scripts/" 2>/dev/null || true

# Profiles (SOUL / skills) — merge into Hermes profiles/
# alice, christina, emily, eliza, renee, zoe + desk workflows
```

Apply hints: [`docs/APPLY.md`](APPLY.md). Create missing profiles with Hermes (`hermes profiles` / setup) before copying SOUL files.

## 6. Reports portal sync

Copy [`scripts/host/sync_reports_www.sh`](../scripts/host/sync_reports_www.sh) to `$HERMES_HOME/scripts/` and schedule `portal-sync-www` from the cron catalog. Inbox → `REPORTS_WWW` every 30 minutes is the usual cadence.

## 7. Seed schedule jobs

Use [`docs/cron-catalog.md`](cron-catalog.md) / [`fixtures/cron-catalog.yaml`](../fixtures/cron-catalog.yaml).

- Create jobs with your Hermes cron UI/CLI using **semantic names** and the listed schedules.
- Do **not** invent or copy foreign 12-hex IDs from other hosts.
- Prefer one **Desk Pack daily** train and one **Desk Pack weekly** train (legs absorbed) — see catalog.

## 8. Smoke checklist

1. `python3 -m pytest scripts/tests -q` (from this repo; offline).
2. `./scripts/run-equity-sleeve-audits.sh`
3. Hermes: chat a one-liner to `emily` / `alice` (observation only).
4. Drop a sample `.md` into `$REPORTS_INBOX/market-close/` and run `sync_reports_www.sh`; open `/reports/`.
5. Run memory sync once: `python3 $HERMES_HOME/scripts/sync_memory_to_ov.py` (needs `OPENVIKING_API_KEY`).

## What stays out of this pack

- Live `jobs.json` / foreign cron UUIDs  
- Real `.env`, Telegram chat IDs, API keys  
- Installing Hermes gateway from scratch  
- Non-finance Hermes skill trees  

When you are ready for a public GitHub visibility flip, keep those exclusions.
