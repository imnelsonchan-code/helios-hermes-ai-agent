# Cron catalog (semantic — no live UUIDs)

Create these jobs on **your** Hermes host. Schedules are UTC unless noted.
Machine-readable twin: [`fixtures/cron-catalog.yaml`](../fixtures/cron-catalog.yaml).

**Rules**

- Store investment trains on the **default / Sarah** cron store (MAIN), not per-profile cron files.
- Prefer **one** daily Desk Pack train and **one** Sunday weekly train (absorbed legs stay paused/absent).
- Never paste another host’s 12-hex job IDs into skills or SOUL files.

## Timeline (weekday)

```text
05:00  desk-rank-nous
20:30  social-watcher          (also Sat)
21:15  fedwatch-fetch
21:25  desk-pack-daily         (W1∥ → W2∥ → Alice → T&M+exit)
23:00  position-risk-train
23:30  wow-bracket-70          (optional)
23:35  coverage-watchdog
23:59  scoring-eval-daily
```

## Timeline (weekend)

```text
Sat 11:00  coverage-weekly
Sat 11:15  zoe-tracker
Sat 12:00  saturday-self-review-s1
Sat 19:00  weight-health       (first Saturday of month)
Sun 08:00  kanban-archive
Sun 09:00  form4-monitor
Sun 12:00  desk-pack-weekly    (5 cars serial)
Sun 18:00  journal-integrity
Sun 18:30  valuation-wow
Sun 19:00  scoring-ic-weekly
```

## Always-on loops

| Semantic id | Schedule | Kind | Action |
|-------------|----------|------|--------|
| `kanban-blocked-monitor` | `*/5 * * * *` | no_agent | Alert on newly blocked Kanban tasks |
| `inbox-to-wiki` | `*/30 * * * *` | no_agent | Copy new inbox media to wiki (optional) |
| `portal-sync-www` | `*/30 * * * *` | no_agent | `sync_reports_www.sh` |
| `memory-sync-ov` | `*/30 * * * *` | no_agent | `sync_memory_ov_cron.sh` |
| `weight-config-watchdog` | `*/30 * * * *` | no_agent | Restore Renee weight JSON if corrupt |

## Investment trains (agent)

| Semantic id | Schedule | Profile / chain | Notes |
|-------------|----------|-----------------|-------|
| `social-watcher` | `30 20 * * 1-6` | Sarah → Alice | Snapshot only; no Zoe; see `docs/cron-jobs.md` |
| `desk-pack-daily` | `25 21 * * 1-5` | Wave1 christina∥renee → Wave2 emily∥eliza → Alice | Prompts: `desk_pack_daily_train_prompts.py`; terminal `daily_tm_with_exits.sh` |
| `desk-pack-weekly` | `0 12 * * 0` | christina → emily → T&M → width → Alice | Prompts: `desk_pack_weekly_prompts.py` |
| `saturday-self-review-s1` | `0 12 * * 6` | Serial self-review → Alice portal | Prompts: `saturday_self_review_prompts.py` |
| `fedwatch-fetch` | `15 21 * * 1-5` | no_agent / script | Christina **consume-only** afterward |
| `a08-monday-followup` | `15 10 * * 1` | Eliza | Follow Sunday width names |
| `form4-monitor` | `0 9 * * 0` | Eliza | Sunday Form 4 |
| `sec-monitor-weekday` | `0 14 * * 1-5` | Eliza | Often **paused**; keep job optional |

## Scoring / risk / ops scripts

| Semantic id | Schedule | Script |
|-------------|----------|--------|
| `desk-rank-nous` | `0 5 * * *` | Host Nous free selection / pin (if you use free routes) |
| `position-risk-train` | `0 23 * * 1-5` | Kelly → drawdown → `position_watch` |
| `scoring-eval-daily` | `59 23 * * 1-5` | `scoring_eval_daily.py` |
| `scoring-ic-weekly` | `0 19 * * 0` | IC then `scoring_eval_weekly.py` |
| `valuation-wow` | `30 18 * * 0` | `validate_wow_diff.sh` |
| `journal-integrity` | `0 18 * * 0` | Journal / P&L integrity |
| `zoe-tracker` | `15 11 * * 6` | `zoe_tracker.sh` |
| `coverage-watchdog` | `35 23 * * 1-5` | Desk coverage WD |
| `coverage-weekly` | `0 11 * * 6` | Weekly coverage |

## Workflow YAML (documentation)

Cadence labels (not live cron): [`profiles/desk/workflows/`](../profiles/desk/workflows/).

## Related

- Concept notes: [`cron-jobs.md`](cron-jobs.md)  
- Desk contracts: [`desk-artifact-contracts.md`](desk-artifact-contracts.md)  
- Profiles / revisers: [`PROFILES.md`](PROFILES.md)
