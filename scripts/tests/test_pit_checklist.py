#!/usr/bin/env python3
"""Unit tests for scripts/host/pit_checklist.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
CHECKLIST_PATH = HOST_DIR / "pit_checklist.py"


def _load(name: str = "pit_checklist"):
    spec = importlib.util.spec_from_file_location(name, CHECKLIST_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


GOOD_META = {
    "value": {"statement_as_of": "2026-09-01"},
    "alice": {
        "as_of": "2026-09-10",
        "news_social_window": {"start": "2026-08-01", "end": "2026-09-10"},
        "fred_vintage_pinned": True,
        "fred_vintage": "2026-09-01",
    },
    "tm": {
        "bars": [
            {
                "ticker": "AAPL",
                "series": [{"close": 150.0}, {"close": 151.2}],
            }
        ]
    },
    "memory_lessons": [
        {"trade_date": "2026-08-15", "resolved_by_trade_date": True},
    ],
}


class PitChecklistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_all_pass_on_good_meta(self):
        results = self.mod.run_checklist(GOOD_META)
        by_id = {r["id"]: r for r in results}
        self.assertEqual(by_id["statement_as_of_present"]["status"], "pass")
        self.assertEqual(by_id["news_social_window_trimmed"]["status"], "pass")
        self.assertEqual(by_id["latest_bar_not_dropped_on_nan_close"]["status"], "pass")
        self.assertEqual(by_id["memory_lessons_resolved_by_trade_date"]["status"], "pass")
        self.assertEqual(by_id["fred_vintage_pinned"]["status"], "pass")

    def test_fail_missing_statement_as_of(self):
        meta = dict(GOOD_META)
        meta["value"] = {}
        results = self.mod.run_checklist(meta)
        row = next(r for r in results if r["id"] == "statement_as_of_present")
        self.assertEqual(row["status"], "fail")

    def test_fail_news_window_past_as_of(self):
        meta = json.loads(json.dumps(GOOD_META))
        meta["alice"]["news_social_window"]["end"] = "2026-09-15"
        row = next(
            r for r in self.mod.run_checklist(meta) if r["id"] == "news_social_window_trimmed"
        )
        self.assertEqual(row["status"], "fail")

    def test_warn_fred_vintage_missing(self):
        meta = json.loads(json.dumps(GOOD_META))
        meta["alice"]["fred_vintage_pinned"] = False
        row = next(r for r in self.mod.run_checklist(meta) if r["id"] == "fred_vintage_pinned")
        self.assertEqual(row["status"], "warn")

    def test_strict_exit_code(self):
        meta = {"value": {}}
        with tempfile.TemporaryDirectory() as td:
            meta_path = Path(td) / "meta.json"
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            rc_default = self.mod.main(["--meta", str(meta_path)])
            rc_strict = self.mod.main(["--meta", str(meta_path), "--strict"])
        self.assertEqual(rc_default, 0)
        self.assertEqual(rc_strict, 1)


if __name__ == "__main__":
    unittest.main()
