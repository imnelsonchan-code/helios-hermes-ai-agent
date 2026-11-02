# OmniRoute (Hermes web-infra)

Self-hosted OpenAI-compatible gateway under `~/web-infra/omniroute/` on the Hermes host.

## Layout (folders only — no named volumes)

```text
~/web-infra/omniroute/
  docker-compose.yml
  .env                 # host secrets (not in git)
  data/                # OmniRoute SQLite + encrypted keys
  redis-data/          # Redis persistence
```

## Deploy from this repo

```bash
./scripts/apply-omniroute.sh --dry-run
./scripts/apply-omniroute.sh
```

The apply script:

1. Scp’s compose + `.env.example` + README to `$HERMES_HOST:~/web-infra/omniroute/`
2. Creates `data/` and `redis-data/`
3. Creates `.env` from the example if missing, fills empty `JWT_SECRET` / `API_KEY_SECRET` / `INITIAL_PASSWORD`, `chmod 600 .env`
4. Runs `docker compose up -d`

It does **not** write Hermes `model.default` / `model.provider`. Secrets are never printed — read `INITIAL_PASSWORD` via SSH from the host `.env` if needed.

## Access

| Surface | URL | Notes |
|---------|-----|-------|
| Dashboard | `http://<hermes-lan-ip>:20128` | Internal network |
| OpenAI API | `http://<hermes-lan-ip>:20128/v1` (or `127.0.0.1` on host) | `REQUIRE_API_KEY=true` |

Other servers on the internal network may call the API. No public WAN proxy in v1.

## Free LLMs + routing

1. Log into the dashboard with `INITIAL_PASSWORD` (from host `~/web-infra/omniroute/.env`).
2. Enable free / keyless providers (no DeepSeek; no Nous OAuth — Hermes owns Nous).
3. Opt in to **Radar** feed sync (built-in refresh; no extra host cron).
4. Mint a **client API key** for Hermes.
5. Point narrative profiles at OmniRoute with model **`auto/best-free`** via `hermes model` / setup.

| Mode | Meaning |
|------|---------|
| `auto/best-free` (desk default) | One best free LLM per request; internal failover |
| `fusion` (optional combo) | Multi-model panel + judge synthesis — not Hermes primary |

Hermes outer backup: Nous `:free` via `fallback_providers`. Zoe stays DeepSeek Pro only.

## Image pin

Compose pins `diegosouzapw/omniroute:3.8.51`. Bump the tag in git when you want a newer shipped free-catalog baseline. If amd64 `:3.8.51` looks wrong on Docker Hub, pin by digest (see upstream OmniRoute docker issues).

## Smoke

On the Hermes host:

```bash
cd ~/web-infra/omniroute && docker compose ps
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:20128/
# after minting a key:
curl -fsS http://127.0.0.1:20128/v1/models -H "Authorization: Bearer $OMNIROUTE_API_KEY" | head
```

## Non-goals

- Not installed via SOUL `apply-to-hermes.sh`
- No named Docker volumes
- No DeepSeek / Nous credentials inside OmniRoute
- No fusion as default Hermes primary
