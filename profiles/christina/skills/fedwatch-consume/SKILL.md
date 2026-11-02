---
name: fedwatch-consume
description: >-
  christina: consume-only FedWatch daily artifact from existing cron
  <job-id>. Cite-or-miss; never cron-run, re-fetch, or invent
  probability tables. Feeds Rate scenario FedWatch cite column.
---

# FedWatch consume — read-only policy probability artifact

**Owner:** christina · rates  
**Load order:** curve → real → **this skill** → bond-etf → fx → trunk  
**Not:** fetch · patch cron · `hermes cron-run` · invented probabilities  

---

## When to use

- Every session: **read** existing FedWatch daily artifact on host  
- File present and as-of verifiable → fill Rate scenario **FedWatch cite** (**artifact path** only)  
- No file/stale/unverifiable/age flagged → entire `## FedWatch` **`miss` + one-line reason**, **or** only the artifact’s own **`data_delay` qualitative bias**  

---

## Locked rules (hard)

| Rule | Content |
|------|------|
| Cron id | **`<job-id>`** (existing job; christina **does not own**) |
| Mode | **Consume-only** |
| Script | `fedwatch_daily_fetch.py` (ops/Sarah owned; this skill **does not** run) |
| Stale/age | Primary artifact **stale/age flagged** → entire `## FedWatch` **`miss` + reason** **or** only artifact **`data_delay` qualitative bias** (do not silently treat as today) |
| Cite column | Rate scenario **FedWatch cite** = **artifact path** or **`miss`** only |
| Miss | No artifact/bad file/expired unverifiable → entire section `miss` + one-line reason |
| ❌ | `hermes cron-run` · manual re-fetch · schedule edits · invented probability tables/OIS path · **Polymarket/`ZQ=F`/predictmarketcap** filling meeting-by-meeting table as FedWatch primary |

**Host artifact paths (locked · cron `<job-id>`):**

| Prefer | Path |
|--------|------|
| 1 — latest pointer | `~/.hermes/shared/reports/alice/fedwatch/latest.json` |
| 2 — same-day dated | `~/.hermes/shared/reports/alice/fedwatch/YYYY-MM-DD-fedwatch.json` |

Host absolute root often `$HERMES_HOME/shared/reports/alice/fedwatch/`. Read order: **`latest.json` first**, then same-day dated file. Missing/unreadable → **entire `## FedWatch` = `miss` + reason**. Primary **stale/age flagged** → **entire `miss` + reason** **or** only artifact **`data_delay` qualitative bias** (do not silently treat as today; ❌ alternate probability table). ❌ invent probs. ❌ Polymarket/`ZQ=F`/predictmarketcap as FedWatch primary.

---

## Degenerate-source gate

Degenerate-source gate: read `cross_check.citation` from `latest.json` only. `miss`, a missing key, an `a_primary` hike probability at 0% or 100%, or a calibration `range_pct` outside 0–100 → the whole `## FedWatch` section is `miss` plus `degenerate_zq_sole_source`. Do not quote that probability. `primary_only` quotes a non-bound a_primary only and sets the c_sentiment cell to `miss`. `b_backup_zq` is the same `ZQ=F` instrument and is not a second source. Copy `c_sentiment` only from `layers.c_sentiment.summary` when `freshness.layers.c_sentiment` is fresh and the value is not 0 or 100. Otherwise that cell is `miss`. A 15–56% band is `miss`. This artifact has no news layer, so the news cell is `miss`. Do not cron-run, re-fetch, or fill a number to avoid miss. Consume-only cron `<job-id>`.

---

## Output (handoff)

```markdown
## FedWatch (consume-only · <job-id>)
| Item | Value | As-of | Note |
|------|-------|-------|------|
| Artifact | path cite or `miss` | | |
| a_primary | `miss` unless gate passes | | 0%/100% or bad `range_pct` → entire `miss` + `degenerate_zq_sole_source`; ❌ quote |
| c_sentiment | `layers.c_sentiment.summary` or `miss` | | fresh and not 0 or 100; 15–56% band = `miss` |
| news | `miss` | | no news layer |
```

Hand to trunk/curve: Rate scenario **FedWatch cite** column **artifact path or `miss` only** (no Polymarket/`ZQ=F`/predictmarketcap/third-party forecast sites).

**Conflict with Rate scenario (backtest gate):** FW points opposite continuation/scenario → trunk/bond-etf should **`B_WAIT`/no Obs TP/Conf≤L**, do not force TP.

---

## Forbidden

- ❌ cron-run/fetch/patch  
- ❌ Invent meeting-by-meeting probability table  
- ❌ Polymarket/`ZQ=F`/predictmarketcap as FedWatch primary for meeting table  
- ❌ FedWatch cite column anything other than artifact path/`miss`  
- ❌ Mix FW “score” into E5  

---

## Checklist

- [ ] Read-only; no cron-run  
- [ ] path: `…/alice/fedwatch/latest.json` or `YYYY-MM-DD-fedwatch.json`  
- [ ] artifact path cite or explicit `miss` (cite column has no third option)  
- [ ] stale/age → entire `miss`+reason **or** only `data_delay` (from artifact)  
- [ ] as-of/`data_delay`/reason line  
- [ ] Degenerate-source gate: `latest.json` `cross_check.citation` only. `miss`, 0%/100%, missing key, or `range_pct` outside 0–100 → entire `miss` + `degenerate_zq_sole_source`, ❌ quote. `primary_only` → quote non-0/100 a_primary only, c_sentiment cell `miss`. `b_backup_zq` is not a second source. `c_sentiment` only when citation `ok`, fresh, not 0/100; else `miss`. news = `miss`. ❌ cron-run/re-fetch/fill numbers to avoid miss  
- [ ] Hand off Rate scenario cite column  
