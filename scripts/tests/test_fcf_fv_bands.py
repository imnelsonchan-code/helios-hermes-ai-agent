#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from fcf_fv_bands import (  # noqa: E402
    FV_ENGINE,
    candidate_ok,
    compute_fv_range,
    stamp_fcf_bands,
    upside_vs,
)


class FcfFvBandsTests(unittest.TestCase):
    def test_compute_fv_range(self):
        fv = compute_fv_range(fcf=1000, shares=100)
        self.assertEqual(fv["conservative"], 100.0)
        self.assertEqual(fv["reasonable"], 150.0)
        self.assertEqual(fv["optimistic"], 200.0)

    def test_market_cap_derives_shares(self):
        fv = compute_fv_range(fcf=500, market_cap=1000, spot=50)
        self.assertEqual(fv["reasonable"], 375.0)

    def test_upside_vs(self):
        self.assertAlmostEqual(upside_vs(115, 100), 0.15)

    def test_candidate_ok_floor(self):
        fv = {"reasonable": 116.0, "conservative": 110.0, "optimistic": 120.0}
        self.assertTrue(candidate_ok(fv, 100.0, band="reasonable"))
        self.assertFalse(candidate_ok(fv, 110.0, band="reasonable"))

    def test_stamp_does_not_touch_valuation_score(self):
        row = {"ticker": "AAA", "valuation_score": 68, "fcf": 1000, "shares": 100, "spot": 80}
        out = stamp_fcf_bands(row)
        self.assertEqual(out["fv_engine"], FV_ENGINE)
        self.assertEqual(row["valuation_score"], 68)
        self.assertEqual(out.get("valuation_score"), 68)
        self.assertTrue(out["fcf_band_upside"]["candidate_ok"])

    def test_negative_fcf_raises(self):
        with self.assertRaises(ValueError):
            compute_fv_range(fcf=-1, shares=100)


if __name__ == "__main__":
    unittest.main()
