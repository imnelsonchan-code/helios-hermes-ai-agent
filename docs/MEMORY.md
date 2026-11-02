# Memory — OpenViking + Hermes MEMORY.md

Hermes keeps a local `MEMORY.md` per profile. OpenViking makes that memory
**searchable cross-profile** and stores durable KB report URIs.

## Architecture

```text
MEMORY.md (per profile)
    │  every ~30m  sync_memory_to_ov.py
    ▼
viking://user/<profile>/peers/hermes/memories/patterns/mem_LOCAL_MEMORY_<profile>.md

Report pipelines / viking_kb upsert
    ▼
viking://resources/reports/<type>/...
```

| Kind | URI prefix |
|------|------------|
| Agent memory | `viking://user/<profile>/peers/hermes/memories/<subdir>/` |
| KB reports | `viking://resources/reports/<type>/` |

`subdir` ∈ `preferences | entities | events | cases | patterns`.

## Auth

| Item | Source |
|------|--------|
| Endpoint | `OPENVIKING_ENDPOINT` (default `http://127.0.0.1:1933`) |
| API key | `OPENVIKING_API_KEY` or `VIKING_KEY` — **required**, no hardcoded default |
| Headers | `X-API-Key`, `X-OpenViking-Account: default`, `X-OpenViking-User: <profile>`, `X-OpenViking-Actor-Peer: hermes` |

Match `OPENVIKING_API_KEY` to `server.root_api_key` in `web-infra/openviking/ov.conf`.

## Sync script

[`scripts/host/sync_memory_to_ov.py`](../scripts/host/sync_memory_to_ov.py):

1. `GET /health` — abort + alert if down.
2. Per profile: **forget** fixed URI (best-effort) → **create** with full MEMORY.md.
3. Read-back via `fs/ls` parent directory (match `uri` key, not `name`).

OpenViking `content/write` with `mode=create` is **immutable** — same URI twice → 409. Forget-then-create is intentional.

Cron wrapper: [`scripts/host/sync_memory_ov_cron.sh`](../scripts/host/sync_memory_ov_cron.sh) (sources Hermes `.env`, runs `--quiet`).

Schedule: see `memory-sync-ov` in [`cron-catalog.md`](cron-catalog.md).

## Profile → MEMORY.md map

Uses `$HERMES_HOME` (default `~/.hermes`):

| Profile | Path |
|---------|------|
| sarah (default) | `$HERMES_HOME/memories/MEMORY.md` |
| alice / eliza / renee / zoe | `$HERMES_HOME/profiles/<name>/memories/MEMORY.md` |

Extend the map in the script if you add desk profiles that own MEMORY.md.

## Operator tips

- Never commit `ov.conf` or API keys.
- After rotating `root_api_key`, update Hermes `.env` and restart OpenViking.
- Optional: every-4h export of OV memories into a personal vault (host-specific; not required for desk trains).
