#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
CHECKER_PATH = HOST_DIR / "exit_signal_checker.py"
TIME_STOP_PATH = HOST_DIR / "time_stop.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ExitSignalCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts = _load("time_stop", TIME_STOP_PATH)
        cls.mod = _load("exit_signal_checker", CHECKER_PATH)

    def test_partial_closed_sell_leaves_open_remainder(self):
        rows = [
            {"Ticker": "TST1.L", "Action": "BUY", "Shares": "100", "Status": "OPEN", "Date": "2026-08-05"},
            {"Ticker": "TST1.L", "Action": "SELL", "Shares": "25", "Status": "CLOSED", "Date": "2026-08-12"},
            {"Ticker": "TST1.L", "Action": "SELL", "Shares": "10", "Status": "CLOSED", "Date": "2026-08-21"},
            {"Ticker": "TST1.L", "Action": "SELL", "Shares": "33", "Status": "CLOSED", "Date": "2026-08-28"},
            {"Ticker": "TST1.L", "Action": "SELL", "Shares": "50", "Status": "VOID", "Date": "2026-08-10"},
        ]
        positions = self.mod.compute_open_book(rows)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].remaining, 32)

    def test_daily_score_field_not_missing_total(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "2026-09-09-data.json").write_text(
                json.dumps({"results": [{"ticker": "BETA", "daily_score": 48.5}]}),
                encoding="utf-8",
            )
            scores, source = self.mod.load_scores(str(folder), date(2026, 9, 9))
            self.assertEqual(scores, {"BETA": 48.5})
            self.assertEqual(source, "2026-09-09-data.json")

    def test_score_and_time_are_separate_from_price_levels(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            signals = self.mod.find_exit_signals(
                [position],
                {"BETA": 49},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("0.4")},
                latch_path=latch,
            )
        text = " ".join(signals[0]["reasons"])
        self.assertIn("Signal decay", text)
        self.assertIn("Time stop", text)
        self.assertNotIn("SL", text)
        self.assertNotIn("TP", text)

    def test_reentry_age_starts_from_current_position_cycle(self):
        rows = [
            {"Ticker": "AAA", "Action": "BUY", "Shares": "10", "Status": "CLOSED", "Date": "2026-01-01"},
            {"Ticker": "AAA", "Action": "SELL", "Shares": "10", "Status": "CLOSED", "Date": "2026-01-10"},
            {"Ticker": "AAA", "Action": "BUY", "Shares": "5", "Status": "OPEN", "Date": "2026-09-08"},
        ]
        position = self.mod.compute_open_book(rows)[0]
        self.assertEqual(position.remaining, 5)
        self.assertEqual(position.entry_date, "2026-09-08")

    def test_time_stop_skipped_when_mfe_ge_1r(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            signals = self.mod.find_exit_signals(
                [position],
                {"BETA": 60},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("1.5")},
                latch_path=latch,
            )
        self.assertEqual(signals, [])

    def test_time_stop_skipped_when_mfe_missing(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        signals = self.mod.find_exit_signals(
            [position],
            {"BETA": 60},
            date(2026, 9, 9),
            mfe_close_r={},
            latch_path=None,
        )
        self.assertEqual(signals, [])

    def test_time_stop_fires_once_then_latched(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            first = self.mod.find_exit_signals(
                [position],
                {"BETA": 60},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("0.2")},
                latch_path=latch,
            )
            self.assertEqual(len(first), 1)
            self.assertIn("Time stop", first[0]["reasons"][0])
            second = self.mod.find_exit_signals(
                [position],
                {"BETA": 60},
                date(2026, 9, 10),
                mfe_close_r={"BETA": Decimal("0.2")},
                latch_path=latch,
            )
            self.assertEqual(second, [])

    def test_parse_failure_does_not_trip_time_stop(self):
        self.assertIsNone(self.mod.count_trading_days("not-a-date", date(2026, 9, 9)))
        position = self.mod.OpenBookPosition("BETA", 50, "bogus")
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            signals = self.mod.find_exit_signals(
                [position],
                {},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("0.1")},
                latch_path=latch,
            )
        self.assertEqual(signals, [])


    def test_corrupt_latch_fails_closed(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        with tempfile.TemporaryDirectory() as td:
            latch = Path(td) / "latch.json"
            latch.write_text("{not-json", encoding="utf-8")
            signals = self.mod.find_exit_signals(
                [position],
                {"BETA": 60},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("0.2")},
                latch_path=str(latch),
            )
        self.assertEqual(signals, [])

    def test_dry_run_still_latches(self):
        position = self.mod.OpenBookPosition("BETA", 50, "2026-08-01")
        with tempfile.TemporaryDirectory() as td:
            latch = str(Path(td) / "latch.json")
            first = self.mod.find_exit_signals(
                [position],
                {},
                date(2026, 9, 9),
                mfe_close_r={"BETA": Decimal("0.2")},
                latch_path=latch,
                write_latch=True,
            )
            self.assertEqual(len(first), 1)
            second = self.mod.find_exit_signals(
                [position],
                {},
                date(2026, 9, 10),
                mfe_close_r={"BETA": Decimal("0.2")},
                latch_path=latch,
                write_latch=True,
            )
            self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
