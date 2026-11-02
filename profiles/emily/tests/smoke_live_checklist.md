# emily — Live smoke checklist (observation-only)

Adhoc **daily lite** smoke on an **existing Hermes host** (operator CLI is private — not shipped in this public snapshot).
**No secrets · no API keys · no broker · no SimpleFX/IB/Alpaca/RL.**

English OK. Display **"emily · commodities"** ≠ broker Emily.

---

## Preconditions

Use your private host-control wrapper (not in this repo) to:

1. Confirm host reachability
2. Confirm profile `emily` is listed

Do **not** dump `.env`, API keys, or chat IDs. Do **not** run gateway updates or disable the gateway during smoke.

---

## Static first (no SSH required)

```bash
./profiles/emily/tests/run_emily_audit.sh
# optional focused check:
./profiles/emily/tests/check_desk_pack_prompts.sh
```

Expect exit `0`. If desk-pack prompts still use the **old** emily load order, the check fails — fix prompts before live smoke.

**Canonical Keep load (8):**
`sources → world → insight → direction → forecast → signal → puzzle → trunk`
**Out of load:** `commodity-obs-backtest` (Eval/Sat) · Later stubs (`eia-wpsr` / `usda-wasde-psd` / `cftc-cot-disagg`)

---

## Live adhoc — daily lite (observation)

Prefer a **kanban / chat** smoke that asks emily for a **lite scaffold** only — not a full paid-data crawl, not broker paths.

### Option A — chat one-liner (lightest)

Ask emily (via your host chat CLI):

`status in one line — emily commodities, observation only`

Expect a short reply; display name / role should not sound like broker Emily.

### Option B — adhoc lite session ask (still observation)

Ask emily:

```text
Adhoc daily-lite smoke only. Observation only · Not investment advice.
Load Keep-8 only: sources → world → insight → direction → forecast → signal → puzzle → trunk.
Do NOT load commodity-obs-backtest or Later stubs (eia-wpsr / usda-wasde-psd / cftc-cot-disagg).
Do NOT invent inventory/COT/WASDE; miss > invent; no paid APIs.
Reply with: (1) load order echoed (2) whether you would write ## Session summary (3) one miss example.
No inbox write required for this smoke unless paths already exist.
```

### Option C — desk-pack daily train (heavier; only if intentional)

Documented train clock is on Sarah (see `docs/cron-jobs.md`). Only trigger a live cron run if you **intend** a full Wave1∥→Wave2∥→Alice side effect. Use placeholder `<daily-train-id>` from your private host job list — never invent IDs into skills.

---

## Pass criteria (smoke)

- [ ] Host reachable; emily profile reachable
- [ ] Static audit + desk-pack prompt check pass
- [ ] Reply is observation-only (no broker / no order language)
- [ ] Keep-8 load order echoed when asked
- [ ] No secrets printed
