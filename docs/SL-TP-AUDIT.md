# Audited cut-loss and take-profit

Operational risk-control specification. Non-investment advice.

Current sidecar **preferred adopt** policy: **`atr-chandelier-v1`**
(TP1 at 2R, ~1/3 tranche, no fixed TP2, close-based k=4 trail). Omitting
`--policy` on `risk_plan_migrate.py` now defaults to chandelier. Existing
`atr-r-v2` / `atr-zone-v1` OPEN plans may be upgraded with
`--policy atr-chandelier-v1 --adopt ROW_ID` (audited core replace; prior plan
JSON archived under `shared/audit/risk-plan-upgrades/`). Pure `atr-r-v2` remains
available via explicit `--policy atr-r-v2`. Nothing is written to
`~/.hermes/risk_plans.json` until the owner adopts or grandfathers a row. The
live wrapper runs **without** `--shadow` (owner lifted 2026-09-10); pass
`--shadow` only to silence Yahoo/risk-plan Telegram classes.

## Policy

For a verified long fill `F` in the instrument's native trading currency,
calculate Wilder ATR14 `A` from the last fully completed session before the
fill. Intermediate values are not rounded.

```text
R   = 1.5 × A
SL0 = F − R
TP1 = F + 2R = F + 3A
TP2 = F + 4R = F + 6A
```

Long stops round **ceiling-to-tick toward fill** so tick rounding cannot
increase dollar risk. Targets round ceiling-to-tick away from fill. Plan 50%
of the original whole shares for TP1 (rounded down) and all remaining shares
for TP2. A one-share position has no TP1 quantity.

GOOGL fixture check: `F=336.32`, `A=8.65` → `R=12.975` →
`SL0=323.35`, `TP1=362.27`, `TP2=388.22`.

Shadow/adopt-only `atr-zone-v1` adds 1C+2D congestion support for new
proposals only:

- 1C: prefer VPDC over the last 20 completed sessions ending at `atr_session`;
  if volume is missing/zero/unusable, fall back to OTCC. Never blend both.
- 2D: when the zone is valid, `ATR_SL = F - 1.5A`,
  `Zone_SL = Z_lo - 0.5A`, and `SL_final = min(ATR_SL, Zone_SL)` before final
  stop rounding. `TP1` and `TP2` are then recomputed from
  `R_eff = F - SL_final` as `F + 2R_eff` and `F + 4R_eff`.
- If `F - SL_raw > 2.5A` before final rounding, raise/reject rather than
  silently capping into congestion. On migrate propose, `R_MAX_EXCEEDED`
  falls back to pure `atr-r-v2` (same as other zone rejects).
- Ambiguous equal mass+width clusters (`AMBIGUOUS_CLUSTER`), no-cluster, or
  zone-above-fill fall back to pure `atr-r-v2` geometry, with zone status
  recorded in the proposal only.

The daily T&M pack's `Entry = close + 0.5A` levels are proposals for a new
entry. Their absolute `stop_loss` and `take_profit` values must not overwrite
an already-filled position's plan.

NAV advisory gates (file-only, GBP book vs £50,000 default): lot 0.5%,
book 3%, sector 1.5%, stress-gap 5%. They never place orders.

## Lifecycle

1. At entry, freeze `SL0`, `TP1`, `TP2`, quantities, source OHLC, ATR session,
   policy version `atr-r-v2`, and calculation hashes in
   `~/.hermes/risk_plans.json`.
2. Before a confirmed TP1 SELL, the active stop stays at `SL0` (or a later
   explicit trail) and may never be lowered.
3. A touch or nightly alert does not change state. Only a journal SELL with
   `Status=CLOSED` and `PLAN_ROW_ID=` advances the state.
4. After confirmed TP1 execution, **keep SL0 / the trailed stop**. Do **not**
   auto-raise to fill (no automatic breakeven). Remaining shares stay planned
   for TP2.
5. Manual trailing requires an append-only `TRAIL_SL` event with old/new
   level, actor, reason, and timestamp. The nightly script never trails or
   writes the journal. Watcher `TRAIL_SL` comes from those events, not Notes.
6. New BUY lots receive separate plans and separate watch rows. Remaining is
   that lot's BUY minus `Status=CLOSED` sells (`PLAN_ROW_ID` else FIFO).
   Levels are never silently averaged. Watch uses `PlanView` (`active_sl`,
   `tp1`, `tp2`), never raw `plan.levels` after rebase/trail.
7. A `REBASE_SPLIT` event restates shares and levels; unrebased Yahoo splits
   otherwise fail closed.

Broker protective stops (if any) are separate from this nightly close alert.

## Currency contract

- USD holdings: fill is `Price USD`, with `Total USD / Shares` as a validated
  fallback. `Price` is the GBP book amount and must not be labelled USD.
- GBP/LSE holdings: fill is `Price`. Yahoo `GBp`/`GBX` bars are normalized by
  `0.01`; ambiguous units block comparison.
- Entry, Yahoo OHLC, SL, and TP must all be in the same currency.
- The default GBP/USD reporting rate is never used for breach comparisons.

## Market evidence

`market_data.py` requests Yahoo daily data with `auto_adjust=False` and
corporate actions enabled. Lookback is about 400 calendar days for ATR.
Weekends and configured holidays return `EXCHANGE_CLOSED` with no fetch.

A price is eligible for SL/TP comparison only when:

- ticker / Yahoo symbol and expected market session match;
- OHLC is complete and internally valid;
- normalized Yahoo currency matches the plan;
- no unrebased split exists after plan creation (a stored rebase clears this);
- a same-date T&M close, when available, differs by no more than 1%.

`GAP_THROUGH_SL` (session open ≤ active SL) is observational. It does not
invalidate the bar. The journal must still contain the actual execution.

The raw metadata, normalized bars, retrieval time, and verdict are cached
under `~/.hermes/shared/audit/market-data/`. Missing or invalid evidence is
`N/A`, never a safe pass.

## Nightly signals

The official 23:00 decision uses regular-session close:

- `CUT_LOSS_CLOSE`: `close <= active_sl`
- `TP1_CLOSE`: before confirmed TP1, `close >= TP1`
- `TP2_CLOSE`: remaining shares exist and `close >= TP2`

Equality triggers. Distances are:

```text
Dist SL     = (close − active_sl) / close × 100
Dist target = (target − close) / close × 100
```

Daily high/low provides file-only observations:

- low touches SL but close recovers: `SL_INTRADAY_TOUCH`
- high touches a TP but close falls back: `TP_INTRADAY_TOUCH`
- both SL and TP touched: `AMBIGUOUS_INTRADAY`

Telegram policy (stdout attention bullets only):

| Class | Telegram |
| --- | --- |
| Close-confirmed journal SL/TP (not `--shadow` PLAN) | yes |
| Gap through SL | yes, unless `--shadow` |
| Missing SL / lot conflict | yes |
| `EXCHANGE_CLOSED` | file only |
| Kelly / `PARTIAL_EXIT_ACK` / 22:15 score+time / E5 / NAV / intraday | file only |
| `RISK_PLAN_MISSING` | file only |
| `PROPOSED_TRAIL` / `SHADOW_CHANDELIER_TRAIL` / `TRAIL_EXIT_CLOSE` / chandelier propose skips | file only |

Time-stop overlay: fires only when approximate trading days ≥ 10 **and**
`MFE_close < 1R`, and is **latched once** per OPEN cycle key
`TICKER|entry_date` (`~/.hermes/shared/audit/time-stop-latch.json`). Missing
MFE or unparseable entry date fails closed (no time-stop). Unreadable latch
also fails closed (no re-emit).

- **Nightly `position_watch`:** computes `MFE_close` from validated plan bars
  when `risk_per_share` is present; file-only flag.
- **22:15 `exit_signal_checker`:** time-stop only if `--mfe-json` supplies
  per-ticker `MFE_close` in R; without it, score decay still runs but
  **time-stop does not**. Latch still persists even under `--dry-run`.

Score decay (`tm_score < 50`) is unchanged.

Alert-state read/write failure **suppresses** Telegram (fail closed). Do not
re-send the whole set.

The script never infers execution order, fill price, or P&L from a daily
candle.

## Sidecar and migration

The journal remains the execution ledger. The sidecar is keyed by entry
`RowID` and contains immutable inputs/levels plus append-only events.

Generate proposals without writing:

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py
```

Adopt the new ATR policy for a reviewed row — requires broker attestation:

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py \
  --adopt ROW_ID --broker-sl SL0_PRICE
# or: --broker-sl-none
```

Adopt / upgrade to **chandelier** (migrate default) for a reviewed row — prints
an S0 ticket (`SL0` / `TP1` / share split) on stderr. Requires broker
attestation. Omitting `--policy` proposes **`atr-chandelier-v1`**. Existing
CREATED-only `atr-r-v2` / `atr-zone-v1` plans upgrade via the same `--adopt`
(audited core replace + archive under `shared/audit/risk-plan-upgrades/`).
Plans with post-CREATED lifecycle events (`TRAIL_SL` / sells / rebase) are
**refused** for core replace.

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py \
  --adopt ROW_ID --broker-sl SL0_PRICE
# equivalent explicit:
#   --policy atr-chandelier-v1 --adopt ROW_ID --broker-sl SL0_PRICE
# or explicit no resting broker stop:
#   --broker-sl-none
```

Force legacy geometry with `--policy atr-r-v2`. Zone widen (`atr-zone-v1`) is
**never** the default — use `--policy atr-zone-v1` explicitly.

**Residual ops (GOOGL 2026-09-16):** sidecar plan is `atr-chandelier-v1`
SL0=`324.15` / TP1=`360.68`. Journal row was aligned the same day to those
levels (TP2 unused placeholder = TP1). **Broker** static stop must still be
confirmed at SL0 `324.15` (Hermes does not place broker orders). Nightly
`PROPOSED_TRAIL` stays file-only until owner `--trail`.

After the owner amends the broker static stop to match a nightly
`PROPOSED_TRAIL`, append the audited event:

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py \
  --trail ROW_ID --session YYYY-MM-DD --broker-sl NEW_SL
```

Telegram SL breach / gap-through-SL fire only for **adopted PLAN** levels (not
`JOURNAL_ONLY` unaudited journal SL). Journal past-TP alerts are unchanged.

Preserve valid current journal geometry:

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py \
  --grandfather ROW_ID --broker-sl JOURNAL_SL
```

Preserve a reviewed legacy plan whose stop was already raised above fill:

```bash
python3 ~/.hermes/scripts/risk_plan_migrate.py \
  --grandfather-trailed ROW_ID \
  --original-sl 60.50 \
  --trail-sl 61.00 \
  --trail-reason "capital-protected after partial exits" \
  --broker-sl 61.00
```

Changing a live SL/TP changes risk. Migration therefore never chooses or
writes a plan without an explicit row-level decision. A legacy trailing stop
above fill, such as TST1.L, needs explicit trail history rather than automatic
grandfathering.

## Audit gates

- Reproduce Wilder ATR14 from at least 15 fixture bars.
- Verify `atr-r-v2` geometry: `R=1.5×ATR14`, `SL0 < fill < TP1 < TP2`,
  tick rounding, and share allocation.
- After TP1, active SL is still SL0 or an explicit trail — not fill.
- Reconcile risk-plan remaining shares to journal buy minus **CLOSED** sells.
- Reject duplicate events, rewritten event history, changed immutable core,
  unattributed partial sells, oversells, and unexpected partial quantities.
- Suppress breach claims on missing/stale/wrong-currency/split-ambiguous data.
- Weekend/holiday is `EXCHANGE_CLOSED`, not a Yahoo FAIL.
- Reruns for one session must be deterministic; unreadable alert state sends
  nothing.

The wrapper no longer passes `--shadow`: Yahoo/risk-plan/inversion/gap classes
Telegram when unique (same dedupe as journal SL/TP). Trail compare, Kelly, ACK,
NAV, and 22:15 score+time stay file-only. Re-run with `--shadow` to silence the
Yahoo/risk-plan Telegram classes again.
Weekends are `EXCHANGE_CLOSED` with no fetch. A weekday holiday calendar is
not configured yet; a missing holiday bar is `EXPECTED_SESSION_MISSING`, not
`EXCHANGE_CLOSED`. Sector NAV (1.5%) stays inert until lots carry a sector.

Run the deterministic audit suite:

```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
```
