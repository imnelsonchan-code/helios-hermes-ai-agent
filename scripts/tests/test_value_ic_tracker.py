#!/usr/bin/env python3
"""Unit tests for scripts/host/value_ic_tracker.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
TRACKER_PATH = HOST_DIR / "value_ic_tracker.py"


def _load(name: str = "value_ic_tracker"):
    spec = importlib.util.spec_from_file_location(name, TRACKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ValueIcTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_spearman_ic_perfect_positive(self):
        scores = {"A": 10.0, "B": 20.0, "C": 30.0, "D": 40.0}
        returns = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
        ic = self.mod.spearman_ic(scores, returns)
        self.assertIsNotNone(ic)
        self.assertAlmostEqual(ic, 1.0, places=6)

    def test_spearman_ic_too_few_pairs(self):
        self.assertIsNone(self.mod.spearman_ic({"A": 1.0}, {"A": 1.0}))
        self.assertIsNone(self.mod.spearman_ic({"A": 1.0, "B": 2.0}, {"A": 1.0}))

    def test_row_valuation_score_from_composite(self):
        row = {"ticker": "MSFT", "valuation_composite": 0.723}
        self.assertEqual(self.mod.row_valuation_score(row), 72)

    def test_quality_adjusted_separate_series(self):
        rows = [
            {"ticker": "A", "valuation_score": 80, "quality_adjusted_score": 75},
            {"ticker": "B", "valuation_score": 60, "quality_adjusted_score": 55},
            {"ticker": "C", "valuation_score": 40, "quality_adjusted_score": 35},
            {"ticker": "D", "valuation_score": 20, "quality_adjusted_score": 15},
        ]
        returns = {"4w": {"A": 0.1, "B": 0.05, "C": -0.02, "D": -0.08}}
        series, warnings = self.mod.compute_ic_series(rows, returns)
        fields = {e["score_field"] for e in series}
        self.assertIn("valuation_score", fields)
        self.assertIn("quality_adjusted_score", fields)
        self.assertEqual(len(series), 2)

    def test_look_ahead_warning_when_ic_high(self):
        rows = [
            {"ticker": f"T{i}", "valuation_score": i * 10}
            for i in range(1, 6)
        ]
        returns = {"4w": {f"T{i}": i * 0.2 for i in range(1, 6)}}
        series, warnings = self.mod.compute_ic_series(rows, returns)
        self.assertTrue(any("LOOKAHEAD_SUSPECT" in w for w in warnings))
        self.assertTrue(all(e["sleeve"] == "value" for e in series))

    def test_cli_dual_horizon(self):
        width = {
            "tracks": {
                "A": {
                    "rankings": [
                        {"ticker": "AAPL", "valuation_score": 70},
                        {"ticker": "MSFT", "valuation_score": 55},
                        {"ticker": "NVDA", "valuation_score": 40},
                    ]
                }
            }
        }
        returns = {
            "4w": {"AAPL": 0.03, "MSFT": 0.01, "NVDA": -0.02},
            "12w": {"AAPL": 0.08, "MSFT": 0.04, "NVDA": -0.01},
        }
        with tempfile.TemporaryDirectory() as td:
            width_path = Path(td) / "width.json"
            ret_path = Path(td) / "returns.json"
            out_path = Path(td) / "out.json"
            width_path.write_text(json.dumps(width), encoding="utf-8")
            ret_path.write_text(json.dumps(returns), encoding="utf-8")
            rc = self.mod.main(
                ["--width-json", str(width_path), "--returns-json", str(ret_path), "--out", str(out_path)]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            horizons = {e["horizon"] for e in payload["series"]}
            self.assertEqual(horizons, {"12w", "4w"})


if __name__ == "__main__":
    unittest.main()
