# Hermes finance desk (public)

Research and operations tooling for a multi-specialist **investment desk** running on Hermes agents: trend/momentum (P-TM), value/width (P-VAL), rates, commodities, and macro integration. This repository is a **scrubbed, English-facing** snapshot of host scripts, profile docs, and desk contracts suitable for public review.

**Not investment advice.** Scripts read journals and market data; they do not place broker orders unless explicitly wired on a private host.

## Audience / prerequisites

- **Requires an existing Hermes host** if you want to apply profiles or run host scripts.
- This repo **does not install Hermes**, OpenViking, Telegram, or model providers.
- Clone → read docs / run unit tests works offline. Live apply / cron / chat stay on your private ops tooling.

## What is included vs private

| Included here | Stays private |
|---------------|---------------|
| Desk docs, SOUL/skills drafts, workflow YAML | Host-control CLI, apply-to-live scripts |
| `scripts/host/` finance tooling + prompt SSOT | Live cron UUIDs, `.env`, API keys, chat IDs |
| Synthetic pytest fixtures + profile audits | Non-finance skills, live holdings, ops runbooks |

## Layout

| Path | Purpose |
|------|---------|
| `docs/` | Desk contracts, scoring overlays, SL/TP audit, profiles, glossary, failover concept |
| `profiles/` | Agent SOUL drafts, skills checklists, desk workflow YAML (documentation) |
| `scripts/host/` | Maintained Python/shell pool (T&M generator, position watch, risk plan, desk pack prompts) |
| `scripts/tests/` | Unit tests (synthetic fixtures only in named test modules) |

## Key docs

- [`docs/PROFILES.md`](docs/PROFILES.md) — who drafts and who revises after IC gate
- [`docs/desk-artifact-contracts.md`](docs/desk-artifact-contracts.md) — artifact IDs and E5 rules
- [`docs/SCORING-ENHANCEMENTS.md`](docs/SCORING-ENHANCEMENTS.md) — eval overlays vs live engines
- [`docs/SL-TP-AUDIT.md`](docs/SL-TP-AUDIT.md) — stop/target audit and Telegram policy
- [`docs/failover-concept.md`](docs/failover-concept.md) — per-profile model failover (vendor-neutral)
- [`docs/glossary.md`](docs/glossary.md) — desk terminology
- [`docs/APPLY.md`](docs/APPLY.md) — short apply *hints* for an existing host (no bootstrap)

## Architecture (one flow)

```text
Desk Pack cadence → specialist Draft → Zoe IC gate → owner *-revised.md → inbox / portal
```

W-D1 daily / Sunday weekly / Saturday S1 — see `docs/PROFILES.md`. E5: never blend P-TM and P-VAL scores.

## Tests

Optional venv with pytest:

```bash
python3 -m pip install pytest   # if needed
python3 -m pytest scripts/tests -q
```

Profile audits (static, no network):

```bash
./scripts/run-equity-sleeve-audits.sh
./profiles/desk/tests/run_desk_audit.sh
```

Fixtures use synthetic symbols `TST1.L`, `ACME`, `BETA` and note `Synthetic buy` where applicable.

## Deploy (high level, existing Hermes only)

1. Copy or sync `scripts/host/*` into your host script pool.
2. Apply profile SOUL/skills with your private apply path (`docs/APPLY.md` is hints only).
3. Keep live cron IDs and secrets on the host — never commit them here.

## License

MIT — see [`LICENSE`](LICENSE).
