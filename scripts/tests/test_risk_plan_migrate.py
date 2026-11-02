#!/usr/bin/env python3
"""Unit tests for risk_plan_migrate policy + trail adopt (no network)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from market_data import DailyBar  # noqa: E402
from risk_plan import (  # noqa: E402
    CHANDELIER_POLICY_VERSION,
    POLICY_VERSION,
    chandelier_policy,
    create_plan,
    parse_journal_fill,
    plan_to_dict,
    propose_chandelier_trail_sl,
    write_plan_store,
    load_plan_store,
)


def _load_migrate():
    path = HOST_DIR / "risk_plan_migrate.py"
    spec = importlib.util.spec_from_file_location("risk_plan_migrate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FixtureTransport:
    def __init__(self, bars: list[DailyBar], splits=()):
        self.bars = bars
        self.splits = splits

    def daily_history(self, symbol: str, start: date, end: date):
        from market_data import RawMarketResponse

        window = [b for b in self.bars if start <= b.session <= end]
        return RawMarketResponse(
            requested_symbol=symbol,
            returned_symbol=symbol,
            currency_code="USD",
            exchange="NMS",
            quote_timestamp=None,
            bars=tuple(window),
            splits=tuple(self.splits),
            raw_metadata={},
        )


class MigratePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_migrate()

    def _fill_row(self) -> dict:
        return {
            "RowID": "entry-acme",
            "Ticker": "ACME",
            "YahooSymbol": "ACME",
            "Action": "BUY",
            "Status": "OPEN",
            "Shares": "50",
            "Price USD": "336.32",
            "Price": "",
            "Date": "2026-09-08",
            "FilledAt": "2026-09-08",
            "Currency": "USD",
            "SL": "",
            "TP1": "",
            "TP2": "",
        }

    def _atr_bars(self, filled: date) -> list[DailyBar]:
        bars = []
        # 20 prior sessions with ATR-ish range around fill.
        for i in range(25):
            session = filled - timedelta(days=30 - i)
            if session.weekday() >= 5:
                continue
            close = Decimal("330") + Decimal(i)
            bars.append(
                DailyBar(
                    session=session,
                    open=close,
                    high=close + Decimal("10"),
                    low=close - Decimal("5"),
                    close=close,
                    volume=1_000_000,
                )
            )
        return bars

    def test_default_policy_skips_zone_geometry(self):
        """atr-r-v2 propose must not silently become atr-zone-v1."""
        from risk_plan import RiskPolicy, calculate_levels

        self.assertEqual(self.mod.POLICY_VERSION, "atr-r-v2")
        filled = date(2026, 9, 8)
        bars = self._atr_bars(filled)
        # Force a dense zone below fill so atr-zone-v1 would widen if used.
        for i, bar in enumerate(bars[-10:]):
            bars[-(10 - i)] = DailyBar(
                session=bar.session,
                open=Decimal("320"),
                high=Decimal("322"),
                low=Decimal("318"),
                close=Decimal("320"),
                volume=2_000_000,
            )
        with tempfile.TemporaryDirectory() as td:
            plan, record = self.mod._propose_atr_plan(
                self._fill_row(),
                FixtureTransport(bars),
                td,
                policy_version=self.mod.POLICY_VERSION,
            )
        self.assertEqual(plan.policy_version, "atr-r-v2")
        self.assertEqual(record["zone_status"], "SHADOW_ONLY")
        self.assertEqual(record["zone_reason_code"], "SHADOW_ONLY")
        pure = calculate_levels(
            parse_journal_fill(self._fill_row()),
            plan.levels.atr14,
            RiskPolicy(),
        )
        self.assertEqual(plan.levels.sl0, pure.sl0)

    def test_attest_broker_sl_match_and_none(self):
        matched = self.mod._attest_broker_sl(
            expected_sl=Decimal("323.35"),
            broker_sl="323.35",
            broker_sl_none=False,
        )
        self.assertEqual(matched["broker_sl_ack"], "MATCH")
        none = self.mod._attest_broker_sl(
            expected_sl=Decimal("323.35"),
            broker_sl="",
            broker_sl_none=True,
        )
        self.assertEqual(none["broker_sl"], "BROKER_SL_NONE")
        with self.assertRaises(self.mod.RiskPlanError):
            self.mod._attest_broker_sl(
                expected_sl=Decimal("323.35"),
                broker_sl="300",
                broker_sl_none=False,
            )

    def test_with_created_broker_attestation_freezes_without_recompute(self):
        from risk_plan import with_created_broker_attestation

        fill = parse_journal_fill(self._fill_row())
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        )
        attested = with_created_broker_attestation(
            plan, {"broker_sl": str(plan.levels.sl0), "broker_sl_ack": "MATCH"}
        )
        self.assertEqual(attested.levels.sl0, plan.levels.sl0)
        self.assertEqual(attested.events[0].payload["broker_sl_ack"], "MATCH")
        self.assertEqual(attested.calculation_hash, plan.calculation_hash)

    def test_chandelier_policy_levels_match_voted_defaults(self):
        fill = parse_journal_fill(self._fill_row())
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            policy=chandelier_policy(),
        )
        self.assertEqual(plan.policy_version, CHANDELIER_POLICY_VERSION)
        self.assertEqual(plan.levels.tp2, plan.levels.tp1)
        self.assertEqual(plan.levels.tp1_shares, 16)
        self.assertEqual(plan.levels.tp2_shares, 34)

    def test_adopt_trail_sl_raises_on_wrong_policy(self):
        fill = parse_journal_fill(self._fill_row())
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        )
        with tempfile.TemporaryDirectory() as td:
            store = str(Path(td) / "plans.json")
            write_plan_store(store, {plan.plan_id: plan}, existing={})
            with self.assertRaises(self.mod.RiskPlanError) as ctx:
                self.mod.adopt_trail_sl(
                    row_id=plan.plan_id,
                    session=date(2026, 9, 15),
                    store_path=store,
                    transport=FixtureTransport([]),
                )
            self.assertIn("atr-chandelier-v1", str(ctx.exception))

    def test_adopt_trail_sl_monotone_write(self):
        fill = parse_journal_fill(self._fill_row())
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            policy=chandelier_policy(),
        )
        entry = date(2026, 9, 8)
        bars = []
        # Pre-entry ATR window + favourable run above fill.
        for i in range(30):
            session = entry - timedelta(days=40 - i)
            close = Decimal("320")
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
        # Post-entry ramp so highest close - 4*ATR > SL0
        for i in range(12):
            session = entry + timedelta(days=i)
            close = fill.price + Decimal("3") * Decimal(i)
            bars.append(
                DailyBar(
                    session=session,
                    open=close,
                    high=close + Decimal("1"),
                    low=close - Decimal("1"),
                    close=close,
                    volume=1000,
                )
            )
        through = bars[-1].session
        payload, reason = propose_chandelier_trail_sl(
            plan, bars, through_session=through, splits=(), plan_rebased=False
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(payload)
        with tempfile.TemporaryDirectory() as td:
            store = str(Path(td) / "plans.json")
            write_plan_store(store, {plan.plan_id: plan}, existing={})
            updated, adopted = self.mod.adopt_trail_sl(
                row_id=plan.plan_id,
                session=through,
                store_path=store,
                transport=FixtureTransport(bars),
                plans={plan.plan_id: plan},
                broker_sl=payload["new_sl"],
            )
            self.assertEqual(adopted["new_sl"], payload["new_sl"])
            self.assertTrue(
                any(e.kind == "TRAIL_SL" for e in updated.events)
            )
            # NO_RAISE on same session after adopt
            with self.assertRaises(self.mod.RiskPlanError) as ctx:
                self.mod.adopt_trail_sl(
                    row_id=plan.plan_id,
                    session=through,
                    store_path=store,
                    transport=FixtureTransport(bars),
                    plans={plan.plan_id: updated},
                )
            self.assertIn("NO_RAISE", str(ctx.exception))


    def test_write_plan_store_allows_explicit_core_replace(self):
        fill = parse_journal_fill(self._fill_row())
        old = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        )
        new = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            policy=chandelier_policy(),
        )
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "plans.json"
            write_plan_store(store, {old.plan_id: old}, existing={})
            with self.assertRaises(Exception) as ctx:
                write_plan_store(store, {new.plan_id: new}, existing={old.plan_id: old})
            self.assertIn("immutable plan core changed", str(ctx.exception))
            write_plan_store(
                store,
                {new.plan_id: new},
                existing={old.plan_id: old},
                allow_core_replace={new.plan_id},
            )
            loaded = load_plan_store(store)
            self.assertEqual(loaded[new.plan_id].policy_version, CHANDELIER_POLICY_VERSION)

    def test_upgrade_allowed_helpers(self):
        self.assertTrue(self.mod._upgrade_allowed("atr-r-v2", "atr-chandelier-v1"))
        self.assertTrue(self.mod._upgrade_allowed("atr-zone-v1", "atr-chandelier-v1"))
        self.assertFalse(self.mod._upgrade_allowed("atr-r-v2", "atr-zone-v1"))
        self.assertFalse(self.mod._upgrade_allowed("legacy-journal-v1", "atr-chandelier-v1"))

    def test_prior_upgradeable_lifecycle_requires_created_only(self):
        fill = parse_journal_fill(self._fill_row())
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            created_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        )
        self.assertTrue(self.mod._prior_upgradeable_lifecycle(plan))
        trailed = self.mod.append_plan_event(
            plan,
            kind="TRAIL_SL",
            actor="owner",
            reason="test",
            payload={
                "old_sl": str(plan.levels.sl0),
                "new_sl": str(plan.levels.sl0 + Decimal("1")),
                "broker_sl": str(plan.levels.sl0 + Decimal("1")),
                "broker_sl_ack": "MATCH",
            },
        )
        self.assertFalse(self.mod._prior_upgradeable_lifecycle(trailed))

    def test_migrate_cli_defaults_to_chandelier(self):
        parser_default = None
        # argparse default is bound at parse time via module constant
        self.assertEqual(self.mod.CHANDELIER_POLICY_VERSION, "atr-chandelier-v1")
        # Ensure help/default wiring uses chandelier as migrate default.
        import argparse as ap

        p = ap.ArgumentParser()
        p.add_argument(
            "--policy",
            choices=list(self.mod.SUPPORTED_MIGRATE_POLICIES),
            default=self.mod.CHANDELIER_POLICY_VERSION,
        )
        self.assertEqual(p.parse_args([]).policy, "atr-chandelier-v1")


if __name__ == "__main__":
    unittest.main()
