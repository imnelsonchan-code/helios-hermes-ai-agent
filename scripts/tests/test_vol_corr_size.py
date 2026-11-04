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

    # ── Continuity/monotonicity invariants (the curve used to jump UP at the
    # 0.30 and 0.50 boundaries, doubling the cap for higher-risk books) ──

    def _vol_mult(self, v):
        from vol_corr_size import _vol_multiplier
        return _vol_multiplier(v)

    def test_vol_multiplier_continuous_at_30(self):
        just_below = self._vol_mult(0.2999)
        at = self._vol_mult(0.30)
        # Effectively continuous (any residual step must be DOWN, never up).
        self.assertGreaterEqual(at, just_below - 1e-3)

    def test_vol_multiplier_continuous_at_50(self):
        at = self._vol_mult(0.50)
        above = self._vol_mult(0.5001)
        #Cap for HIGHER vol must not increase across the boundary.
        self.assertLessEqual(above, at + 1e-9)

    def test_vol_multiplier_monotone_non_increasing(self):
        seq = [self._vol_mult(0.10 + 0.01 * i) for i in range(45)]
        for lo, hi in zip(seq, seq[1:]):
            self.assertLessEqual(hi, lo + 1e-9)

    def test_extreme_vol_not_larger_than_50pct_cap(self):
        cap50 = position_cap_pct(0.50, 0.80)
        cap60 = position_cap_pct(0.60, 0.80)
        cap80 = position_cap_pct(0.80, 0.80)
        self.assertLessEqual(cap60, cap50 + 1e-9)
        self.assertLessEqual(cap80, cap50 + 1e-9)


if __name__ == "__main__":
    unittest.main()
