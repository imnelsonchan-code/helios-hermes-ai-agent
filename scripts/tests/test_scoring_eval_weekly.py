#!/usr/bin/env python3
"""Regression tests for scripts/host/scoring_eval_weekly.py.

Focus: F1 — the JSONL merge layer must never rewrite a settled row whose hit
is already locked (a duplicate-key update used to erase the locked result),
and F2 — settle_all's default as_of must be fail-closed (today UTC).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
if str(HOST_DIR) not in sys.path:
    sys.path.insert(0, str(HOST_DIR))

WEEKLY_PATH = HOST_DIR / "scoring_eval_weekly.py"


def _load_weekly():
    spec = importlib.util.spec_from_file_location("scoring_eval_weekly", WEEKLY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class RewriteJsonlLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_weekly()

    def test_locked_settled_row_not_rewritten_by_duplicate_key_update(self):
        locked = {
            "sleeve": "tm", "ticker": "AAA", "as_of": "2026-09-01",
            "status": "settled", "hit": True, "mark_price": 11.0,
            "return_pct": 10.0, "settle_reason": "long: mark>entry",
        }
        dup_pending = {
            "sleeve": "tm", "ticker": "AAA", "as_of": "2026-09-01",
            "status": "pending", "entry_price": 10.0,
        }
        update = {
            "status": "settled", "hit": False, "mark_price": 9.5,
            "return_pct": -5.0, "settle_reason": "long: mark<=entry",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "predictions-tm.jsonl"
            path.write_text(
                json.dumps(locked) + "\n" + json.dumps(dup_pending) + "\n",
                encoding="utf-8",
            )
            self.mod._rewrite_jsonl(path, {("tm", "AAA", "2026-09-01"): update})
            rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["status"], "settled")
        self.assertTrue(rows[0]["hit"])
        self.assertAlmostEqual(rows[0]["mark_price"], 11.0)  # lock intact
        # The duplicate-key row itself still gets its settlement applied.
        self.assertEqual(rows[1]["status"], "settled")
        self.assertFalse(rows[1]["hit"])

    def test_plain_pending_row_update_still_applies(self):
        row = {
            "sleeve": "value", "ticker": "ZZZ", "as_of": "2026-09-01",
            "status": "pending", "entry_price": 10.0,
        }
        update = {"status": "settled", "hit": True, "mark_price": 12.0}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "predictions-value.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.mod._rewrite_jsonl(path, {("value", "ZZZ", "2026-09-01"): update})
            out = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(out["status"], "settled")
        self.assertTrue(out["hit"])
        self.assertAlmostEqual(out["mark_price"], 12.0)


class SettleAllDefaultAsOfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_weekly()

    def test_default_as_of_defers_future_horizon(self):
        """as_of=None must be fail-closed (today UTC), not ungated."""
        preds = [self.mod.parse_prediction({
            "sleeve": "tm", "ticker": "AAA", "direction": "long",
            "as_of": "2026-09-01", "horizon_end": "9999-01-01",
            "entry_price": 100.0,
        })]
        report = self.mod.settle_all(preds, {"AAA": 110.0})
        self.assertEqual(report.predictions[0].status, "pending")
        self.assertIn("before horizon_end", report.predictions[0].settle_reason)


if __name__ == "__main__":
    unittest.main()
