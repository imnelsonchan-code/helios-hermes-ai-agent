# Desk model failover (concept)

Operational design for **narrative desk profiles** when the primary LLM route is unavailable. This document describes behavior only — no vendor product names, no live host IDs.

## Scope

| In chain | Out of chain |
|----------|----------------|
| Orchestrator + session authors (macro, T&M, value, commodities, rates) | IC gate profile (stays on its dedicated Pro route) |
| Free-tier backup models on the desk | External decision sidecars (separate API keys) |

**Context overflow is not failover.** Prompt or session too large → shorten load, archive bloated cron sessions, or pick a model with honest context limits. Walking backup models does not fix an oversized prompt.

## Target chain (per profile)

Each narrative profile keeps its **own** ledger — one profile failing does not rewrite others.

```text
1. Primary gateway route (best-free style picker)
2. Strongest healthy free backup (sticky pin for this profile)
3. Other healthy free backups (random walk among remainder)
4. One retry of primary (first sticky episode per calendar day only)
5a. Retry succeeds → pin primary immediately (mid-day re-pin flag)
5b. Retry fails → stay on backup until morning restore
6. After mid-day re-pin: primary dies again → sticky backup; no second retry until morning job
```

Morning health job: refresh rank list + backup ordering, **probe primary**, restore sticky profiles only when probe OK. Clear per-profile retry / re-pin locks so the new day gets a fresh retry budget even if restore is skipped.

## Dead vs soft (backup layer)

| Symptom class | Walk this request | Sticky rewrite primary? | Long denylist |
|---------------|-------------------|-------------------------|---------------|
| Rate limit / timeout / 5xx on backup id | Skip id for this walk | No | No |
| Missing model / catalog hard-dead | Skip + optional re-pin | Maybe | Yes (e.g. 72h) |
| Primary gateway layer dead (incl. rate limit after internal upstream walk) | Pin profile to strongest backup | Yes (this profile only) | No on primary layer |

## Sticky pin and restore

| Event | Action |
|-------|--------|
| Primary layer dead | Sticky-pin **that profile** to strongest healthy free backup; continue request; notify operator |
| Strongest backup unusable | Random among remaining healthy backups |
| All backups exhausted (retry budget left) | Retry primary once |
| Primary retry OK | Pin primary; set mid-day re-pin used |
| Primary retry fail | Lock until morning; stay on backup |
| Primary dies after mid-day re-pin | Sticky backup; no retry until morning |
| Morning probe OK | Restore sticky / forced profiles to primary |
| Morning probe fail | Keep backup + skipped-restore notice |
| Permanent hold off primary | Policy flag disables morning restore and mid-day retry |

## Rules summary

- Primary first for every narrative profile except the IC gate.
- Primary layer failure (including rate limits) → sticky backup for **that profile only**.
- Backup rate limits → walk only; no sticky rewrite; no long denylist.
- At most **one** primary retry per profile per day (first sticky episode).
- Morning restore is **probe-gated**.
- IC gate never pinned to free backup chain.

## Related repo docs

- Scoring and sleeves: [`SCORING-ENHANCEMENTS.md`](SCORING-ENHANCEMENTS.md)
- Artifact contracts: [`desk-artifact-contracts.md`](desk-artifact-contracts.md)
- Profiles: [`PROFILES.md`](PROFILES.md)
