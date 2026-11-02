#!/usr/bin/env python3
"""Unit tests for scripts/host/position_watch.py (not copied to the live host)."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
WATCH_PATH = HOST_DIR / "position_watch.py"


def _load(name: str = "position_watch"):
    spec = importlib.util.spec_from_file_location(name, WATCH_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {WATCH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _row(
    ticker: str,
    action: str,
    status: str,
    shares,
    price,
    sl="",
    tp1="",
    tp2="",
    notes="",
    date_s="2026-09-08",
    price_usd="",
    total_usd="",
    gbp_amount="",
    row_id="",
) -> dict:
    return {
        "Date": date_s,
        "Ticker": ticker,
        "Action": action,
        "Shares": str(shares),
        "Price": str(price),
        "Price USD": "" if price_usd == "" else str(price_usd),
        "Total USD": "" if total_usd == "" else str(total_usd),
        "GBP Amount": "" if gbp_amount == "" else str(gbp_amount),
        "SL": "" if sl == "" else str(sl),
        "TP1": "" if tp1 == "" else str(tp1),
        "TP2": "" if tp2 == "" else str(tp2),
        "Status": status,
        "Notes": notes,
        "RowID": row_id,
    }


def _tst1_fixture() -> list[dict]:
    ack = "PARTIAL_EXIT_ACK remaining 32 OPEN"
    return [
        _row(
            "TST1.L",
            "BUY",
            "OPEN",
            100,
            60.08,
            sl=61.00,
            tp1=63.00,
            tp2=64.00,
            notes=f"KELLY_OVERRIDE | {ack}",
            date_s="2026-08-05",
            gbp_amount=6008.00,
        ),
        _row("TST1.L", "SELL", "VOID", 50, 63.11, gbp_amount=3155.5),
        _row("TST1.L", "SELL", "CLOSED", 25, 63.4, date_s="2026-08-12", gbp_amount=1585.0),
        _row("TST1.L", "SELL", "CLOSED", 10, 65.05, date_s="2026-08-21"),
        _row("TST1.L", "SELL", "CLOSED", 33, 65.69, date_s="2026-08-28", gbp_amount=2167.77),
        _row(
            "ACME",
            "BUY",
            "OPEN",
            50,
            249.40,
            sl=330.00,
            tp1=351.00,
            tp2=373.00,
            notes="Synthetic buy",
            date_s="2026-09-08",
            price_usd=336.32,
            total_usd=16815.75,
            gbp_amount=12469.97,
            row_id="acme-entry",
        ),
        _row(
            "BETA",
            "BUY",
            "OPEN",
            50,
            292.01,
            sl=382.00,
            tp1=411.00,
            tp2=431.00,
            notes="Synthetic buy",
            date_s="2026-09-08",
            price_usd=393.78,
            total_usd=19688.79,
            gbp_amount=14600.51,
        ),
        _row("EMPTYSL", "BUY", "OPEN", 10, 20.0, sl="", tp1=22.0, tp2=24.0, total_usd=200),
    ]


class PositionWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.session = date(2026, 9, 9)
        cls.rows = _tst1_fixture()
        cls.positions = cls.mod.compute_open_positions(cls.rows, gbp_usd_rate=1.31)

    def _by_ticker(self):
        return {p.ticker: p for p in self.positions}

    def test_tst1_remaining_32_void_ignored(self):
        tst1 = self._by_ticker()["TST1.L"]
        self.assertEqual(tst1.remaining, 32)
        self.assertTrue(tst1.ack)
        self.assertTrue(tst1.kelly_override)
        self.assertTrue(tst1.etf)
        self.assertEqual(tst1.sl, 61.0)
        self.assertEqual(tst1.tp1, 63.0)
        self.assertEqual(tst1.tp2, 64.0)

    def test_acme_beta_remaining(self):
        by = self._by_ticker()
        self.assertEqual(by["ACME"].remaining, 50)
        self.assertEqual(by["BETA"].remaining, 50)

    def test_empty_sl_filled_tp(self):
        empty = self._by_ticker()["EMPTYSL"]
        self.assertIsNone(empty.sl)
        self.assertEqual(empty.tp1, 22.0)

    def test_join_tm_unh_last_and_score_googl_na_tst1_na(self):
        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        self.mod.join_tm(positions, {"BETA": {"tm_score": 58.4, "last": 400.84}})
        by = {p.ticker: p for p in positions}
        self.assertEqual(by["BETA"].last, 400.84)
        self.assertEqual(by["BETA"].tm_score, 58.4)
        self.assertIsNone(by["ACME"].last)
        self.assertIsNone(by["ACME"].tm_score)
        self.assertIsNone(by["TST1.L"].last)
        self.assertIsNone(by["TST1.L"].tm_score)

    def test_tst1_strips_tm_even_if_present(self):
        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        self.mod.join_tm(positions, {"TST1.L": {"tm_score": 80, "last": 62.0}})
        tst1 = {p.ticker: p for p in positions}["TST1.L"]
        self.assertIsNone(tst1.tm_score)
        self.assertIsNone(tst1.last)

    def test_daily_score_maps_to_tm_score_column(self):
        with tempfile.TemporaryDirectory() as td:
            tm_dir = Path(td)
            payload = {
                "date": "2026-09-09",
                "results": [
                    {"ticker": "BETA", "daily_score": 58.4, "price": 400.84, "score": 1},
                ],
            }
            (tm_dir / "2026-09-09-data.json").write_text(json.dumps(payload), encoding="utf-8")
            mapped, src = self.mod.load_same_date_tm(str(tm_dir), self.session)
            self.assertEqual(src, "2026-09-09-data.json")
            self.assertEqual(mapped["BETA"]["tm_score"], 58.4)
            self.assertEqual(mapped["BETA"]["last"], 400.84)

    def test_stale_json_not_used(self):
        with tempfile.TemporaryDirectory() as td:
            tm_dir = Path(td)
            payload = {"results": [{"ticker": "BETA", "daily_score": 99, "price": 1}]}
            (tm_dir / "2026-09-08-data.json").write_text(json.dumps(payload), encoding="utf-8")
            mapped, src = self.mod.load_same_date_tm(str(tm_dir), self.session)
            self.assertEqual(src, "missing")
            self.assertEqual(mapped, {})

    def test_through_sl_and_not_near_3pct(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)],
            gbp_usd_rate=1.31,
        )
        self.mod.join_tm(positions, {"AAA": {"tm_score": 70, "last": 94.0}})
        positions[0].market_valid = True
        flags = self.mod.build_flags(positions, self.session, [])
        kinds = [f.kind for f in flags]
        self.assertIn("SL-breach", kinds)
        self.assertNotIn("near SL", kinds)
        texts = " ".join(f.text for f in flags)
        self.assertNotIn("3%", texts)

    def test_file_has_time_stop_telegram_does_not(self):
        from market_data import DailyBar

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        by = {p.ticker: p for p in positions}
        tst1 = by["TST1.L"]
        # MFE_close < 1R required for time-stop; latch path must be writable.
        tst1.risk_per_share = 2.0
        tst1.market_bars = (
            DailyBar(
                session=date(2026, 8, 5),
                open=Decimal("60.08"),
                high=Decimal("60.50"),
                low=Decimal("59.50"),
                close=Decimal("60.20"),
                volume=1000,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            flags = self.mod.build_flags(
                positions, self.session, [], time_stop_latch_path=latch
            )
        tst1_exit = [f for f in flags if f.kind == "exit" and "TST1.L" in f.text]
        self.assertTrue(tst1_exit)
        self.assertTrue(all(not f.telegram for f in tst1_exit))
        tel = self.mod.telegram_lines(flags)
        kelly = [f for f in flags if f.kind == "Kelly"]
        ack = [f for f in flags if f.kind == "ACK"]
        self.assertTrue(any("ACME" in f.text for f in kelly))
        self.assertTrue(any("BETA" in f.text for f in kelly))
        self.assertTrue(any("TST1.L" in f.text for f in ack))
        self.assertTrue(all(not f.telegram for f in kelly + ack))
        self.assertFalse(any("Kelly over cap" in t for t in tel))
        self.assertFalse(any("PARTIAL_EXIT_ACK" in t for t in tel))
        self.assertFalse(any("10-day" in t for t in tel))
        self.assertFalse(any("TST1.L" in t and t.startswith("Kelly") for t in tel))

    def test_time_stop_skipped_when_mfe_ge_1r(self):
        from market_data import DailyBar

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        tst1 = next(p for p in positions if p.ticker == "TST1.L")
        tst1.risk_per_share = 1.0
        tst1.market_bars = (
            DailyBar(
                session=date(2026, 8, 5),
                open=Decimal("60.08"),
                high=Decimal("65"),
                low=Decimal("59"),
                close=Decimal("62.08"),  # +2R
                volume=1000,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            flags = self.mod.build_flags(
                positions, self.session, [], time_stop_latch_path=latch
            )
        tst1_time = [
            f
            for f in flags
            if f.kind == "exit" and "TST1.L" in f.text and "10-day" in f.text
        ]
        self.assertEqual(tst1_time, [])

    def test_tst1_kelly_override_skips_kelly(self):
        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        flags = self.mod.build_flags(positions, self.session, [])
        kelly_tst1 = [f for f in flags if f.kind == "Kelly" and "TST1" in f.text]
        self.assertEqual(kelly_tst1, [])

    def test_empty_book_copy(self):
        audit = self.mod.build_final_audit([], [], "missing", {})
        md = self.mod.render_markdown(self.session, [], [], "missing", audit)
        self.assertIn("No OPEN positions today", md)
        self.assertNotIn("No extra attention today", md)
        self.assertIn("Not investment advice", md)
        self.assertIn("tm_score", md)
        self.assertNotIn("| score |", md.lower())
        self.assertNotIn("valuation_score", md)
        self.assertNotIn("| ATR14", md)
        self.assertNotIn("| Risk%", md)
        self.assertIn("## Final audit", md)
        self.assertIn("no LLM", md)

    def test_missing_journal_exit_2(self):
        code, md, bullets = self.mod.run(
            journal_path="/no/such/journal.csv",
            session=self.session,
            tm_dir="/tmp",
            width_dir="/tmp",
            out_dirs=[],
            write=False,
        )
        self.assertEqual(code, 2)
        self.assertEqual(md, "")
        self.assertEqual(bullets, [])

    def test_lot_conflict(self):
        rows = [
            _row("ZZZ", "BUY", "OPEN", 10, 10, sl=9, tp1=12, total_usd=100, date_s="2026-09-08", row_id="z1"),
            _row("ZZZ", "BUY", "OPEN", 10, 11, sl=8, tp1=12, total_usd=110, date_s="2026-09-08", row_id="z2"),
        ]
        positions = self.mod.compute_open_positions(rows, gbp_usd_rate=1.31)
        self.assertEqual(len(positions), 2)
        self.assertEqual({p.sl for p in positions}, {9.0, 8.0})
        self.assertFalse(any(p.sl_conflict for p in positions))
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any("inconsistent" in f.text for f in flags))

    def test_write_three_layers_and_stdout_not_table(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            journal = root / "j.csv"
            fieldnames = list(_tst1_fixture()[0].keys())
            with journal.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(_tst1_fixture())
            tm_dir = root / "tm"
            tm_dir.mkdir()
            (tm_dir / "2026-09-09-data.json").write_text(
                json.dumps({"results": [{"ticker": "BETA", "daily_score": 58.4, "price": 400.84}]}),
                encoding="utf-8",
            )
            d1, d2, d3 = root / "a", root / "b", root / "c"
            code, md, bullets = self.mod.run(
                journal_path=str(journal),
                session=self.session,
                tm_dir=str(tm_dir),
                width_dir=str(root / "width"),
                out_dirs=[str(d1), str(d2), str(d3)],
                gbp_usd=1.31,
                write=True,
            )
            self.assertEqual(code, 0)
            name = "2026-09-09-position-watch.md"
            for folder in (d1, d2, d3):
                self.assertTrue((folder / name).is_file())
            self.assertIn("| BETA | 50 |", md)
            self.assertIn("$336.32", md)
            self.assertIn("$330.00", md)
            self.assertIn("$351.00", md)
            self.assertIn("$373.00", md)
            self.assertIn("£60.08", md)
            self.assertIn("£61.00", md)
            self.assertIn("£63.00", md)
            self.assertIn("£64.00", md)
            self.assertIn("$393.78", md)
            self.assertIn("$382.00", md)
            self.assertIn("N/A", md)  # ACME / TST1 tm_score
            self.assertFalse(any("Kelly" in b for b in bullets))
            self.assertTrue(any("Missing SL" in b for b in bullets))
            joined = "\n".join(bullets)
            self.assertNotIn("| Ticker |", joined)
            self.assertIn("Cost at entry", md)
            self.assertNotIn("Shares×Last", md)
            self.assertIn("## Final audit", md)
            self.assertIn("TST1.L 32", md)
            self.assertNotIn("**FAIL:**", md)
            self.assertNotIn("Final audit", joined)

    def test_e5_file_only(self):
        positions = [
            p for p in self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31) if p.ticker == "BETA"
        ]
        flags = self.mod.build_flags(positions, self.session, ["BETA", "ACT"])
        e5 = [f for f in flags if f.kind == "E5"]
        self.assertEqual(len(e5), 1)
        self.assertFalse(e5[0].telegram)
        self.assertNotIn("valuation_score", e5[0].text)

    def test_row_prices_follow_entry_currency(self):
        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        md = self.mod.render_markdown(self.session, positions, [], "missing")
        googl = next(ln for ln in md.splitlines() if ln.startswith("| ACME |"))
        tst1 = next(ln for ln in md.splitlines() if ln.startswith("| TST1.L |"))
        self.assertIn("$336.32", googl)
        self.assertIn("$330.00", googl)
        self.assertIn("$351.00", googl)
        self.assertIn("$373.00", googl)
        self.assertNotIn("£", googl)
        self.assertIn("£60.08", tst1)
        self.assertIn("£61.00", tst1)
        self.assertIn("£63.00", tst1)
        self.assertIn("£64.00", tst1)
        self.assertNotIn("$", tst1)

    def test_live_usd_fill_not_gbp_price(self):
        by = self._by_ticker()
        self.assertEqual(by["ACME"].entry, 336.32)
        self.assertEqual(by["BETA"].entry, 393.78)

    def test_price_usd_classifies_usd_when_total_is_zero(self):
        positions = self.mod.compute_open_positions(
            [
                _row(
                    "AAA",
                    "BUY",
                    "OPEN",
                    10,
                    75,
                    sl=98,
                    tp1=104,
                    price_usd=100,
                    total_usd=0,
                )
            ]
        )
        self.assertEqual(positions[0].native_ccy, "USD")
        self.assertEqual(positions[0].entry, 100)

    def test_sell_without_price_reduces_remaining(self):
        rows = [
            _row("AAA", "BUY", "OPEN", 10, 100, sl=95, total_usd=1000),
            _row("AAA", "SELL", "CLOSED", 4, "", total_usd=""),
        ]
        self.assertEqual(self.mod.compute_open_positions(rows)[0].remaining, 6)

    def test_blocked_plan_suppresses_price_comparisons(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.plan_state = "BLOCKED"
        pos.plan_issues = ["TRAIL_SL_LOWERED"]
        pos.last = 90
        pos.market_valid = True
        pos.low = 89
        flags = self.mod.build_flags(positions, self.session, [], shadow=True)
        self.assertFalse(any(f.kind in {"SL-breach", "past-TP", "intraday"} for f in flags))

    def test_unvalidated_tm_price_cannot_trigger_official_breach(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        positions[0].last = 90
        positions[0].market_source = "T&M"
        positions[0].market_valid = False
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any(f.kind == "SL-breach" for f in flags))

    def test_shadow_suppresses_adopted_plan_delivery(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.level_source = "PLAN"
        pos.plan_state = "ACTIVE"
        pos.last = 95
        pos.market_valid = True
        flags = self.mod.build_flags(positions, self.session, [], shadow=True)
        breach = [f for f in flags if f.kind == "SL-breach"]
        self.assertEqual(len(breach), 1)
        self.assertFalse(breach[0].telegram)

    def test_plan_must_match_bound_journal_fill(self):
        from risk_plan import create_plan, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        googl = next(pos for pos in positions if pos.ticker == "ACME")
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source)
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8"),
            atr_source="fixture",
        )
        bad = replace(plan, fill=replace(plan.fill, ticker="BBB"))
        self.mod.join_risk_plans(positions, {"acme-entry": bad}, self.rows)
        self.assertEqual(googl.plan_state, "BLOCKED")
        self.assertIn("PLAN_JOURNAL_BINDING_MISMATCH", googl.plan_issues)

    def test_tp1_not_repeated_after_confirmed_partial(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, tp2=120, total_usd=1000)]
        )
        pos = positions[0]
        pos.plan_state = "TP1_EXECUTED"
        pos.level_source = "PLAN"
        pos.last = 115
        pos.market_valid = True
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any("TP1" in f.text and f.kind == "past-TP" for f in flags))

    def test_close_equality_triggers_and_intraday_touch_is_file_only(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)],
            gbp_usd_rate=1.31,
        )
        pos = positions[0]
        pos.active_sl = 95
        pos.plan_tp1 = 110
        pos.plan_tp2 = 120
        pos.last = 95
        pos.market_valid = True
        pos.high = 109
        pos.low = 94
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertTrue(any(f.kind == "SL-breach" for f in flags))
        pos.last = 100
        flags = self.mod.build_flags(positions, self.session, [])
        touch = [f for f in flags if "SL_INTRADAY_TOUCH" in f.text]
        self.assertEqual(len(touch), 1)
        self.assertFalse(touch[0].telegram)

    def test_ambiguous_intraday_does_not_infer_order(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)],
            gbp_usd_rate=1.31,
        )
        pos = positions[0]
        pos.active_sl = 95
        pos.plan_tp1 = 110
        pos.last = 102
        pos.market_valid = True
        pos.low = 94
        pos.high = 111
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertTrue(any("AMBIGUOUS_INTRADAY" in f.text for f in flags))

    def test_telegram_dedupe_is_idempotent(self):
        flags = [self.mod.WatchFlag("SL-breach", True, "same alert")]
        with tempfile.TemporaryDirectory() as td:
            state = str(Path(td) / "alerts.json")
            first = self.mod.telegram_lines(flags, session=self.session, state_path=state)
            second = self.mod.telegram_lines(flags, session=self.session, state_path=state)
            self.assertEqual(first, ["same alert"])
            self.assertEqual(second, [])

    def test_telegram_unreadable_state_fail_closed(self):
        flags = [self.mod.WatchFlag("SL-breach", True, "same alert")]
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "alerts.json"
            state.write_text("{not-json", encoding="utf-8")
            out = self.mod.telegram_lines(
                flags, session=self.session, state_path=str(state)
            )
            self.assertEqual(out, [])

    def test_per_lot_plans_evaluate_separately(self):
        from risk_plan import create_plan, parse_journal_fill

        rows = [
            _row(
                "AAA",
                "BUY",
                "OPEN",
                10,
                100,
                sl=95,
                tp1=110,
                tp2=120,
                total_usd=1000,
                row_id="lot-a",
            ),
            _row(
                "AAA",
                "BUY",
                "OPEN",
                8,
                102,
                sl=96,
                tp1=112,
                tp2=122,
                total_usd=816,
                row_id="lot-b",
            ),
        ]
        positions = self.mod.compute_open_positions(rows, gbp_usd_rate=1.31)
        self.assertEqual(len(positions), 2)
        plans = {}
        for source in rows:
            fill = parse_journal_fill(source)
            plans[fill.row_id] = create_plan(
                fill,
                atr_session=date(2026, 9, 7),
                atr14=Decimal("2"),
                atr_source="fixture",
            )
        self.mod.join_risk_plans(positions, plans, rows)
        self.assertEqual(len(positions), 2)
        self.assertEqual({p.row_ids[0] for p in positions}, {"lot-a", "lot-b"})
        self.assertTrue(all(p.level_source == "PLAN" for p in positions))
        self.assertNotIn("PLAN_LOT_AMBIGUOUS", " ".join(p.plan_issues[0] if p.plan_issues else "" for p in positions))
        self.assertNotEqual(positions[0].plan_tp1, positions[1].plan_tp1)
        self.assertEqual(sum(p.remaining for p in positions), 18)

    def test_plan_view_levels_and_trail_event(self):
        from datetime import datetime, timezone
        from risk_plan import append_plan_event, create_plan, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source, yahoo_symbol="ACME")
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
        )
        plan = append_plan_event(
            plan,
            kind="TRAIL_SL",
            actor="owner",
            reason="protect",
            payload={"old_sl": "323.35", "new_sl": "338.00", "broker_sl": "338.00"},
            occurred_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        )
        self.mod.join_risk_plans(positions, {"acme-entry": plan}, self.rows)
        googl = next(pos for pos in positions if pos.ticker == "ACME")
        self.assertTrue(googl.trailed)
        self.assertEqual(googl.active_sl, 338.0)
        self.assertAlmostEqual(googl.plan_tp1, 362.27)
        self.assertAlmostEqual(googl.plan_tp2, 388.22)
        self.assertEqual(googl.yahoo_symbol, "ACME")
        self.assertEqual(googl.level_source, "PLAN")

    def test_join_market_uses_plan_symbol_and_active_sl(self):
        from market_data import DailyBar, MarketEvidence, MarketRequest

        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)],
            gbp_usd_rate=1.31,
        )
        pos = positions[0]
        pos.yahoo_symbol = "AAA.US"
        pos.active_sl = 93.5
        pos.entry_date = "2026-09-08"
        captured: dict = {}

        class StubMarket:
            def get_validated_evidence(self, request: MarketRequest):
                captured["request"] = request
                return MarketEvidence(
                    symbol=request.symbol,
                    session=request.expected_session,
                    currency="USD",
                    bar=DailyBar(
                        session=request.expected_session,
                        open=Decimal("100"),
                        high=Decimal("101"),
                        low=Decimal("99"),
                        close=Decimal("100.5"),
                    ),
                    retrieved_at="2026-09-09T23:00:00Z",
                    valid_for_breach=True,
                    issues=(),
                    gap_through_sl=False,
                )

        self.mod.join_market(positions, StubMarket(), self.session)
        req = captured["request"]
        self.assertEqual(req.symbol, "AAA.US")
        self.assertEqual(req.active_sl, Decimal("93.5"))
        self.assertEqual(positions[0].last, 100.5)
        self.assertTrue(positions[0].market_valid)

    def test_exchange_closed_is_file_only(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        positions[0].market_issues = ["EXCHANGE_CLOSED"]
        positions[0].market_source = "Yahoo"
        flags = self.mod.build_flags(positions, self.session, [])
        data = [f for f in flags if f.kind == "data"]
        self.assertEqual(len(data), 1)
        self.assertFalse(data[0].telegram)
        audit = self.mod.build_final_audit(positions, flags, "missing", {})
        self.assertTrue(any(status == "N/A" and "session closed" in text for status, text in audit))

    def test_gap_through_sl_telegrams_unless_shadow(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.gap_through_sl = True
        pos.last = 90
        pos.active_sl = 95
        pos.market_valid = True
        pos.level_source = "PLAN"
        pos.plan_state = "ACTIVE"
        live = [f for f in self.mod.build_flags(positions, self.session, []) if f.kind == "gap-SL"]
        self.assertEqual(len(live), 1)
        self.assertTrue(live[0].telegram)
        shadowed = [
            f
            for f in self.mod.build_flags(positions, self.session, [], shadow=True)
            if f.kind == "gap-SL"
        ]
        self.assertFalse(shadowed[0].telegram)

    def test_journal_only_cut_loss_is_file_only(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)],
            gbp_usd_rate=1.31,
        )
        self.mod.join_tm(positions, {"AAA": {"tm_score": 70, "last": 94.0}})
        positions[0].market_valid = True
        positions[0].level_source = "JOURNAL"
        positions[0].plan_state = "JOURNAL_ONLY"
        flags = self.mod.build_flags(positions, self.session, [])
        cut = [f for f in flags if f.kind == "SL-breach"]
        self.assertTrue(cut)
        self.assertTrue(all(not f.telegram for f in cut))

    def test_nav_gate_is_file_only(self):
        positions = self.mod.compute_open_positions(
            [_row("BBB", "BUY", "OPEN", 10000, 100, sl=1, tp1=120, gbp_amount=1000000)]
        )
        flags = self.mod.build_flags(positions, self.session, [])
        nav = [f for f in flags if f.kind == "NAV"]
        self.assertTrue(nav)
        self.assertTrue(all(not f.telegram for f in nav))
        self.assertTrue(any("LOT_RISK_EXCESS" in f.text or "BOOK_RISK_EXCESS" in f.text for f in nav))

    def test_unattributed_closed_sell_is_fifo(self):
        rows = [
            _row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000, row_id="lot-a"),
            _row("AAA", "BUY", "OPEN", 8, 102, sl=96, tp1=112, total_usd=816, row_id="lot-b"),
            _row("AAA", "SELL", "CLOSED", 4, 101, total_usd=404),
        ]
        positions = self.mod.compute_open_positions(rows)
        by_id = {p.row_ids[0]: p.remaining for p in positions}
        self.assertEqual(by_id, {"lot-a": 6, "lot-b": 8})

    def test_open_sell_does_not_reduce_remaining(self):
        rows = [
            _row("AAA", "BUY", "OPEN", 10, 100, sl=95, total_usd=1000),
            _row("AAA", "SELL", "OPEN", 4, 101, total_usd=404),
        ]
        self.assertEqual(self.mod.compute_open_positions(rows)[0].remaining, 10)

    def test_mixed_row_id_keeps_unlabelled_lot(self):
        from risk_plan import create_plan, parse_journal_fill

        rows = [
            _row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000, row_id="lot-a"),
            _row("AAA", "BUY", "OPEN", 8, 102, sl=96, tp1=112, total_usd=816),
        ]
        positions = self.mod.compute_open_positions(rows)
        fill = parse_journal_fill(rows[0])
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("2"),
            atr_source="fixture",
        )
        self.mod.join_risk_plans(positions, {"lot-a": plan}, rows)
        self.assertEqual(len(positions), 2)
        states = {tuple(p.row_ids): p.plan_state for p in positions}
        self.assertEqual(states[("lot-a",)], "ACTIVE")
        self.assertEqual(states[()], "JOURNAL_ONLY")

    def test_gap_without_valid_bar_does_not_alert(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.gap_through_sl = True
        pos.market_valid = False
        pos.last = 90
        pos.active_sl = 95
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any(f.kind == "gap-SL" for f in flags))

    def test_closed_remaining_skips_sl_compare(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl=95, tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.remaining = 0
        pos.plan_state = "CLOSED"
        pos.level_source = "PLAN"
        pos.last = 90
        pos.active_sl = 95
        pos.market_valid = True
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any(f.kind == "SL-breach" for f in flags))

    def test_missing_journal_sl_ok_when_plan_has_active_sl(self):
        positions = self.mod.compute_open_positions(
            [_row("AAA", "BUY", "OPEN", 10, 100, sl="", tp1=110, total_usd=1000)]
        )
        pos = positions[0]
        pos.active_sl = 97.0
        pos.level_source = "PLAN"
        pos.plan_state = "ACTIVE"
        flags = self.mod.build_flags(positions, self.session, [])
        self.assertFalse(any(f.kind == "missing-SL" for f in flags))

    def test_telegram_null_state_fail_closed(self):
        flags = [self.mod.WatchFlag("SL-breach", True, "same alert")]
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "alerts.json"
            state.write_text("null", encoding="utf-8")
            out = self.mod.telegram_lines(
                flags, session=self.session, state_path=str(state)
            )
            self.assertEqual(out, [])

    def test_final_audit_etf_and_missing_tm(self):
        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        flags = self.mod.build_flags(positions, self.session, [])
        audit = self.mod.build_final_audit(positions, flags, "missing", {})
        by = {text: status for status, text in audit}
        self.assertTrue(any(s == "N/A" and "T&M JSON missing" in t for s, t in audit))
        self.assertTrue(any("TST1.L 32" in t and s == "PASS" for s, t in audit))
        self.assertTrue(any("PARTIAL_EXIT_ACK" in t and "TST1.L 32" in t for s, t in audit))
        self.assertFalse(any(s == "FAIL" for s, _t in audit))
        self.assertTrue(any("ETF/LSE" in t for t in by))

    def test_import_does_not_mkdir_home(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"HOME": td}):
                isolated = _load("position_watch_nohome")
                isolated.compute_open_positions(_tst1_fixture(), gbp_usd_rate=1.31)
            self.assertFalse((Path(td) / ".hermes").exists())

    def test_zone_flag_is_file_only(self):
        from market_data import ZoneEvidence
        from risk_plan import create_plan_with_zone, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source)
        plan = create_plan_with_zone(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8"),
            atr_source="fixture",
            zone=ZoneEvidence(
                status="OK",
                reason_code="OK",
                mode="VPDC",
                zone_lo=Decimal("320.5"),
                zone_hi=Decimal("322"),
                through_session=date(2026, 9, 7),
                window_start=date(2026, 8, 11),
                window_end=date(2026, 9, 7),
                bars_used=20,
                bin_size=Decimal("0.8"),
                mass=Decimal("1000"),
                total_mass=Decimal("2000"),
                width=Decimal("2.4"),
            ),
        )
        self.mod.join_risk_plans(positions, {"acme-entry": plan}, self.rows)
        flags = self.mod.build_flags(positions, self.session, [])
        zone_flags = [f for f in flags if f.kind == "ZONE" and "ACME" in f.text]
        self.assertEqual(len(zone_flags), 1)
        self.assertFalse(zone_flags[0].telegram)
        self.assertIn("status=OK", zone_flags[0].text)

    def test_chandelier_trail_file_only_and_hides_tp2(self):
        from market_data import DailyBar, SplitEvent
        from risk_plan import chandelier_policy, create_plan, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source)
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
            policy=chandelier_policy(),
        )
        self.mod.join_risk_plans(positions, {"acme-entry": plan}, self.rows)
        googl = next(pos for pos in positions if pos.ticker == "ACME")
        self.assertIsNone(googl.plan_tp2)
        googl.market_valid = True
        googl.last = 360.0
        googl.high = 365.0
        googl.low = 350.0
        # Bars with a clear raise vs SL0≈323.
        start = date(2026, 8, 20)
        bars = []
        for i in range(25):
            session = start + timedelta(days=i)
            close = Decimal("360") if session >= date(2026, 9, 8) else Decimal("336")
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
        googl.market_bars = tuple(bars)
        googl.market_splits = ()
        self.mod.join_trail_proposals(
            positions, {"acme-entry": plan}, bars[-1].session
        )
        self.assertIsNotNone(googl.proposed_trail)
        flags = self.mod.build_flags(positions, bars[-1].session, [])
        trail_flags = [f for f in flags if f.kind == "TRAIL" and "ACME" in f.text]
        self.assertTrue(trail_flags)
        self.assertTrue(all(not f.telegram for f in trail_flags))
        self.assertFalse(any("past TP2" in f.text or "TP2_INTRADAY" in f.text for f in flags))
        md = self.mod.render_markdown(
            bars[-1].session, positions, flags, "fixture.json", []
        )
        # Chandelier row should show em dash for TP2, not journal 373.
        self.assertIn("CHANDELIER", md)
        googl_line = next(line for line in md.splitlines() if line.startswith("| ACME"))
        self.assertNotIn("373", googl_line)

    def _googl_bars(self, close_after_fill: Decimal):
        from market_data import DailyBar

        start = date(2026, 8, 20)
        bars = []
        for i in range(25):
            session = start + timedelta(days=i)
            close = close_after_fill if session >= date(2026, 9, 8) else Decimal("336")
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
        return bars

    def test_legacy_shadow_compare_only_on_no_raise(self):
        from risk_plan import create_plan, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source)
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
        )
        self.mod.join_risk_plans(positions, {"acme-entry": plan}, self.rows)
        googl = next(pos for pos in positions if pos.ticker == "ACME")
        googl.market_valid = True
        bars = self._googl_bars(Decimal("336"))
        googl.market_bars = tuple(bars)
        googl.market_splits = ()
        self.mod.join_trail_proposals(
            positions, {"acme-entry": plan}, bars[-1].session
        )
        self.assertIsNone(googl.proposed_trail)
        self.assertIsNotNone(googl.trail_shadow_compare)
        self.assertEqual(googl.trail_shadow_compare["compare_only"], "NO_RAISE")
        self.assertFalse(googl.trail_propose_issues)
        flags = self.mod.build_flags(positions, bars[-1].session, [])
        compare = [f for f in flags if "SHADOW_CHANDELIER_COMPARE" in f.text]
        trail = [f for f in flags if "SHADOW_CHANDELIER_TRAIL" in f.text]
        self.assertEqual(len(compare), 1)
        self.assertFalse(compare[0].telegram)
        self.assertIn("NO_RAISE", compare[0].text)
        self.assertIn("raw_sl=", compare[0].text)
        self.assertIn("hc=", compare[0].text)
        self.assertIn("atr=", compare[0].text)
        self.assertFalse(trail)

    def test_legacy_shadow_trail_flag_on_raise(self):
        from risk_plan import create_plan, parse_journal_fill

        positions = self.mod.compute_open_positions(self.rows, gbp_usd_rate=1.31)
        source = next(row for row in self.rows if row.get("RowID") == "acme-entry")
        fill = parse_journal_fill(source)
        plan = create_plan(
            fill,
            atr_session=date(2026, 9, 7),
            atr14=Decimal("8.65"),
            atr_source="fixture",
        )
        self.mod.join_risk_plans(positions, {"acme-entry": plan}, self.rows)
        googl = next(pos for pos in positions if pos.ticker == "ACME")
        googl.market_valid = True
        bars = self._googl_bars(Decimal("360"))
        googl.market_bars = tuple(bars)
        googl.market_splits = ()
        self.mod.join_trail_proposals(
            positions, {"acme-entry": plan}, bars[-1].session
        )
        self.assertIsNotNone(googl.proposed_trail)
        self.assertIsNone(googl.trail_shadow_compare)
        self.assertTrue(googl.trail_shadow_legacy)
        flags = self.mod.build_flags(positions, bars[-1].session, [])
        trail = [f for f in flags if "SHADOW_CHANDELIER_TRAIL" in f.text]
        compare = [f for f in flags if "SHADOW_CHANDELIER_COMPARE" in f.text]
        self.assertEqual(len(trail), 1)
        self.assertFalse(trail[0].telegram)
        self.assertFalse(compare)

    def test_comment_stub_and_preserve_on_rewrite(self):
        audit = self.mod.build_final_audit([], [], "missing", {})
        md = self.mod.render_markdown(self.session, [], [], "missing", audit)
        self.assertIn("## Final audit", md)
        self.assertIn(self.mod.COMMENT_HEADING, md)
        self.assertLess(md.index("## Final audit"), md.index(self.mod.COMMENT_HEADING))
        stub_line = "Renee: trend only. Eliza: value only. Christina: rates/bonds only. Emily: commodities only."
        filled = md.replace(
            stub_line,
            "### AVGO · short-term · lead renee\n- SL: hold $344\n",
        )
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            name = f"{self.session.isoformat()}-position-watch.md"
            (folder / name).write_text(filled, encoding="utf-8")
            written = self.mod.write_layers(md, self.session, [str(folder)])
            saved = Path(written[0]).read_text(encoding="utf-8")
        self.assertIn("### AVGO · short-term · lead renee", saved)
        self.assertIn("- SL: hold $344", saved)
        self.assertEqual(saved.count(self.mod.COMMENT_HEADING), 1)
        self.assertIn("No OPEN positions today", saved)


if __name__ == "__main__":
    unittest.main()

