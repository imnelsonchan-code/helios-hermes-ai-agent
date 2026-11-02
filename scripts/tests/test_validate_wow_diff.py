#!/usr/bin/env python3
"""Unit tests for scripts/host/validate_wow_diff.py (not copied to the live host)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
MOD_PATH = HOST_DIR / "validate_wow_diff.py"


def _load_module(name: str = "validate_wow_diff"):
    if not MOD_PATH.is_file():
        raise FileNotFoundError(f"missing {MOD_PATH}")
    spec = importlib.util.spec_from_file_location(name, MOD_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {MOD_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _report_with_b(
    *,
    rankings: list | None = None,
    screened=None,
    include_b: bool = True,
) -> dict:
    tracks: dict = {"A": {"rankings": [{"ticker": "AAA"}]}}
    if include_b:
        b: dict = {}
        if rankings is not None:
            b["rankings"] = rankings
        if screened is not None:
            b["screened"] = screened
        tracks["B"] = b
    return {"tracks": tracks}


class ValidateWowDiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_stock_count_drop_shows_negative_pct(self):
        alert = self.mod.stock_count_wow_alert(5, 25)
        self.assertIsNotNone(alert)
        self.assertIn("25->5", alert)
        self.assertIn("(-80%)", alert)
        self.assertNotIn("(+80%)", alert)

    def test_stock_count_rise_shows_positive_pct(self):
        alert = self.mod.stock_count_wow_alert(40, 20)
        self.assertIsNotNone(alert)
        self.assertIn("20->40", alert)
        self.assertIn("(+100%)", alert)

    def test_stock_count_threshold_requires_abs_ratio_over_half(self):
        self.assertIsNone(self.mod.stock_count_wow_alert(15, 10))  # +50% exact
        self.assertIsNotNone(self.mod.stock_count_wow_alert(16, 10))  # +60%
        self.assertIsNone(self.mod.stock_count_wow_alert(5, 10))  # -50% exact
        self.assertIsNotNone(self.mod.stock_count_wow_alert(4, 10))  # -60%

    def test_track_b_missing_alert_fires_when_baseline_had_b(self):
        prev = _report_with_b(rankings=[{"ticker": "XYZ"}], screened=True)
        curr = _report_with_b(include_b=False)
        alert = self.mod.track_b_missing_alert(curr, prev)
        self.assertEqual(alert, self.mod.TRACK_B_MISSING_ALERT)

        curr_unscreened = _report_with_b(rankings=[], screened=False)
        self.assertEqual(
            self.mod.track_b_missing_alert(curr_unscreened, prev),
            self.mod.TRACK_B_MISSING_ALERT,
        )

        curr_empty = _report_with_b(rankings=[])
        self.assertEqual(
            self.mod.track_b_missing_alert(curr_empty, prev),
            self.mod.TRACK_B_MISSING_ALERT,
        )

    def test_track_b_missing_alert_silent_when_both_lack_b(self):
        prev = _report_with_b(include_b=False)
        curr = _report_with_b(include_b=False)
        self.assertIsNone(self.mod.track_b_missing_alert(curr, prev))

        prev_empty = _report_with_b(rankings=[], screened=False)
        curr_empty = _report_with_b(rankings=[], screened=False)
        self.assertIsNone(self.mod.track_b_missing_alert(curr_empty, prev_empty))

    def test_track_b_present_in_both_no_alert(self):
        prev = _report_with_b(rankings=[{"ticker": "XYZ"}], screened=True)
        curr = _report_with_b(rankings=[], screened=True)  # screened 0 hits is real
        self.assertIsNone(self.mod.track_b_missing_alert(curr, prev))


if __name__ == "__main__":
    unittest.main()
