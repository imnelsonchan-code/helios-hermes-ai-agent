#!/usr/bin/env python3
"""Unit tests for scripts/host/sleeve_paper_book.py (not copied to the live host)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
BOOK_PATH = HOST_DIR / "sleeve_paper_book.py"


def _load_module(name: str = "sleeve_paper_book"):
    if not BOOK_PATH.is_file():
        raise FileNotFoundError(f"missing {BOOK_PATH}")
    spec = importlib.util.spec_from_file_location(name, BOOK_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {BOOK_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


TM_PACK = {
    "as_of": "2026-09-01",
    "rows": [
        {"ticker": "AAA", "bracket": "BUY", "tm_score": 72, "close": 100.0},
        {"ticker": "BBB", "bracket": "BUY", "tm_score": 65, "last": 50.0},
        {"ticker": "CCC", "bracket": "WATCH", "tm_score": 70, "close": 20.0},
        {"ticker": "DDD", "bracket": "BUY", "tm_score": 55, "close": 10.0},
        {"ticker": "EEE", "bracket": "BUY", "tm_score": 80, "close": 40.0, "dmi_plus": 30, "dmi_minus": 35},
        {"ticker": "FFF", "bracket": "SELL", "tm_score": 90, "close": 30.0},
        {"ticker": "GGG", "bracket": "BUY", "tm_score": 88, "close": 25.0, "dmi_plus": 40, "dmi_minus": 20},
    ],
}

VALUE_PACK = {
    "as_of": "2026-09-01",
    "selected": [
        {"ticker": "AAA", "width_verdict": "Candidate", "valuation_score": 78, "close": 100.0},
        {"ticker": "HHH", "width_verdict": "green", "close": 200.0},
        {"ticker": "III", "width_verdict": "Watch", "close": 15.0},
        {"ticker": "JJJ", "status": "Candidate", "close": 10.0},
    ],
}


class SleevePaperBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_select_tm_tickers_filters_score_dmi_and_net_buy(self):
        tickers = self.mod.select_tm_tickers(TM_PACK)
        self.assertEqual(tickers, ["AAA", "BBB", "GGG"])

    def test_choppy_daily_verdict_is_not_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 92.2,
            "daily_bracket": ">=90",
            "daily_verdict": "NO SIGNAL (choppy market)",
            "raw_indicators": {"plus_di": 36.3, "minus_di": 18.5, "adx": 12.6},
        }
        self.assertFalse(self.mod._is_tm_buy_row(row))
        self.assertNotIn("MU", self.mod.select_tm_tickers({"results": [row]}))

    def test_nested_bullish_di_without_choppy_verdict_is_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 92.2,
            "daily_bracket": ">=90",
            "raw_indicators": {"plus_di": 36.3, "minus_di": 18.5},
        }
        self.assertTrue(self.mod._is_tm_buy_row(row))

    def test_nested_bearish_di_is_not_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 92.2,
            "raw_indicators": {"plus_di": 10.0, "minus_di": 20.0},
        }
        self.assertFalse(self.mod._is_tm_buy_row(row))

    def test_top_level_di_wins_over_nested(self):
        row = {
            "ticker": "MU",
            "tm_score": 80,
            "bracket": "BUY",
            "dmi_plus": 10,
            "dmi_minus": 30,
            "raw_indicators": {"plus_di": 40, "minus_di": 5},
        }
        self.assertFalse(self.mod._is_tm_buy_row(row))

    def test_score_below_min_still_not_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 59.9,
            "daily_verdict": "BUY",
            "raw_indicators": {"plus_di": 30, "minus_di": 10},
        }
        self.assertFalse(self.mod._is_tm_buy_row(row))

    def test_explicit_buy_verdict_with_bullish_di_stays_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 92.2,
            "daily_verdict": "BUY",
            "raw_indicators": {"plus_di": 36.3, "minus_di": 18.5},
        }
        self.assertTrue(self.mod._is_tm_buy_row(row))

    def test_engine_no_signal_underscore_is_not_a_buy(self):
        row = {
            "ticker": "MU",
            "daily_score": 70,
            "daily_verdict": "NO_SIGNAL (bearish trend)",
            "dmi_plus": 40,
            "dmi_minus": 10,
        }
        self.assertFalse(self.mod._is_tm_buy_row(row))

    def test_select_value_tickers_green_and_candidate_only(self):
        tickers = self.mod.select_value_tickers(VALUE_PACK)
        self.assertEqual(tickers, ["AAA", "HHH", "JJJ"])

    def test_watch_with_selected_status_excluded(self):
        pack = {
            "selected": [
                {
                    "ticker": "WATCH1",
                    "width_verdict": "Watch",
                    "status": "selected",
                    "close": 10.0,
                },
                {
                    "ticker": "PASS1",
                    "width_verdict": "Candidate",
                    "status": "selected",
                    "close": 11.0,
                },
                {"ticker": "LOOSE", "status": "pass", "close": 12.0},
            ]
        }
        self.assertEqual(self.mod.select_value_tickers(pack), ["PASS1"])

    def test_equal_weight_return_and_drawdown(self):
        marks = {"AAA": 110.0, "BBB": 45.0, "GGG": 30.0}
        book = self.mod.run_tm_book(
            TM_PACK,
            entry_marks={},
            mark_marks=marks,
            as_of="2026-09-01",
            mark_as_of="2026-09-10",
        )
        # per-name returns: +10%, -10%, +20% -> avg +6.667%
        self.assertEqual(book.trade_count, 3)
        self.assertAlmostEqual(book.return_pct, 6.6667, places=3)
        self.assertAlmostEqual(book.max_drawdown, 0.0, places=3)
        self.assertEqual(len(book.equity_curve), 2)
        self.assertIsNotNone(book.final_score)

    def test_risk_adjusted_penalizes_excess_drawdown(self):
        marks = {"AAA": 80.0, "BBB": 40.0, "GGG": 20.0}
        book = self.mod.run_tm_book(
            TM_PACK,
            entry_marks={},
            mark_marks=marks,
            as_of="2026-09-01",
            mark_as_of="2026-09-10",
            allowed_dd=8.0,
            penalty=1.0,
        )
        self.assertLess(book.return_pct, 0)
        self.assertGreater(book.max_drawdown, 8.0)
        self.assertAlmostEqual(
            book.risk_adjusted_score,
            book.return_pct - (book.max_drawdown - 8.0),
            places=3,
        )

    def test_empty_book_disqualified(self):
        empty = {"rows": [{"ticker": "ZZZ", "bracket": "BUY", "tm_score": 40, "close": 1.0}]}
        book = self.mod.run_tm_book(
            empty,
            entry_marks={},
            mark_marks={"ZZZ": 1.0},
            as_of="2026-09-01",
            mark_as_of="2026-09-10",
        )
        self.assertEqual(book.trade_count, 0)
        self.assertIsNone(book.final_score)
        self.assertTrue(book.disqualified)

    def test_dated_marks_equity_curve(self):
        dated = {
            "2026-09-01": {"AAA": 100.0, "BBB": 50.0, "GGG": 25.0},
            "2026-09-05": {"AAA": 95.0, "BBB": 40.0, "GGG": 24.0},
            "2026-09-10": {"AAA": 110.0, "BBB": 45.0, "GGG": 30.0},
        }
        book = self.mod.run_tm_book(
            TM_PACK,
            entry_marks=dated["2026-09-01"],
            dated_marks=dated,
            mark_dates=sorted(dated),
            as_of="2026-09-01",
            mark_as_of="2026-09-10",
        )
        self.assertEqual(len(book.equity_curve), 3)
        self.assertGreater(book.max_drawdown, 0.0)

    def test_both_sleeves_no_blended_score_in_cli_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tm_path = Path(tmp) / "tm.json"
            val_path = Path(tmp) / "val.json"
            out_path = Path(tmp) / "out.json"
            tm_path.write_text(json.dumps(TM_PACK), encoding="utf-8")
            val_path.write_text(json.dumps(VALUE_PACK), encoding="utf-8")
            marks = {
                "AAA": 110.0,
                "BBB": 45.0,
                "GGG": 30.0,
                "HHH": 210.0,
                "JJJ": 11.0,
            }
            rc = self.mod.main(
                [
                    "--sleeve",
                    "both",
                    "--tm-json",
                    str(tm_path),
                    "--value-json",
                    str(val_path),
                    "--marks-json",
                    json.dumps(marks),
                    "--out",
                    str(out_path),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertIn("tm", payload)
            self.assertIn("value", payload)
            self.assertNotIn("blended_final_score", payload)
            self.assertNotIn("final_score", payload)
            self.assertIn("never blend", payload["e5_note"])

    def test_value_book_independent_from_tm(self):
        marks = {"AAA": 120.0, "HHH": 180.0, "JJJ": 12.0}
        book = self.mod.run_value_book(
            VALUE_PACK,
            entry_marks={},
            mark_marks=marks,
            as_of="2026-09-01",
            mark_as_of="2026-09-10",
        )
        self.assertEqual(book.sleeve, "value")
        self.assertEqual(book.trade_count, 3)
        self.assertAlmostEqual(book.return_pct, 10.0, places=3)


if __name__ == "__main__":
    unittest.main()
