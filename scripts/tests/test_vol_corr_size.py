#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from vol_corr_size import position_cap_pct  # noqa: E402


class VolCorrSizeTests(unittest.TestCase):
    def test_low_vol_boost(self):
        cap = position_cap_pct(0.10, 0.50)
        self.assertAlmostEqual(cap, 0.25)

    def test_mid_vol_linear(self):
        cap = position_cap_pct(0.225, 0.50)
        self.assertAlmostEqual(cap, 0.1625, places=3)

    def test_high_vol_floor(self):
        cap = position_cap_pct(0.60, 0.90)
        self.assertGreaterEqual(cap, 0.05)
        self.assertLessEqual(cap, 0.20)

    def test_low_corr_boost(self):
        cap_low = position_cap_pct(0.20, 0.10)
        cap_high = position_cap_pct(0.20, 0.85)
        self.assertGreater(cap_low, cap_high)

    def test_baseline_20pct(self):
        cap = position_cap_pct(0.15, 0.50)
        self.assertAlmostEqual(cap, 0.20)


if __name__ == "__main__":
    unittest.main()
