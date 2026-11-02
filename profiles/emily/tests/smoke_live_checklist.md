# emily — Live smoke checklist (observation-only)

Adhoc **daily lite** smoke on the Hermes host via `hermes-ctl`.
**No secrets · no API keys · no broker · no SimpleFX/IB/Alpaca/RL.**

English or bilingual OK. Display **"emily · commodities"** ≠ broker Emily.

---

## Preconditions

```bash
# From repo root — host from gitignored .env (HERMES_HOST)
./scripts/hermes-ctl.sh ping
./scripts/hermes-ctl.sh profiles # expect emily listed
```

Do **not** dump `.env`, API keys, or chat IDs. Do **not** `hermes update` or disable gateway.

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

```bash
./scripts/hermes-ctl.sh chat emily "status in one line — emily commodities, observation only"
```

Expect a short reply; display name / role should not sound like broker Emily.

### Option B — adhoc lite session ask (still observation)

```bash
./scripts/hermes-ctl.sh chat emily "$(cat <<'EOF'
Adhoc daily-lite smoke only. Observation only · Not investment advice.
Load Keep-8 only: sources → world → insight → direction → forecast → signal → puzzle → trunk.
Do NOT load commodity-obs-backtest or Later stubs (eia-wpsr / usda-wasde-psd / cftc-cot-disagg).
Do NOT invent inventory/COT/WASDE; miss > invent; no paid APIs.
Reply with: (1) load order echoed (2) whether you would write ## Session summary (3) one miss example.
No inbox write required for this smoke unless paths already exist.
EOF
)"
```

### Option C — desk-pack daily train (heavier; only if intentional)

Documented train clock is on Sarah (see `docs/cron-jobs.md`). Only `cron-run` if you **intend** a full Wave1∥→Wave2∥→Alice side effect:

```bash
./scripts/hermes-ctl.sh cron-status
# ./scripts/hermes-ctl.sh cron-run <daily-train-id> # only when intentional
```

Do **not** invent cron IDs in skills / stubs; copy IDs from live `jobs` / docs when needed.

---

## Pass criteria (smoke)

- [ ] `ping` OK; emily profile reachable
- [ ] Static audit + desk-pack prompt check pass
- [ ] Chat / adhoc reply echoes **8-skill** load (insight→direction→forecast present; obs-backtest **not** in load)
- [ ] No invent inventory / COT / WASDE; miss language OK
- [ ] No paid-API / broker / SimpleFX / IB / Alpaca / RL language
- [ ] If a revised file is produced: `inbox/commodities-session/YYYY-MM-DD-*-revised.md` (train path)

---

## Saturday note (obs-backtest)

Sat Part C may run **`commodity-obs-backtest`** (Eval/Sat only). Output:

`shared/reports/emily/self-review/YYYY-WW-emily-obs-backtest.md`

❌ PnL / orders / SimpleFX / IB / Alpaca / RL / ARIMA. ❌ insert into daily Keep load.
