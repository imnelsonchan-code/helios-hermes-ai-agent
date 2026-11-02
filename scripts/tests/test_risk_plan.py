#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from market_data import ZoneEvidence  # noqa: E402
from risk_plan import (  # noqa: E402
    POLICY_VERSION,
    ZONE_POLICY_VERSION,
    CHANDELIER_POLICY_VERSION,
    RiskPolicy,
    RiskPlanError,
    append_plan_event,
    apply_split_rebase,
    calculate_levels,
    calculate_levels_with_zone,
    chandelier_policy,
    check_nav_gates,
    create_plan,
    create_plan_with_zone,
    load_plan_store,
    parse_journal_fill,
    planned_stop_risk,
    propose_chandelier_trail_sl,
    reconcile_plan,
    trail_exit_triggered,
    validate_plan,
    write_plan_store,
)

# ACME fixture: F=336.32, ATR14=8.65, R=1.5×ATR14.
# R = 1.5 * 8.65 = 12.975
# raw SL0 = 336.32 - 12.975 = 323.345 -> ceiling-to-tick (toward fill) = 323.35
# raw TP1 = 336.32 + 2*12.975 = 362.27 -> ceiling-to-tick (away from fill) = 362.27
# raw TP2 = 336.32 + 4*12.975 = 388.22 -> ceiling-to-tick (away from fill) = 388.22
ACME_SL0 = Decimal("323.35")
ACME_TP1 = Decimal("362.27")
ACME_TP2 = Decimal("388.22")


def _buy(**updates):
    row = {
        "Date": "2026-09-08",
        "Ticker": "ACME",
        "Action": "BUY",
        "Shares": "50",
        "Price": "249.40",
        "Price USD": "336.32",
        "Total USD": "16815.75",
        "SL": "330",
        "TP1": "351",
        "TP2": "373",
        "Status": "OPEN",
        "Notes": "Synthetic buy",
        "RowID": "entry-1",
    }
    row.update(updates)
    return row


class RiskPlanTests(unittest.TestCase):
    def setUp(self):
        self.fill = parse_journal_fill(_buy())
        self.plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        )

    def test_usd_fill_uses_price_usd(self):
        self.assertEqual(self.fill.currency, "USD")
        self.assertEqual(self.fill.price, Decimal("336.32"))
        self.assertEqual(self.fill.source_field, "Price USD")

    def test_usd_total_fallback_and_mismatch_rejected(self):
        fill = parse_journal_fill(_buy(**{"Price USD": "", "Total USD": "16816"}))
        self.assertEqual(fill.price, Decimal("336.32"))
        with self.assertRaises(RiskPlanError):
            parse_journal_fill(_buy(**{"Total USD": "10000"}))

    def test_atr_r_levels_and_share_allocation(self):
        self.assertEqual(POLICY_VERSION, "atr-r-v2")
        self.assertEqual(self.plan.policy_version, "atr-r-v2")
        levels = calculate_levels(self.fill, Decimal("8.65"))
        self.assertEqual(levels.sl0, ACME_SL0)
        self.assertEqual(levels.tp1, ACME_TP1)
        self.assertEqual(levels.tp2, ACME_TP2)
        self.assertEqual((levels.tp1_shares, levels.tp2_shares), (25, 25))
        self.assertLess(levels.risk_per_share, Decimal("12.975"))

    def test_store_roundtrip_and_core_is_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plans.json"
            write_plan_store(path, {self.plan.plan_id: self.plan})
            loaded = load_plan_store(path)
            self.assertEqual(loaded[self.plan.plan_id], self.plan)
            changed = replace(
                self.plan,
                levels=replace(self.plan.levels, tp2=self.plan.levels.tp2 + Decimal("1")),
            )
            with self.assertRaises(RiskPlanError):
                write_plan_store(path, {changed.plan_id: changed}, existing=loaded)

    def test_tampered_hash_and_malformed_store_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plans.json"
            write_plan_store(path, {self.plan.plan_id: self.plan})
            doc = json.loads(path.read_text())
            doc["plans"]["entry-1"]["levels"]["tp2"] = "999"
            path.write_text(json.dumps(doc))
            with self.assertRaises(RiskPlanError):
                load_plan_store(path)
            path.write_text('{"schema_version":"1","plans":{"x":{}}}')
            with self.assertRaises(RiskPlanError):
                load_plan_store(path)

    def test_event_history_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plans.json"
            write_plan_store(path, {self.plan.plan_id: self.plan})
            replacement = replace(
                self.plan.events[0],
                event_id="sha256:changed",
            )
            changed = replace(self.plan, events=(replacement,))
            with self.assertRaises(RiskPlanError):
                write_plan_store(path, {changed.plan_id: changed})

    def test_partial_sell_requires_attribution_and_exact_quantity(self):
        sell = {
            "Date": "2026-09-09",
            "Ticker": "ACME",
            "Action": "SELL",
            "Shares": "25",
            "Status": "CLOSED",
            "RowID": "sell-1",
            "Notes": "PLAN_ROW_ID=entry-1 TP1",
        }
        view = reconcile_plan(self.plan, [sell])
        self.assertEqual(view.state, "TP1_EXECUTED")
        self.assertEqual(view.remaining_shares, 25)
        self.assertEqual(view.active_sl, self.plan.levels.sl0)
        self.assertEqual(view.active_sl, ACME_SL0)
        self.assertNotEqual(view.active_sl, self.fill.price)
        self.assertEqual(view.tp1, ACME_TP1)
        self.assertEqual(view.tp2, ACME_TP2)
        self.assertFalse(view.rebased)
        unlinked = reconcile_plan(self.plan, [{**sell, "Notes": ""}])
        self.assertEqual(unlinked.state, "BLOCKED")
        self.assertIn("UNATTRIBUTED_SELL", unlinked.issues)

    def test_non_closed_sells_do_not_count(self):
        attributed = {
            "Date": "2026-09-09",
            "Ticker": "ACME",
            "Action": "SELL",
            "Shares": "25",
            "RowID": "sell-ignored",
            "Notes": "PLAN_ROW_ID=entry-1 TP1",
        }
        ignored = [
            {**attributed, "Status": "PENDING", "RowID": "sell-pending"},
            {**attributed, "Status": "VOID", "RowID": "sell-void"},
            {**attributed, "Status": "OPEN", "RowID": "sell-open"},
            {**attributed, "Status": "", "RowID": "sell-blank"},
        ]
        view = reconcile_plan(self.plan, ignored)
        self.assertEqual(view.state, "ACTIVE")
        self.assertEqual(view.remaining_shares, 50)
        self.assertEqual(view.active_sl, ACME_SL0)

    def test_trailing_event_may_raise_but_not_lower_stop(self):
        raised = append_plan_event(
            self.plan,
            kind="TRAIL_SL",
            actor="owner",
            reason="protect profit",
            payload={"old_sl": str(ACME_SL0), "new_sl": "338.00", "broker_sl": "338.00"},
            occurred_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        )
        self.assertEqual(reconcile_plan(raised, []).active_sl, Decimal("338.00"))
        with self.assertRaises(RiskPlanError):
            append_plan_event(
                self.plan,
                kind="TRAIL_SL",
                actor="owner",
                reason="invalid",
                payload={"old_sl": str(ACME_SL0), "new_sl": "300", "broker_sl": "300"},
                occurred_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
            )

    def test_trail_after_tp1_keeps_raised_stop(self):
        sell = {
            "Date": "2026-09-09",
            "Ticker": "ACME",
            "Action": "SELL",
            "Shares": "25",
            "Status": "CLOSED",
            "RowID": "sell-1",
            "Notes": "PLAN_ROW_ID=entry-1 TP1",
        }
        trailed = append_plan_event(
            self.plan,
            kind="TRAIL_SL",
            actor="owner",
            reason="trail after TP1",
            payload={"old_sl": str(ACME_SL0), "new_sl": "340.00", "broker_sl": "340.00"},
            occurred_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        )
        view = reconcile_plan(trailed, [sell])
        self.assertEqual(view.state, "TP1_EXECUTED")
        self.assertEqual(view.active_sl, Decimal("340.00"))
        self.assertNotEqual(view.active_sl, self.fill.price)

    def test_event_requires_audit_fields_and_complete_payload(self):
        with self.assertRaises(RiskPlanError):
            append_plan_event(
                self.plan,
                kind="TRAIL_SL",
                actor="",
                reason="",
                payload={"new_sl": "338", "broker_sl": "338"},
            )

    def test_trail_sl_requires_broker_attestation(self):
        with self.assertRaises(RiskPlanError) as ctx:
            append_plan_event(
                self.plan,
                kind="TRAIL_SL",
                actor="owner",
                reason="missing broker",
                payload={"old_sl": str(ACME_SL0), "new_sl": "338.00"},
                occurred_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
            )
        self.assertIn("broker_sl", str(ctx.exception))
        none_ok = append_plan_event(
            self.plan,
            kind="TRAIL_SL",
            actor="owner",
            reason="no resting stop",
            payload={
                "old_sl": str(ACME_SL0),
                "new_sl": "338.00",
                "broker_sl": "BROKER_SL_NONE",
            },
            occurred_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        )
        self.assertEqual(reconcile_plan(none_ok, []).active_sl, Decimal("338.00"))

    def test_validate_uses_stored_policy_not_defaults(self):
        custom = RiskPolicy(risk_atr_multiple=Decimal("2.0"))
        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            policy=custom,
        )
        self.assertEqual(validate_plan(plan), ())
        self.assertEqual(plan.policy["risk_atr_multiple"], "2.0")
        wiped = replace(plan, policy={})
        self.assertIn("INPUT_HASH_INVALID", validate_plan(wiped))

    def test_rebase_split_updates_plan_view_not_core(self):
        # 2-for-1: shares 50->100
        # SL 323.35/2 = 161.675 -> ceiling-to-tick 161.68
        # TP1 362.27/2 = 181.135 -> ceiling-to-tick 181.14
        # TP2 388.22/2 = 194.11 -> ceiling-to-tick 194.11
        rebased = apply_split_rebase(
            self.plan,
            ratio="2",
            effective_date="2026-09-10",
            actor="owner",
            reason="2-for-1 split",
            occurred_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        )
        event = rebased.events[-1]
        self.assertEqual(event.kind, "REBASE_SPLIT")
        self.assertEqual(event.payload["ratio"], "2")
        self.assertEqual(event.payload["effective_date"], "2026-09-10")
        self.assertEqual(event.payload["new_shares"], 100)
        self.assertEqual(event.payload["new_sl"], "161.68")
        self.assertEqual(event.payload["new_tp1"], "181.14")
        self.assertEqual(event.payload["new_tp2"], "194.11")
        self.assertEqual(rebased.levels.sl0, ACME_SL0)
        self.assertEqual(rebased.fill.shares, 50)
        view = reconcile_plan(rebased, [])
        self.assertTrue(view.rebased)
        self.assertEqual(view.state, "ACTIVE")
        self.assertEqual(view.remaining_shares, 100)
        self.assertEqual(view.active_sl, Decimal("161.68"))
        self.assertEqual(view.tp1, Decimal("181.14"))
        self.assertEqual(view.tp2, Decimal("194.11"))

    def test_zone_policy_geometry_when_zone_widens_stop(self):
        fill = parse_journal_fill(_buy(**{"Price USD": "100", "Total USD": "5000"}))
        zone = ZoneEvidence(
            status="OK",
            reason_code="OK",
            mode="VPDC",
            zone_lo=Decimal("80"),
            zone_hi=Decimal("82"),
            through_session=date(2026, 9, 7),
            window_start=date(2026, 8, 11),
            window_end=date(2026, 9, 7),
            bars_used=20,
            bin_size=Decimal("0.1"),
            mass=Decimal("1000"),
            total_mass=Decimal("2000"),
            width=Decimal("2.0"),
        )
        levels = calculate_levels_with_zone(fill, Decimal("10"), zone)
        self.assertEqual(levels.sl0, Decimal("75.00"))
        self.assertEqual(levels.risk_per_share, Decimal("25.00"))
        self.assertEqual(levels.tp1, Decimal("150.00"))
        self.assertEqual(levels.tp2, Decimal("200.00"))
        plan = create_plan_with_zone(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("10"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            zone=zone,
        )
        self.assertEqual(plan.policy_version, ZONE_POLICY_VERSION)
        self.assertEqual(plan.policy["zone_status"], "OK")
        self.assertEqual(plan.policy["zone_mode"], "VPDC")
        self.assertEqual(plan.policy["zone_lo"], "80")
        self.assertEqual(plan.policy["zone_hi"], "82")
        self.assertEqual(plan.policy["merge"], "min")
        self.assertEqual(validate_plan(plan), ())

    def test_nav_gates(self):
        nav = Decimal("100000")
        self.assertEqual(planned_stop_risk(50, Decimal("12.97")), Decimal("648.50"))
        self.assertEqual(
            check_nav_gates(
                [{"risk": "500", "sector": "tech", "stress_gap": "1000"}],
                nav,
            ),
            (),
        )
        self.assertIn(
            "LOT_RISK_EXCESS",
            check_nav_gates(
                [{"risk": "501", "sector": "tech", "stress_gap": "0"}],
                nav,
            ),
        )
        book_lots = [
            {"risk": "500", "sector": f"s{i}", "stress_gap": "0"} for i in range(7)
        ]
        self.assertIn("BOOK_RISK_EXCESS", check_nav_gates(book_lots, nav))
        self.assertIn(
            "SECTOR_RISK_EXCESS",
            check_nav_gates(
                [
                    {"risk": "400", "sector": "tech", "stress_gap": "0"},
                    {"risk": "400", "sector": "tech", "stress_gap": "0"},
                    {"risk": "400", "sector": "tech", "stress_gap": "0"},
                    {"risk": "400", "sector": "tech", "stress_gap": "0"},
                ],
                nav,
            ),
        )
        self.assertIn(
            "STRESS_GAP_EXCESS",
            check_nav_gates(
                [{"risk": "100", "sector": "x", "stress_gap": "5001"}],
                nav,
            ),
        )

    def test_chandelier_policy_levels(self):
        policy = chandelier_policy()
        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            policy=policy,
        )
        self.assertEqual(plan.policy_version, CHANDELIER_POLICY_VERSION)
        self.assertEqual(plan.levels.tp1, ACME_TP1)
        self.assertEqual(plan.levels.tp2, plan.levels.tp1)
        self.assertEqual(plan.levels.tp1_shares, 16)
        self.assertEqual(plan.levels.tp2_shares, 34)
        self.assertEqual(plan.policy.get("trail_k"), "4.0")
        self.assertEqual(plan.policy.get("trail_anchor"), "close")
        self.assertEqual(plan.policy.get("tp2_mode"), "unused")
        self.assertEqual(validate_plan(plan), ())

    def test_chandelier_k3_at_tp1_equals_fill(self):
        """Regression: k=3 sits at fill when price reaches TP1 (= F+3A)."""
        atr = Decimal("8.65")
        fill = self.fill.price
        # Algebraic identity from atr-r-v2: R=1.5A ⇒ TP1=F+3A.
        tp1 = fill + Decimal("3") * atr
        self.assertEqual(tp1 - Decimal("3") * atr, fill)
        self.assertLess(tp1 - Decimal("4") * atr, fill)
        # Integration: when highest close is TP1, raw trail with k=3 ≈ fill.
        from market_data import DailyBar, chandelier_raw

        entry = date(2026, 9, 1)
        bars = []
        for i in range(21):
            session = entry - timedelta(days=20 - i)
            close = fill if i < 20 else tp1
            bars.append(
                DailyBar(
                    session=session,
                    open=close,
                    high=close + atr / Decimal("2"),
                    low=close - atr / Decimal("2"),
                    close=close,
                    volume=1000,
                )
            )
        through = bars[-1].session
        hc, bar_atr, raw3 = chandelier_raw(
            bars,
            from_session=entry,
            through_session=through,
            trail_k=Decimal("3"),
        )
        self.assertEqual(hc, tp1)
        # Allow Wilder ATR to differ slightly from the constant used in geometry.
        self.assertLess(abs(raw3 - (hc - Decimal("3") * bar_atr)), Decimal("0.01"))
        _hc4, _a4, raw4 = chandelier_raw(
            bars,
            from_session=entry,
            through_session=through,
            trail_k=Decimal("4"),
        )
        self.assertLess(raw4, raw3)

    def test_chandelier_trail_propose_monotone_and_core_immutable(self):
        from market_data import DailyBar

        start = date(2026, 8, 1)
        # Constant true range ≈ 2 so recomputed ATR matches plan atr14.
        base = []
        for i in range(20):
            session = start + timedelta(days=i)
            base.append(
                DailyBar(
                    session=session,
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100"),
                    volume=1000,
                )
            )
        fill = parse_journal_fill(
            _buy(
                **{
                    "Date": "2026-08-15",
                    "Price USD": "100",
                    "Total USD": "5000",
                    "Shares": "50",
                }
            )
        )
        atr = Decimal("2")
        plan = create_plan(
            fill,
            atr_session=date(2026, 8, 14),
            atr14=atr,
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        core_hash = plan.calculation_hash
        # Continue after last base session — no duplicate dates.
        # Need HC − 4×ATR > SL0≈97 -> HC > 105 with ATR≈2.
        ramp = list(base)
        last = base[-1].session
        sessions = []
        for i, close in enumerate((110, 114, 118)):
            session = last + timedelta(days=i + 1)
            sessions.append(session)
            ramp.append(
                DailyBar(
                    session=session,
                    open=Decimal(str(close - 1)),
                    high=Decimal(str(close + 1)),
                    low=Decimal(str(close - 1)),
                    close=Decimal(str(close)),
                    volume=1000,
                )
            )
        proposed = []
        for session in sessions:
            payload, reason = propose_chandelier_trail_sl(
                plan, ramp, through_session=session
            )
            if payload is None:
                self.assertIn(reason, {None, "NO_RAISE", "MISSING_SESSION"})
                continue
            proposed.append(Decimal(payload["new_sl"]))
            plan = append_plan_event(
                plan,
                kind="TRAIL_SL",
                actor="test",
                reason="TEST_TRAIL",
                payload={"old_sl": payload["old_sl"], "new_sl": payload["new_sl"], "broker_sl": payload["new_sl"]},
            )
        self.assertGreaterEqual(len(proposed), 1)
        for earlier, later in zip(proposed, proposed[1:]):
            self.assertLessEqual(earlier, later)
        self.assertEqual(plan.calculation_hash, core_hash)
        self.assertTrue(trail_exit_triggered(proposed[-1], proposed[-1]))
        self.assertFalse(trail_exit_triggered(proposed[-1] + 1, proposed[-1]))

    def test_chandelier_missing_session_no_update(self):
        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        self.assertEqual(
            propose_chandelier_trail_sl(plan, (), through_session=date(2026, 9, 9)),
            (None, "MISSING_SESSION"),
        )

    def test_chandelier_rebase_allows_trail_above_tp1(self):
        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        # Raise trail above the unused TP1 placeholder (normal runner path).
        above_tp1 = plan.levels.tp1 + Decimal("10")
        plan = append_plan_event(
            plan,
            kind="TRAIL_SL",
            actor="test",
            reason="TEST_ABOVE_TP1",
            payload={"old_sl": str(plan.levels.sl0), "new_sl": str(above_tp1), "broker_sl": str(above_tp1)},
        )
        rebased = apply_split_rebase(
            plan,
            ratio=Decimal("2"),
            effective_date="2026-09-10",
            actor="test",
        )
        view = reconcile_plan(rebased, [])
        self.assertTrue(view.rebased)
        self.assertEqual(view.remaining_shares, 100)
        self.assertEqual(view.tp1, view.tp2)
        self.assertGreater(view.active_sl, view.tp1)
        self.assertEqual(validate_plan(rebased), ())

    def test_chandelier_unrebased_split_refuses_propose(self):
        from market_data import DailyBar, SplitEvent

        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        # Bars must span fill (2026-09-08) through a later session with a split.
        start = date(2026, 8, 20)
        bars = []
        for i in range(25):
            session = start + timedelta(days=i)
            bars.append(
                DailyBar(
                    session=session,
                    open=Decimal("350"),
                    high=Decimal("352"),
                    low=Decimal("348"),
                    close=Decimal("350"),
                    volume=1000,
                )
            )
        through = bars[-1].session
        self.assertGreater(through, date(2026, 9, 8))
        splits = (SplitEvent(through, Decimal("2")),)
        self.assertEqual(
            propose_chandelier_trail_sl(
                plan, bars, through_session=through, splits=splits
            ),
            (None, "UNREBASED_SPLIT"),
        )
        # After REBASE_SPLIT, the same restated series may propose again.
        rebased = apply_split_rebase(
            plan,
            ratio=Decimal("2"),
            effective_date=through.isoformat(),
            actor="test",
        )
        payload, reason = propose_chandelier_trail_sl(
            rebased,
            bars,
            through_session=through,
            splits=splits,
            plan_rebased=True,
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(payload)

    def test_shadow_legacy_no_raise_emits_compare_only(self):
        from market_data import DailyBar

        start = date(2026, 8, 20)
        bars = []
        for i in range(25):
            session = start + timedelta(days=i)
            close = Decimal("336")
            bars.append(
                DailyBar(
                    session=session,
                    open=close,
                    high=close + Decimal("2"),
                    low=close - Decimal("2"),
                    close=close,
                    volume=1000,
                )
            )
        through = bars[-1].session
        # Default atr-r-v2 plan — shadow path only.
        payload, reason = propose_chandelier_trail_sl(
            self.plan,
            bars,
            through_session=through,
            shadow_for_legacy=True,
        )
        self.assertEqual(reason, "NO_RAISE")
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["compare_only"], "NO_RAISE")
        self.assertEqual(payload["shadow"], "atr-chandelier-v1")
        self.assertEqual(payload["old_sl"], payload["new_sl"])
        self.assertEqual(Decimal(payload["new_sl"]), self.plan.levels.sl0)
        for key in (
            "session",
            "atr14",
            "highest_close",
            "trail_k",
            "trail_anchor",
            "entry_session",
        ):
            self.assertIn(key, payload)

    def test_chandelier_no_raise_stays_silent(self):
        from market_data import DailyBar

        start = date(2026, 8, 20)
        bars = []
        for i in range(25):
            session = start + timedelta(days=i)
            close = Decimal("336")
            bars.append(
                DailyBar(
                    session=session,
                    open=close,
                    high=close + Decimal("2"),
                    low=close - Decimal("2"),
                    close=close,
                    volume=1000,
                )
            )
        plan = create_plan(
            self.fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        self.assertEqual(
            propose_chandelier_trail_sl(plan, bars, through_session=bars[-1].session),
            (None, "NO_RAISE"),
        )


if __name__ == "__main__":
    unittest.main()
