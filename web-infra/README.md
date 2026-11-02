# Web infra (Docker templates)

Sanitized Compose stacks for a Hermes finance-desk host. Copy each folder to
`$HOME/web-infra/<name>/` (or keep them in-repo and point volumes accordingly).

**Never commit real `.env`, tokens, or `ov.conf` with live keys.**

| Service | Default bind | Role |
|---------|--------------|------|
| [`reports-server/`](reports-server/) | `:8080` | Nginx portal for inbox reports |
| [`openviking/`](openviking/) | `127.0.0.1:1933` | Memory + KB (OpenViking) |
| [`searxng/`](searxng/) | `127.0.0.1:8888` | Web search for agents |
| [`browserless/`](browserless/) | `127.0.0.1:9222` | Headless Chrome |
| [`crawl4ai/`](crawl4ai/) | `127.0.0.1:11235` | Crawl / extract API |
| [`omniroute/`](omniroute/) | `:20128–20129,:20132` | Optional free-model router (OmniRoute) |

## Bring-up order

```bash
# From each service directory (after filling secrets):
docker compose up -d
docker compose ps
```

Suggested order: **openviking → searxng → browserless → crawl4ai → reports-server → omniroute (optional)**.

Wire Hermes / desk scripts via [`.env.example`](../.env.example) and [`docs/INSTALL.md`](../docs/INSTALL.md).
