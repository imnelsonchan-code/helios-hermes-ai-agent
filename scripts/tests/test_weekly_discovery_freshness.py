#!/usr/bin/env python3
"""Freshness window for width-scan discoveries, plus §5 missing-entry rows.

The weekly modules import pandas at load time. These tests call the functions
from source when that import is unavailable, and use the live module when it is.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKTEST = Path(__file__).resolve().parents[1] / "host" / "backtest"
INDICATOR = BACKTEST / "weekly_indicator_update.py"
REPORT_GEN = BACKTEST / "weekly_report_gen.py"


def _exec_functions(path: Path, names: list[str]) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    found = {node.name for node in selected}
    missing = [name for name in names if name not in found]
    if missing:
        raise AssertionError(f"{path.name} missing {missing}")
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "__builtins__": __builtins__,
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _filter_new_discovery():
    try:
        mod = _load_module(INDICATOR, "weekly_indicator_update_freshness")
        return mod.filter_new_discovery
    except (ImportError, ModuleNotFoundError, AttributeError):
        ns = _exec_functions(INDICATOR, ["filter_new_discovery"])
        return ns["filter_new_discovery"]


def _render_additions_block():
    try:
        mod = _load_module(REPORT_GEN, "weekly_report_gen_additions")
        return mod.render_additions_block
    except (ImportError, ModuleNotFoundError, AttributeError):
        ns = _exec_functions(
            REPORT_GEN, ["_sig_label", "render_additions_block"]
        )
        return ns["render_additions_block"]


def _addition_row(ticker: str, entry, score: float):
    return {
        "ticker": ticker,
        "company": f"{ticker} Co",
        "sector": "Tech",
        "score_total": score,
        "verdict": "BUY",
        "raw": {"adx": 22, "rsi": 58, "volume_ratio": 1.4},
        "entry": entry,
    }


def _additions_ds(row: dict) -> dict:
    return {
        "width_additions": {"tickers": [row["ticker"]], "ge60": 1},
        "rows": [row],
    }


class WeeklyDiscoveryFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.filter_new_discovery = staticmethod(_filter_new_discovery())
        cls.render_additions_block = staticmethod(_render_additions_block())

    def test_scan_time_seven_weeks_ago_dropped(self):
        discoveries = [{"ticker": "AAA", "score_total": 71.5}]
        scanned = (datetime.now(timezone.utc) - timedelta(weeks=7)).isoformat()
        kept, status = self.filter_new_discovery(
            {
                "scan_time": scanned,
                "week_end": "2026-09-04",
                "discoveries": discoveries,
            },
            "2026-10-23",
        )
        self.assertEqual(kept, [])
        self.assertEqual(status, "stale_dropped")
        self.assertEqual(discoveries[0]["score_total"], 71.5)

    def test_scan_time_six_days_ago_kept(self):
        discoveries = [{"ticker": "BBB", "score_total": 64.0}]
        aware = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        kept, status = self.filter_new_discovery(
            {"scan_time": aware, "discoveries": discoveries},
            "2026-10-23",
        )
        self.assertEqual(status, "ok")
        self.assertIs(kept, discoveries)
        self.assertEqual(kept[0]["score_total"], 64.0)

        naive = (datetime.now(timezone.utc) - timedelta(days=6)).replace(tzinfo=None)
        naive_rows = [{"ticker": "BBB", "score_total": 64.0}]
        kept_naive, naive_status = self.filter_new_discovery(
            {"scan_time": naive.isoformat(), "discoveries": naive_rows},
            "2026-10-23",
        )
        self.assertEqual(naive_status, "ok")
        self.assertIs(kept_naive, naive_rows)

    def test_missing_scan_time_week_end_not_seven_days_dropped(self):
        discoveries = [{"ticker": "CCC", "score_total": 55.0}]
        kept, status = self.filter_new_discovery(
            {"week_end": "2026-10-01", "discoveries": discoveries},
            "2026-10-23",
        )
        self.assertEqual(kept, [])
        self.assertEqual(status, "stale_dropped")
        self.assertEqual(discoveries[0]["score_total"], 55.0)

    def test_missing_scan_time_same_week_end_kept(self):
        discoveries = [{"ticker": "FFF", "score_total": 66.0}]
        kept, status = self.filter_new_discovery(
            {"week_end": "2026-10-23", "discoveries": discoveries},
            "2026-10-23",
        )
        self.assertEqual(status, "ok")
        self.assertIs(kept, discoveries)

    def test_missing_scan_time_exact_seven_days_kept(self):
        discoveries = [{"ticker": "DDD", "score_total": 80.0}]
        kept, status = self.filter_new_discovery(
            {"week_end": "2026-10-16", "discoveries": discoveries},
            "2026-10-23",
        )
        self.assertEqual(status, "ok")
        self.assertIs(kept, discoveries)
        self.assertEqual(kept[0]["score_total"], 80.0)

    def test_unusable_scan_dropped(self):
        kept, status = self.filter_new_discovery(None, "2026-10-23")
        self.assertEqual(kept, [])
        self.assertEqual(status, "stale_dropped")
        kept, status = self.filter_new_discovery(
            {"scan_time": "not-a-timestamp", "discoveries": [{"ticker": "EEE"}]},
            "2026-10-23",
        )
        self.assertEqual(kept, [])
        self.assertEqual(status, "stale_dropped")


class WeeklyAdditionsEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.render_additions_block = staticmethod(_render_additions_block())

    def test_missing_entry_is_attempted_miss_without_fake_tp(self):
        row = _addition_row("ZZZ", None, 61.0)
        text, _stat = self.render_additions_block(_additions_ds(row))
        self.assertIn("attempted + miss", text)
        self.assertIn("ZZZ", text)
        self.assertIn("61.0", text)
        self.assertNotIn("TP", text)
        self.assertNotIn("Entry", text)
        self.assertNotIn("999.99", text)
        self.assertNotIn("12.50", text)

        empty = _addition_row("ZZZ", {}, 61.0)
        empty_text, _stat = self.render_additions_block(_additions_ds(empty))
        self.assertIn("attempted + miss", empty_text)
        self.assertNotIn("TP", empty_text)

        blank = _addition_row("ZZZ", "", 61.0)
        blank_text, _stat = self.render_additions_block(_additions_ds(blank))
        self.assertIn("attempted + miss", blank_text)

    def test_entry_present_keeps_printed_plan_fields(self):
        entry = {
            "entry": 10.0,
            "sl": 9.0,
            "tp": 12.5,
            "rr": 2.0,
            "atr14": 1.25,
        }
        row = _addition_row("ZZZ", entry, 72.5)
        text, _stat = self.render_additions_block(_additions_ds(row))
        self.assertIn("ZZZ", text)
        self.assertIn("ZZZ Co", text)
        self.assertIn("Tech", text)
        self.assertIn("72.5", text)
        self.assertIn("🟢 BUY", text)
        self.assertIn("22", text)
        self.assertIn("58", text)
        self.assertIn("1.4x", text)
        self.assertNotIn("attempted + miss", text)


if __name__ == "__main__":
    unittest.main()
