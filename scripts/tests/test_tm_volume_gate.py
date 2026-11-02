#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from tm_volume_gate import apply_volume_gate, volume_confirmed  # noqa: E402


def _buy_row(**kw):
    base = {
        "ticker": "AAA",
        "tm_score": 70,
        "effective_bracket": "BUY",
        "volume_ratio": 0.8,
        "score_breakdown": {"volume": 8},
    }
    base.update(kw)
    return base


class TmVolumeGateTests(unittest.TestCase):
    def test_volume_ratio_confirms(self):
        self.assertTrue(volume_confirmed({"volume_ratio": 1.2}))

    def test_volume_leg_confirms(self):
        self.assertTrue(
            volume_confirmed(
                {"volume_ratio": 0.9, "score_breakdown": {"volume": 14}}
            )
        )

    def test_volume_not_confirmed(self):
        self.assertFalse(volume_confirmed(_buy_row()))

    def test_buy_demoted_when_volume_fails(self):
        bracket, reason = apply_volume_gate(_buy_row())
        self.assertEqual(bracket, "WATCH")
        self.assertIn("volume_gate", reason or "")

    def test_buy_kept_when_confirmed(self):
        bracket, reason = apply_volume_gate(_buy_row(volume_ratio=1.5))
        self.assertEqual(bracket, "BUY")
        self.assertIsNone(reason)

    def test_watch_unchanged(self):
        row = _buy_row(tm_score=55, effective_bracket="WATCH")
        bracket, reason = apply_volume_gate(row)
        self.assertEqual(bracket, "WATCH")
        self.assertIsNone(reason)

    def test_tm_score_not_required_for_gate(self):
        row = {"effective_bracket": "BUY", "volume_ratio": 2.0}
        bracket, _ = apply_volume_gate(row)
        self.assertEqual(bracket, "BUY")


if __name__ == "__main__":
    unittest.main()
