# Take-profit redesign proposal

Hong Kong Chinese: [`TP-PROPOSAL.zh-HK.md`](TP-PROPOSAL.zh-HK.md)

Operational risk-control specification. Non-investment advice.

**Status: atr-chandelier-v1 is the preferred adopt policy.** `risk_plan_migrate.py`
defaults to chandelier; existing `atr-r-v2` OPEN rows upgrade via `--adopt`
(audited core replace). `atr-r-v2` remains available with explicit `--policy`.
Code for chandelier + excursion ledger is in-repo (propose / file-only trail
flags; legacy `SHADOW_CHANDELIER_COMPARE` on `NO_RAISE` for non-chandelier
plans). The position-watch wrapper is **live** (no `--shadow`) as of
2026-09-10. Row-level adopt still requires an explicit owner decision per
[`SL-TP-AUDIT.md`](SL-TP-AUDIT.md).

Prepared in response to: *review the take-profit method; stop computing it from
entry price only.*

## Summary

The complaint is correct, but the strongest reason is not the obvious one. The
entry price is a defensible anchor. The two real defects are that **the current
policy's TP2 and the system's own time stop cannot both be satisfied**, and that
**a fixed 4R cap truncates the exact tail a momentum book earns from**.

Three findings drive the recommendation:

1. `TP2 = F + 4R = F + 6·ATR14` is effectively unreachable inside the ~10-session
   time stop (~0.8% touch probability; ~60 sessions to become plausible).
2. The entry-anchored geometry is **expectancy-neutral by construction**. The
   current 50/50 split at 2R/4R has an expectancy of exactly `0.000R` under a
   driftless walk. All edge must come from the T&M screen's drift; the level
   geometry contributes none.
3. The existing audit machinery already supports the fix. A close-based trailing
   stop reduces to a `TRAIL_SL` event, which is already append-only, monotone,
   and hash-chained.

Recommended shape: keep a **smaller** entry-anchored first tranche (~1/3 at 2R),
**delete the fixed TP2** and replace it with a close-based Chandelier trail at
`k = 4.0` emitted as proposed `TRAIL_SL` events, and build the excursion ledger
first so later calibration can revisit these defaults.

## Diagnosis

### The two rules contradict each other

With `ATR ≈ 1.4 × daily σ` (Gaussian range gives `σ·√(8/π) ≈ 1.60σ`; true range
adds gaps, empirical ratios run 1.2–1.6), reflection-principle touch
probabilities are:

| Horizon | `TP1 = 3·ATR` | `TP2 = 6·ATR` |
| --- | --- | --- |
| 10 sessions | ~18% | ~0.8% |
| 60 sessions | ~59% | ~28% |

These ignore the opposing barrier, so they are upper bounds on *touching*, not on
touching first. `exit_signal_checker.py:148` flags a time stop at `days >= 10`.
TP2 needs roughly a quarter of a trading year. Positive drift from a working
screen improves both columns but cannot close a 6× horizon gap.

### The geometry contributes no edge

Enumerating the current policy's outcomes in R:

| Path | Outcome |
| --- | --- |
| Stops out before 2R | −1.0R |
| TP1, remainder later stops at SL0 | `0.5·(+2R) + 0.5·(−1R)` = **+0.5R** |
| TP1 then TP2 | `0.5·(+2R) + 0.5·(+4R)` = +3.0R |

```text
E = −1 + 1.5·p1 + 2.5·p2
```

Under a driftless walk `P(hit +bR before −1R) = 1/(1+b)`, so `p1 = 1/3`,
`p2 = 1/5`, and `E = −1 + 0.500 + 0.500 = 0.000R` exactly. Because `p2` is near
zero within the time-stop horizon, the realistic distribution collapses onto the
first two rows — where the **best** case is +0.5R. Half the position banks at a
good multiple and the other half is held all the way back to the original stop.
That is the least attractive shape available.

Note the coincidence: `1/(1+b)` is both the breakeven win rate for reward:risk
`b` and the driftless first-passage probability. Fixed-target geometry is a fair
game by construction. **Tuning the multiples cannot manufacture edge**; it only
decides how much of an existing edge is captured.

## What "not entry-price-only" can mean

Three genuinely different changes hide inside one sentence, with very different
audit profiles. Conflating them is the main way this goes wrong.

| | What moves | Audit impact |
| --- | --- | --- |
| **A. Different anchor, still frozen** | The level, once, at plan creation | None. New formula, new `policy_version`, same immutability contract. |
| **B. Path-dependent exit** | The active stop, monotonically upward | Fits the existing `TRAIL_SL` event model exactly. |
| **C. Recomputed target** | The target itself, in both directions | Requires a new event kind with no natural monotone invariant. |

A and B are safe. **C is where the bad ideas live** and is rejected below.

## Proposed policy — `atr-chandelier-v1`

Keep TP1 entry-anchored at **2R** and set `tp1_fraction` to **~1/3**. Delete the
fixed TP2. Manage the runner with a close-based trail at **`k = 4.0`** (multi-agent
vote; see [Voted answers](#voted-answers)):

```text
trail_t = max( SL0, highest_close(entry..t) − 4.0 × ATR14_t )
exit     when close_t ≤ trail_t
```

Monotone non-decreasing. Emitted nightly as a **proposed** `TRAIL_SL` event for
owner confirmation, mirroring the existing propose/adopt flow in
`risk_plan_migrate.py`. `k`, `trail_anchor`, and the per-instrument tick are
frozen into the hashed policy document at plan creation, so replaying the event
chain from bars reproduces every level.

Broker side (if used at all): a **static** protective stop on the separate track
already allowed by [`SL-TP-AUDIT.md`](SL-TP-AUDIT.md) — not a live auto-ratcheting
broker trail. The Chandelier only advances via propose/adopt `TRAIL_SL` from
closes.

### Why close-based, and why not k = 3

Computed on **closes only**, the trail generates no intraday path ambiguity at
all. There is no `AMBIGUOUS_INTRADAY` analogue for a close-triggered trail — a
strictly stronger determinism property than the current TP/SL touch classes. This
matters more here than in most systems because the audit contract, not the
backtest, is the binding constraint.

`k = 3` must be avoided. Because `R = 1.5·A`, `TP1 = F + 3A`, so a 3-ATR trail
sits at **exactly the fill price** when price reaches TP1 — quietly
reintroducing the automatic breakeven stop that
[`SL-TP-AUDIT.md`](SL-TP-AUDIT.md) rule 4 deliberately forbids. At `k = 4` the
trail first exceeds SL0 at `MFE ≈ 1.67R` and reaches breakeven at `MFE ≈ 2.67R`.

### Why a partial tranche survives at all

The evidence is genuinely mixed and worth stating honestly. Systematic
trend-following backtests find that essentially every profit-target and
position-reduction combination **reduces total return** — while also reducing
maximum drawdown. Partials buy drawdown reduction with return.

The counterweight is specific to this system: orders are placed manually. Odean's
brokerage study shows individual investors sell winners too readily, and the
winners they sell keep outperforming the losers they keep. The realistic
alternative to a defined partial is not the theoretically optimal full-runner
policy — it is the owner overriding the system on a bad afternoon. That argues
for keeping *a* partial while shrinking it, not for deleting it.

Three tranches are rejected: commission and FX drag on a ~£5,000 lot, plus more
share-allocation edge cases on top of the existing one-share special case.

## Rejected options

| Option | Verdict | Reason |
| --- | --- | --- |
| Re-anchor TP to current ATR | **Reject** | ATR expands after favourable moves, so `F + 6·ATR_t` recedes as price approaches. A target that cannot be converged on is worse than none. Also needs a mutable target event with no monotone invariant. |
| Keltner / Bollinger upper band | **Reject** | Mean-reversion logic on a momentum book; in strong trends price walks the band, so it exits at the start of the best moves. |
| 52-week / all-time high target | **Reject** | George & Hwang: nearness to the 52-week high predicts *continuation*, and those returns do not reverse. Selling there sells as the anchoring bias resolves in your favour. |
| Parabolic SAR | **Reject** | 10–30% win rates on daily OHLC; always in the market; the accelerating factor is path-dependent state, a reproducibility hazard. |
| Percentage trailing stop | **Reject** | Strictly dominated by ATR trailing when Wilder ATR14 is already computed, across two currencies with different volatility scales. |
| Automatic breakeven after TP1 | **Reject** (already policy) | Sits inside normal noise. Flagged because `k = 3` reintroduces it by the back door. |
| Upside congestion zone | **Reject** | See below — it degenerates for exactly the entries this system takes. |

### Why the symmetric upside zone does not work

This is the appealing idea, and it fails for two independent reasons that
reinforce each other.

**Structural.** A cluster found in a 20-bar window cannot lie above that window's
highest high. For a momentum/breakout entry — what a T&M screen with MACD, ADX
and MA alignment is meant to produce — the fill sits at or near the top of the
20-bar range, so there is by construction almost no mass above it. The upside
zone resolves to `NO_CLUSTER` for precisely the trades that matter.

**Parametric.** `market_data.py:331` sets `min_mass = total_mass * cfg.rho` with
`rho = 0.40` — 40% of the mass of the *entire* window. A resistance cluster above
current price would have to hold 40% of all 20 sessions' volume. When price is
near the low of its range, which is exactly when overhead supply is worth
knowing, nothing above it can clear that bar. Reusing the zone finder upward is
therefore not "add a price floor"; `rho` would have to be re-based on mass above
the floor, changing the parameter's meaning rather than its value.

Extending to a ~250-session window would capture genuine overhead supply and is
within the 400-day fetch, but degrades badly: a year of **unadjusted** bars mixes
pre- and post-dividend price levels, any split destroys the profile, and the
candidate scan hits `AMBIGUOUS_CLUSTER` far more often. The most common outcome
would be a reject.

The one defensible use of this family is micro-placement: shade a resting limit
one or two ticks **below** a round number rather than at it. Osler finds
take-profit orders cluster particularly strongly at round numbers (9.3% exactly
at "00" vs 4.4% for stops), making them partially reflecting barriers. That is a
two-line change to the rounding function, not a policy.

## Phased plan

### P0 — Excursion ledger (read-only, zero risk)

Ship `scripts/host/excursion_ledger.py` **before** changing any policy. For every
closed lot, replay validated bars between entry and exit and record MAE,
`MFE_high`, `MFE_close`, capture ratio, and sessions held, in R units. Write a
JSON artifact plus a nightly report section. It writes nothing to
`risk_plans.json`.

This is the only proposal that cannot make anything worse, needs no new data, and
converts the 2R/4R argument from opinion into measurement.

Record **both** `MFE_high` and `MFE_close`. MFE from daily highs measures what a
resting GTC limit could have captured; `MFE_close` is the achievable benchmark
for a close-based, next-session-manual workflow. The gap between them is a
direct, quantified measure of what this execution model costs.

**Known limit.** The live journal holds 2 fully closed round trips (CMCSA, IBM),
   against a working minimum near 30 for percentile-based targets — the repo's own
weakest statistical gate is `WR_MIN_CLOSED = 10` (`portfolio_tracker.py:45`). So
the ledger is instrumentation now and calibration in 12–18 months. The weak
version is still decisive today: **if TP2 has never once been reached, that alone
retires it.**

### P1 — `atr-chandelier-v1` in shadow

Register the policy version, compute the trail nightly, emit proposals only.
Trail raise/compare flags stay file-only (`telegram=False`), following the
`ZONE` precedent — independent of the watch wrapper's live Telegram mode.
Add a row to the Telegram policy table in [`SL-TP-AUDIT.md`](SL-TP-AUDIT.md).

### P2 — Unify the exit ladder

Today price exits live in `position_watch.py` against the sidecar, while score
and time exits live in `exit_signal_checker.py` writing to stdout. Two exit
systems that can disagree, with no shared precedence rule and only one of them
audited. Make time and score **condition** the price rule rather than race it:

- Count actual sessions from the bar series. `count_trading_days` currently
  computes `calendar_days × 5/7` and returns `999` on a parse failure, which also
  trips the flag (`exit_signal_checker.py:126-133`, duplicated at
  `position_watch.py:163`).
- Latch the time stop so it fires **once**. `days >= 10` is monotone in time, so
  a six-month winner emits that line ~120 times. Alerts that always fire get
  ignored.
- Condition it on `MFE_close < 1R`, so it means "this never worked" rather than
  "this is old."
- Feed `tm_score < 50` into the trail multiple (tighten `k` toward 2.5) instead
  of emitting a competing exit suggestion. This stays monotone, so it remains a
  legal `TRAIL_SL`.

## Prerequisites and defects found

These surfaced during the review and are worth fixing regardless of which policy
is adopted.

1. **`MarketEvidence` discards the bar series.** `market_data.py:126-135` exposes
   a single `DailyBar`. The nightly fetch already retrieves, validates and caches
   ~400 calendar days — `_history_start` anchors on
   `min(expected_session, plan_created_session) − 400d`, so **every nightly fetch
   already covers the entire holding period**. Verified live: a UNH cache file
   holds 277 bars for a 2026-09-08 fill. Exposing this series is the shared
   prerequisite for the trail and for the ledger.
2. **`tick_size` is hardcoded to 0.01 and wrong for LSE.** `RiskPolicy.tick_size`
   (`risk_plan.py:94`) is a 1 **penny** grid after GBp normalisation. Under MiFID
   II RTS 11 a liquid name at 605p has a 0.2p tick (0.002 GBP, 5× finer); a 45p
   small-cap has ~0.05p (0.0005 GBP), where 1p rounding distorts levels by up to
   **2.2% of price** — potentially a large fraction of R. The direction is
   conservative for stops (`ROUND_CEILING` toward fill) but pushes targets
   further away and shrinks a trail's effective resolution. Any trailing policy
   needs a per-instrument tick frozen into the plan.
3. **TP conflict detection is dead code.** `_uniq_level` (`position_watch.py:122`)
   is defined but never called, so `tp1_conflict`/`tp2_conflict` are permanently
   `False` and multi-lot TP disagreement is silently undetected.
4. **Reruns are not addressable.** `retrieved_at` sits inside the `evidence`
   block that feeds the cache filename digest (`market_data.py:486-490`), so each
   rerun writes a new file rather
   than overwriting, and `evidence.cache_path` is `null` inside the stored
   document. Reproducing a specific night's level requires knowing which digest
   the report used, and nothing records it.

## Determinism contract

A trailing level must be a pure function of (validated bars up to session *S*,
frozen plan). Specific hazards:

- **Split restatement.** yfinance with `auto_adjust=False` still returns
  split-adjusted history, so a 2:1 split halves every prior high and moves
  "highest close since entry" with no new session. The existing guard only fires
  for splits after plan creation (`market_data.py:599`), and `position_watch.py`
  drops `UNREBASED_SPLIT` once a `REBASE_SPLIT` exists. Recompute the trail from
  the same restated basis as the rebased levels, and refuse when a split falls in
  the entry→session window without a matching rebase.
- **Recompute, never store a running maximum.** On `EXPECTED_SESSION_MISSING` a
  stateless recompute simply produces no update that night. A stored running high
  would freeze with nothing recording why.
- **Dividends.** The highest close on unadjusted bars is measured pre-ex-div while
  the current close is post, which tightens the trail by the dividend amount. Add
  a `DIVIDEND_IN_WINDOW` observational flag.
- **Volume restatement is not a hazard here.** The trail is price-only. This is
  another argument against the volume-weighted upside zone, which is not.

## Test plan

The suite is already fully injection-based (`FixtureTransport`,
`WindowTransport`, `BoomTransport`, `StubMarket`) with no network access.

- Chandelier level equals `max(close since entry) − k × ATR` as an exact
  `Decimal`, on a synthetic ramp-then-fade series.
- The trail never decreases across three consecutive session runs.
- A missing session leaves the trail unchanged.
- An unrebased split **refuses** rather than emitting a restated level.
- `k = 3` reproduces the fill price at TP1 — pinned as a regression guard against
  accidental breakeven.
- `TRAIL_TP`-free round trip: the immutable core and `calculation_hash` are
  unchanged by any trail event.
- Ledger: MAE/MFE in R units against a hand-built bar fixture, including the
  `MFE_high` vs `MFE_close` divergence.

Existing gaps worth closing at the same time: no test covers the TP2 close breach
flag, `TP1_INTRADAY_TOUCH`/`TP2_INTRADAY_TOUCH`, the `--grandfather` path, or the
`PARTIAL_LEGACY` state.

## Voted answers

Four agents voted independently. Lenses: risk/audit, expectancy/math, ops/execution,
behavioural sustainability. Still a proposal — nothing is adopted into the live
sidecar until an explicit owner row-level decision.

| Decision | Risk/audit | Expectancy | Ops | Behavioural | **Consensus** |
| --- | --- | --- | --- | --- | --- |
| Trail `k` | 4.0 | 4.0 | 4.0 | 4.0 | **4.0 (4/4)** |
| `tp1_fraction` | ~1/3 | ~1/3 | 0.5 | ~1/3 | **~1/3 (3/4)** |
| TP1 level | 2R | 2R | 1.5R | 2R | **2R (3/4)** |
| Broker trail | daily-close only | daily-close only | live broker trail + sidecar | static broker SL + daily-close propose | **daily-close Chandelier; no live broker trail (3/4)** |

### 1. `k = 4.0` — unanimous

All four lenses preferred the looser trail. It sits further from accidental
breakeven (`k=3` is forbidden; `k=3.5` still engages early), truncates winners
less often under T&M drift, and fires fewer nightly amendment nights for a manual
owner. Shadow may still *compare* 3.5; the frozen policy default is 4.0.

### 2. `tp1_fraction ≈ 1/3` — 3/4

Risk, expectancy, and behavioural: after TP2 dies, the runner is the only
non-neutral piece of the policy; half-size still glued to SL0 recreates the
+0.5R dead zone and the “I already took the win” dump. Ops dissented for 0.5
(more set-and-forget GTC, thinner runner babysitting). Consensus follows the
majority: bank enough to quiet disposition itch, leave ~2/3 for the Chandelier.

### 3. TP1 stays at **2R** — 3/4

Do not retune the entry-anchored tranche in the same adoption that deletes TP2
and adds a path-dependent trail. Dropping to 1.5R buys hit rate by clipping
earlier into a fair-game cashflow; reachability of the *runner* exit is what the
Chandelier addresses. Ops wanted 1.5R for resting-limit practicality inside the
time-stop window — noted as dissent, not adopted.

### 4. Daily-close Chandelier; no live broker trail — 3/4

The trail advances only via propose/adopt `TRAIL_SL` from closes, so bar replay
stays deterministic. A live auto-ratcheting broker trail races the hashed
sidecar, can flatten overnight with no ritual, and can reintroduce near-fill
“protection” outside the event chain.

Ops wanted a live broker trail for gap/intraday protection. Behavioural allowed
only a **static** broker protective stop (already a separate track in
`SL-TP-AUDIT.md`) plus the daily-close propose cadence — that is compatible with
the majority, not with a self-moving broker trail. Conceding intraday range and
overnight gap is an accepted execution cost of the audit model.

### Ballots

```text
Risk/audit:   k=4.0; fraction≈1/3; TP1=2R; broker=daily-close-only
Expectancy:   k=4.0; fraction≈1/3; TP1=2R; broker=daily-close
Ops:          k=4.0; fraction=0.5; TP1=1.5R; broker=hybrid-broker-trail+sidecar-alert
Behavioural:  k=4.0; fraction≈1/3; TP1=2R; broker=hybrid (protective SL + daily-close trail propose)
```
