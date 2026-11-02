#!/usr/bin/env python3
"""stamp_cross_check fixtures. No network, no live latest.json."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"


def _load():
    path = HOST / "fedwatch_daily_fetch.py"
    spec = importlib.util.spec_from_file_location("fedwatch_daily_fetch_stamp", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sentiment(status: str, oct_hike, with_market: bool) -> dict:
    markets = []
    if with_market:
        markets.append(
            {
                "url": "https://example.test/fed-october",
                "question": "Federal Reserve Decision in October?",
            }
        )
    return {
        "freshness_stamp": {"status": status},
        "summary": {"oct_hike_pct": oct_hike},
        "markets": markets,
    }


class FedwatchCrossCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_degenerate_zq_is_miss(self):
        data = {
            "layers": {
                "a_primary": {
                    "summary": {"oct_hike_pct": 100},
                    "forward_backward_calibration": {"range_pct": [682.0, 1136.7]},
                },
                "b_backup_zq": {"prob_hike_pct": 40, "status": "fresh"},
                "c_sentiment": _sentiment("unknown", 100, with_market=False),
            },
            "freshness": {
                "status": "fresh",
                "layers": {"a_primary": "fresh", "b_backup_zq": "fresh", "c_sentiment": "unknown"},
            },
        }
        out = self.mod.stamp_cross_check(data)
        self.assertIs(out, data)
        self.assertEqual(out["cross_check"]["citation"], "miss")
        self.assertEqual(out["cross_check"]["reason"], "degenerate_zq_sole_source")
        self.assertEqual(out["freshness"]["citation"], "miss")

    def test_fresh_sentiment_and_in_range_primary_is_ok(self):
        data = {
            "layers": {
                "a_primary": {
                    "summary": {"oct_hike_pct": 42.0},
                    "forward_backward_calibration": {"range_pct": [20.0, 55.0]},
                },
                "c_sentiment": _sentiment("fresh", 40.0, with_market=True),
            },
            "freshness": {"layers": {"c_sentiment": "fresh"}},
        }
        out = self.mod.stamp_cross_check(data)
        self.assertEqual(out["cross_check"], {"citation": "ok"})
        self.assertNotIn("citation", out["freshness"])

    def test_usable_primary_with_stale_sentiment_is_primary_only(self):
        data = {
            "layers": {
                "a_primary": {
                    "summary": {"oct_hike_pct": 42.0},
                    "forward_backward_calibration": {"range_pct": [20.0, 55.0]},
                },
                "c_sentiment": _sentiment("unknown", None, with_market=False),
            },
            "freshness": {"layers": {"c_sentiment": "unknown"}},
        }
        out = self.mod.stamp_cross_check(data)
        self.assertEqual(out["cross_check"]["citation"], "primary_only")
        self.assertEqual(out["cross_check"]["reason"], "sentiment_miss")
        self.assertNotIn("citation", out["freshness"])

    def test_backup_zq_cannot_clear_bound_primary(self):
        data = {
            "layers": {
                "a_primary": {
                    "summary": {"oct_hike_pct": 100},
                    "meetings": [{"prob_move_pct": 100}],
                    "forward_backward_calibration": {"range_pct": [10, 40]},
                },
                "b_backup_zq": {
                    "status": "fresh",
                    "prob_hike_pct": 37.5,
                    "calc": {"probability": 37.5, "range_pct": [30, 45]},
                },
                "c_sentiment": _sentiment("fresh", 35.0, with_market=True),
            },
            "freshness": {"status": "fresh", "layers": {"c_sentiment": "fresh"}},
        }
        out = self.mod.stamp_cross_check(data)
        self.assertEqual(out["cross_check"]["citation"], "miss")
        self.assertEqual(out["cross_check"]["reason"], "degenerate_zq_sole_source")
        self.assertEqual(out["freshness"]["citation"], "miss")


if __name__ == "__main__":
    unittest.main()
