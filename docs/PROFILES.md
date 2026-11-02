# Profiles and who revises

Cron starts as **Sarah** (`default`). Specialists run via Kanban. **E5:** Eliza screens on cheapness / quality; Renee screens on trend / momentum. Each sleeve scores its own selected names: P-VAL publishes `valuation_score`, while P-TM publishes `tm_score`. Same ticker may appear in both packs (**WARN only**) — never mix or blend the two scoring systems, checks, ranks, breakdowns, or exit rules.

```text
Draft → Zoe challenge → owner revises (*revised.md) → inbox / web
```

| Profile | Role | Drafts | Revises after Zoe |
|---------|------|--------|-------------------|
| **Sarah** | Orchestrator | — | — (cron / kanban only) |
| **Alice** | Macro, integrate, desk overall | Close / deep-dive / Sat overall | **Market close**, deep dive, Saturday overall (not daily T&M) |
| **emily** | Commodities session author (display: emily · commodities) | Daily / weekly commodity session | **Own** `inbox/commodities-session/*-revised.md` |
| **christina** | Rates session author (display: christina · rates) | Daily / weekly rates session | **Own** `inbox/rates-session/*-revised.md` |
| **Renee** | P-TM scores + narrative | Daily T&M draft, weekly T&M | **Daily T&M** + **Weekly T&M** |
| **Eliza** | P-VAL width / SEC / value session | Width, filings, daily value-session | **Daily value-session** + **Weekly valuation width** |
| **Zoe** | IC gate | Challenges only | Does not write `*revised.md` |

**Naming firewall:** profile slug **`emily`** (commodities session) ≠ historical broker **Emily** (M7 execution, **decommissioned 2026-07-17**). Keep slug `emily` — inbox / cron paths depend on it. Broker Emily is historical only; this profile is **not** her successor.

**default vs sarah (ops):** Live cron / gateway home is Hermes **`default`** (`~/.hermes/config.yaml` + `profiles/default/SOUL.md`; **no** per-profile `config.yaml` under `default` — intentional). Profile **`sarah`** is a stopped sibling with shared Telegram risk; editing `sarah/config.yaml` does **not** change live cron. See [`HERMES-CONTROL.md`](HERMES-CONTROL.md) when present on your host.

**Clone hygiene:** Never leave emily / christina `config.yaml` pointing at Eliza `environment_hint` or another profile's memory DB. Host fix: `scripts/host/patch_clone_config_identity.py` (christina drops memory-store plugin under NO_DB).

**Desk Pack (LOCKED B+Reuse+S1):** five portal reports per cadence — emily · christina · renee · eliza · Alice overall. Each session requires `## Session summary`. Alice overall cites the four revised paths + news/social.

- **W-D1 daily:** Wave1 christina ∥ renee → Wave2 emily ∥ eliza → Alice overall.
- **Sun 12:00:** one full Desk Pack weekly job (christina → emily → weekly T&M → Eliza width → Alice overall). Width and Alice clocks may be paused on some hosts.
- **Sat S1:** portal = Alice overall (`weekly-performance/`) only.

Daily SEC cron may be **paused** (job kept). Eliza still owns filings conceptually; Sunday Form 4 stays.

Daily T&M: Renee `daily_trend_momentum.py` → Zoe → **Renee** revises (no re-score). Engine/methodology changes wait for Renee's Sunday weekly revise **or** a daily generator card.

Weekly T&M: Renee `weekly_indicator_update` + `verify_weekly_adx` + `weekly_report_gen` (Risk% + ATR14%) → Zoe → **Renee** revise. Do not copy that generator onto the daily job. Details: [`SAT-SUN-FIXES.md`](SAT-SUN-FIXES.md#tm-generators-live-2026-09-06) when present.

Tracker job checks that a same-date `*revised.md` exists. Script pool: [`../scripts/host/`](../scripts/host/).

Routine social snapshots (`social-watch/*-snapshot.md`) are a monitoring feed, not formal portal reports — no Zoe gate. Alice owns depth scan there (tier-1 social leaders + capped forums). Market-close / desk overall is **cite-only** for social — do not re-crawl. The close wrap also carries Alice **financial news analysis** (ledger + themes / bull-bear), **news vs social comments**, and **inline Sources**; template skill: `profiles/alice/skills/market-close-news-social`. Inbox path `daily-social/` is the **market-close companion** deliverable (coverage SSOT), **not** the social-watch snapshot.

Cron jobs start on the **clock**. Inside one report, Kanban `parents=` runs the next card after the previous finishes. Sat/Sun applied patches: [`SAT-SUN-FIXES.md`](SAT-SUN-FIXES.md). Web: reports portal on the Hermes host (`/reports/`).
