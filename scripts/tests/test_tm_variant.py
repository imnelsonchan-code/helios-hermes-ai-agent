#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from tm_variant import (  # noqa: E402
    OPTION_G_SPY_ADX_THRESHOLD,
    apply_shadow_gates,
    apply_variant_to_pack,
    shadow_equal_weights_score,
    stamp_variant,
)


def _row(**kw):
    base = {
        "ticker": "AAA",
        "tm_score": 65,
        "dmi_shift": 0,
        "score_breakdown": {
            "macd": 18,
            "rsi": 16,
            "ma": 14,
            "adx": 12,
            "volume": 10,
        },
    }
    base.update(kw)
    return base


class TmVariantTests(unittest.TestCase):
    def test_stamp_control_adds_contract(self):
        out = stamp_variant({"meta": {}}, "control")
        self.assertEqual(out["meta"]["variant_key"], "control")
        self.assertEqual(out["meta"]["scoring_contract"], "option6_v4.4")

    def test_stamp_non_control_no_contract(self):
        out = stamp_variant({}, "dmi_off")
        self.assertEqual(out["meta"]["variant_key"], "dmi_off")
        self.assertNotIn("scoring_contract", out["meta"])

    def test_control_buy_at_60(self):
        self.assertEqual(apply_shadow_gates(_row(tm_score=60), "control"), "BUY")

    def test_control_option_g_demotes_buy(self):
        self.assertEqual(
            apply_shadow_gates(_row(tm_score=65), "control", spy_adx=20),
            "WATCH",
        )

    def test_option_g_boundary_just_below_threshold_demotes(self):
        self.assertEqual(OPTION_G_SPY_ADX_THRESHOLD, 25)
        self.assertEqual(
            apply_shadow_gates(
                _row(tm_score=65), "control", spy_adx=24.999
            ),
            "WATCH",
        )

    def test_option_g_boundary_at_threshold_keeps_buy(self):
        self.assertEqual(
            apply_shadow_gates(
                _row(tm_score=65), "control", spy_adx=25.0
            ),
            "BUY",
        )

    def test_option_g_custom_threshold(self):
        """25.0 demotes when threshold raised to 25.1."""
        self.assertEqual(
            apply_shadow_gates(
                _row(tm_score=65),
                "control",
                spy_adx=25.0,
                adx_threshold=25.1,
            ),
            "WATCH",
        )
        self.assertEqual(
            apply_shadow_gates(
                _row(tm_score=65),
                "control",
                spy_adx=25.0,
                adx_threshold=OPTION_G_SPY_ADX_THRESHOLD,
            ),
            "BUY",
        )

    def test_missing_spy_adx_skips_demote(self):
        self.assertEqual(
            apply_shadow_gates(_row(tm_score=65), "control", spy_adx=None),
            "BUY",
        )

    def test_weekly_ignores_option_g(self):
        self.assertEqual(
            apply_shadow_gates(
                _row(tm_score=65), "control", spy_adx=20, timeframe="weekly"
            ),
            "BUY",
        )

    def test_no_option_g_ignores_spy_adx(self):
        self.assertEqual(
            apply_shadow_gates(_row(tm_score=65), "no_option_g", spy_adx=20),
            "BUY",
        )

    def test_dmi_bullish_promotes(self):
        self.assertEqual(
            apply_shadow_gates(_row(tm_score=55, dmi_shift=1), "control"),
            "BUY",
        )

    def test_dmi_off_ignores_shift(self):
        self.assertEqual(
            apply_shadow_gates(_row(tm_score=55, dmi_shift=1), "dmi_off"),
            "WATCH",
        )

    def test_equal_weights_shadow_score(self):
        row = _row()
        shadow = shadow_equal_weights_score(row)
        self.assertEqual(shadow, 70.0)
        self.assertEqual(row["tm_score"], 65)

    def test_equal_weights_bracket_from_shadow(self):
        row = _row(
            tm_score=80,
            score_breakdown={
                "macd": 10,
                "rsi": 10,
                "ma": 10,
                "adx": 10,
                "volume": 10,
            },
        )
        self.assertEqual(apply_shadow_gates(row, "equal_weights"), "WATCH")

    def test_tm_score_untouched_by_equal_weights(self):
        row = _row(tm_score=65)
        apply_shadow_gates(row, "equal_weights")
        self.assertEqual(row["tm_score"], 65)
        self.assertEqual(row["shadow_tm_score"], 70.0)

    def test_apply_variant_to_pack(self):
        pack = {"rankings": [_row()]}
        out = apply_variant_to_pack(pack, "control", spy_adx=30)
        self.assertEqual(out["meta"]["variant_key"], "control")
        self.assertEqual(out["rankings"][0]["effective_bracket"], "BUY")

    def test_apply_variant_walks_results_key(self):
        """Live daily packs use results[], not rankings[]."""
        pack = {
            "results": [
                _row(ticker="AAA", tm_score=65, dmi_shift=0),
                _row(ticker="BBB", tm_score=40, dmi_shift=0),
            ]
        }
        out = apply_variant_to_pack(pack, "control", spy_adx=20, timeframe="daily")
        rows = {r["ticker"]: r for r in out["results"]}
        self.assertEqual(rows["AAA"]["effective_bracket"], "WATCH")  # Option G
        self.assertEqual(rows["BBB"]["effective_bracket"], "NO_SIGNAL")
        self.assertEqual(rows["AAA"]["tm_score"], 65)


if __name__ == "__main__":
    unittest.main()
