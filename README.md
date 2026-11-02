# Hermes finance desk (public)

Research and operations tooling for a multi-specialist **investment desk** running on Hermes agents: trend/momentum (P-TM), value/width (P-VAL), rates, commodities, and macro integration. This repository is a **scrubbed, English-facing** snapshot of host scripts, profile docs, and desk contracts suitable for public review.

**Not investment advice.** Scripts read journals and market data; they do not place broker orders unless explicitly wired on a private host.

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

## Tests

From repo root (optional venv with pytest):

```bash
python3 -m pytest scripts/tests/test_position_watch.py scripts/tests/test_portfolio_tracker.py \
  scripts/tests/test_exit_signal_checker.py scripts/tests/test_market_data.py \
  scripts/tests/test_tm_snapshot_verify.py scripts/tests/test_risk_plan.py \
  scripts/tests/test_risk_plan_migrate.py -q
```

Fixtures use synthetic symbols `TST1.L`, `ACME`, `BETA` and note `Synthetic buy` where applicable.

## License

MIT — see [`LICENSE`](LICENSE).
