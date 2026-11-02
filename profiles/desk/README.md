# desk — documentation workflows (equity cross-cutting)

**Docs / refine sketches only.** These YAMLs are **not** live Hermes cron and do not auto-execute on the host.

Shared artifact IDs, E5 no-blend rules, and portal path contracts live in:

- [`docs/desk-artifact-contracts.md`](../../docs/desk-artifact-contracts.md)

Workflow sketches under `workflows/`:

| File | Cadence (label) |
|------|-----------------|
| `desk-pack-daily.yaml` | Mon–Fri Desk Pack (W-D1) |
| `desk-pack-weekly.yaml` | Sunday full Desk Pack |
| `desk-pack-saturday.yaml` | Saturday S1 self-review |

Zoe challenge IDs **Z-XC-01…08** are documented in `profiles/zoe/SOUL.md` / `skills-checklist.md`.

---

## Audits

Desk smoke (contracts + workflow markers + Zoe Z-XC):

```bash
./profiles/desk/tests/run_desk_audit.sh
```

Equity-sleeve wrapper (eliza + renee + desk):

```bash
./scripts/run-equity-sleeve-audits.sh
```

Exit `0` = PASS · non-zero = FAIL. No network / no secrets.
