#!/usr/bin/env python3
"""Unit tests for pack_meta_stamp.py and prediction_emit.py."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"


def _load(name: str):
    path = HOST / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class PackMetaStampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("pack_meta_stamp")

    def test_stamp_tm_promotes_volume_and_aliases(self):
        pack = {
            "date": "2026-09-14",
            "spy_adx": 11.4,
            "results": [
                {
                    "ticker": "AAA",
                    "daily_score": 72,
                    "daily_bracket": "BUY",
                    "price": 10.0,
                    "raw_indicators": {"volume_ratio": 1.5, "plus_di": 30, "minus_di": 20},
                    "score_breakdown": {"volume": 13},
                }
            ],
        }
        out = self.mod.stamp_tm_pack(pack)
        row = out["results"][0]
        self.assertEqual(row["tm_score"], 72)
        self.assertEqual(row["bracket"], "BUY")
        self.assertEqual(row["theoretical_bracket"], "BUY")
        self.assertEqual(row["volume_ratio"], 1.5)
        self.assertEqual(row["dmi_plus"], 30)
        self.assertEqual(out["meta"]["spy_adx"], 11.4)
        self.assertTrue(out["meta"]["pack_meta_stamped"])

    def test_stamp_theoretical_ignores_live_watch_demotion(self):
        """WATCH + score≥60 must still be theoretical BUY (score ladder)."""
        pack = {
            "date": "2026-09-14",
            "results": [
                {
                    "ticker": "BBB",
                    "daily_score": 70,
                    "daily_bracket": "WATCH",
                    "price": 10.0,
                }
            ],
        }
        row = self.mod.stamp_tm_pack(pack)["results"][0]
        self.assertEqual(row["bracket"], "WATCH")  # live narrative
        self.assertEqual(row["theoretical_bracket"], "BUY")

    def test_stamp_theoretical_ignores_live_buy_promotion(self):
        """BUY + score<60 must not be theoretical BUY."""
        pack = {
            "date": "2026-09-14",
            "results": [
                {
                    "ticker": "CCC",
                    "daily_score": 40,
                    "daily_bracket": "BUY",
                    "price": 10.0,
                }
            ],
        }
        row = self.mod.stamp_tm_pack(pack)["results"][0]
        self.assertEqual(row["bracket"], "BUY")  # live narrative
        self.assertEqual(row["theoretical_bracket"], "NO_SIGNAL")

    def test_stamp_score_band_maps_to_theoretical_buy(self):
        pack = {
            "date": "2026-09-14",
            "results": [
                {
                    "ticker": "DDD",
                    "daily_score": 65,
                    "daily_bracket": "60-69",
                    "price": 10.0,
                }
            ],
        }
        row = self.mod.stamp_tm_pack(pack)["results"][0]
        self.assertEqual(row["theoretical_bracket"], "BUY")
        self.assertEqual(row["bracket"], "BUY")

    def test_stamp_clips_score_over_100_preserves_raw(self):
        pack = {
            "date": "2026-09-14",
            "results": [
                {
                    "ticker": "EEE",
                    "daily_score": 118.2,
                    "daily_bracket": "BUY",
                    "price": 10.0,
                }
            ],
        }
        row = self.mod.stamp_tm_pack(pack)["results"][0]
        self.assertEqual(row["tm_score"], 100.0)
        self.assertEqual(row["daily_score"], 100.0)
        self.assertEqual(row["weighted_total_raw"], 118.2)
        self.assertEqual(row["theoretical_bracket"], "BUY")

    def test_stamp_value_statement_as_of(self):
        pack = {"week": "2026-W37", "tracks": {"A": {"rankings": [{"ticker": "ASB", "width_verdict": "🟢", "price": 1}]}}}
        out = self.mod.stamp_value_pack(pack)
        self.assertEqual(out["meta"]["value"]["statement_as_of"], "2026-W37")
        self.assertEqual(out["tracks"]["A"]["rankings"][0]["status"], "Candidate")


class PredictionEmitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("prediction_emit")

    def test_emit_tm_buys_only(self):
        pack = {
            "date": "2026-09-14",
            "meta": {"as_of": "2026-09-14"},
            "results": [
                {"ticker": "AAA", "daily_bracket": "BUY", "daily_score": 70, "price": 10},
                {"ticker": "BBB", "daily_bracket": "WATCH", "daily_score": 70, "price": 10},
                {"ticker": "CCC", "daily_bracket": "BUY", "daily_score": 40, "price": 10},
            ],
        }
        rows = self.mod.emit_tm_predictions(pack)
        self.assertEqual([r["ticker"] for r in rows], ["AAA"])
        self.assertEqual(rows[0]["sleeve"], "tm")
        self.assertEqual(rows[0]["horizon_end"], "2026-09-21")

    def test_emit_value_candidates_only(self):
        pack = {
            "week": "2026-W37",
            "tracks": {
                "A": {
                    "rankings": [
                        {"ticker": "GOOD", "width_verdict": "🟢", "price": 5, "valuation_score": 60},
                        {"ticker": "BAD", "width_verdict": "🟡", "price": 5, "valuation_score": 60},
                    ]
                }
            },
        }
        rows = self.mod.emit_value_predictions(pack)
        self.assertEqual([r["ticker"] for r in rows], ["GOOD"])
        self.assertEqual(rows[0]["sleeve"], "value")


if __name__ == "__main__":
    unittest.main()
