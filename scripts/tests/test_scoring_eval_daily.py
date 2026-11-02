#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from scoring_eval_daily import (  # noqa: E402
    TM_DIRS,
    assert_funnel_monotonic,
    build_summary,
    compute_funnel_counts,
)
from tm_variant import (  # noqa: E402
    OPTION_G_SPY_ADX_THRESHOLD,
    apply_shadow_gates,
)


def _theo_buy_row(**kw):
    base = {
        "ticker": "AAA",
        "bracket": "BUY",
        "tm_score": 65,
        "volume_ratio": 1.5,
        "score_breakdown": {"volume": 14},
    }
    base.update(kw)
    return base


def _with_option_g(row: dict, spy_adx: float | None) -> dict:
    """Annotate effective_bracket the way apply_variant_to_pack does."""
    out = dict(row)
    out["effective_bracket"] = apply_shadow_gates(
        out, "control", spy_adx=spy_adx, timeframe="daily"
    )
    return out


class ScoringEvalDailyPackPathTests(unittest.TestCase):
    def test_tm_dirs_prefer_desk_pack_workspace(self):
        """Desk pack prompts write workspace/daily-trend-momentum first."""
        home = Path.home() / ".hermes"
        self.assertEqual(
            TM_DIRS[0],
            home / "profiles" / "renee" / "workspace" / "daily-trend-momentum",
        )
        self.assertEqual(
            TM_DIRS[1],
            home / "shared" / "reports" / "renee" / "daily-trend-momentum",
        )
        self.assertEqual(
            TM_DIRS[2],
            home
            / "profiles"
            / "renee"
            / "workspace"
            / "reports"
            / "daily-trend-momentum",
        )

    def test_find_pack_prefers_earlier_tm_dir(self):
        import scoring_eval_daily as sed
        import tempfile

        session = date(2026, 9, 14)
        name = f"{session.isoformat()}-data.json"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preferred = root / "preferred"
            fallback = root / "fallback"
            preferred.mkdir()
            fallback.mkdir()
            (preferred / name).write_text('{"ok":1}\n', encoding="utf-8")
            (fallback / name).write_text('{"ok":2}\n', encoding="utf-8")
            old = sed.TM_DIRS
            try:
                sed.TM_DIRS = [preferred, fallback]
                found = sed._find_pack(session)
                self.assertEqual(found, preferred / name)
            finally:
                sed.TM_DIRS = old


class ScoringEvalDailyFunnelTests(unittest.TestCase):
    def test_option_g_demotion_skips_volume_gate(self):
        """Old bug: theo BUY + volume pass still incremented after_vol.

        With low spy_adx, Option G demotes BUY->WATCH; after_vol must be 0
        even when volume would confirm.
        """
        row = _with_option_g(_theo_buy_row(volume_ratio=2.0), spy_adx=20.0)
        self.assertEqual(row["effective_bracket"], "WATCH")

        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 1)
        self.assertEqual(funnel["buys_after_option_g"], 0)
        self.assertEqual(funnel["buys_after_volume_gate"], 0)
        self.assertEqual(funnel["volume_demotions"], [])
        self.assertNotIn("volume_gated_bracket", row)
        assert_funnel_monotonic(funnel)

    def test_high_adx_volume_pass_monotonic(self):
        row = _with_option_g(_theo_buy_row(volume_ratio=1.5), spy_adx=30.0)
        self.assertEqual(row["effective_bracket"], "BUY")

        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 1)
        self.assertEqual(funnel["buys_after_option_g"], 1)
        self.assertEqual(funnel["buys_after_volume_gate"], 1)
        self.assertEqual(funnel["volume_demotions"], [])
        self.assertEqual(row["volume_gated_bracket"], "BUY")
        assert_funnel_monotonic(funnel)

    def test_high_adx_volume_fail_demotes(self):
        row = _with_option_g(
            _theo_buy_row(volume_ratio=0.5, score_breakdown={"volume": 5}),
            spy_adx=30.0,
        )
        self.assertEqual(row["effective_bracket"], "BUY")

        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 1)
        self.assertEqual(funnel["buys_after_option_g"], 1)
        self.assertEqual(funnel["buys_after_volume_gate"], 0)
        self.assertEqual(len(funnel["volume_demotions"]), 1)
        self.assertEqual(row["volume_gated_bracket"], "WATCH")
        assert_funnel_monotonic(funnel)

    def test_funnel_monotonic_mixed_pack(self):
        rows = [
            _with_option_g(_theo_buy_row(ticker="LOW", volume_ratio=2.0), spy_adx=20.0),
            _with_option_g(_theo_buy_row(ticker="PASS", volume_ratio=1.5), spy_adx=30.0),
            _with_option_g(
                _theo_buy_row(
                    ticker="FAIL",
                    volume_ratio=0.4,
                    score_breakdown={"volume": 4},
                ),
                spy_adx=30.0,
            ),
            {"ticker": "WATCH", "bracket": "WATCH", "effective_bracket": "WATCH"},
        ]
        # Per-row Option G uses each row's own spy context via effective_bracket
        # already stamped; mixed spy_adx above simulates stamped pack rows.
        funnel = compute_funnel_counts(rows)
        theo = funnel["buys_theoretical"]
        after_g = funnel["buys_after_option_g"]
        after_vol = funnel["buys_after_volume_gate"]
        self.assertEqual(theo, 3)
        self.assertEqual(after_g, 2)  # PASS + FAIL (LOW demoted by Option G)
        self.assertEqual(after_vol, 1)  # PASS only
        self.assertLessEqual(after_vol, after_g)
        self.assertLessEqual(after_g, theo)
        assert_funnel_monotonic(funnel)

    def test_assert_funnel_monotonic_rejects_after_vol_gt_after_g(self):
        """Old parallel logic could yield after_vol > after_g; helper catches it."""
        bad = {
            "buys_theoretical": 2,
            "buys_after_option_g": 0,
            "buys_after_volume_gate": 1,
            "volume_demotions": [],
        }
        with self.assertRaises(ValueError) as ctx:
            assert_funnel_monotonic(bad)
        self.assertIn("non-monotonic", str(ctx.exception))

    def test_assert_funnel_monotonic_rejects_demotions_when_after_g_zero(self):
        """after_G=0 must not carry volume_demotions (even if after_vol=0)."""
        bad = {
            "buys_theoretical": 6,
            "buys_after_option_g": 0,
            "buys_after_volume_gate": 0,
            "volume_demotions": [
                {"ticker": "DE", "reason": "volume_gate"},
                {"ticker": "GILD", "reason": "volume_gate"},
                {"ticker": "BIIB", "reason": "volume_gate"},
            ],
        }
        with self.assertRaises(ValueError) as ctx:
            assert_funnel_monotonic(bad)
        self.assertIn("volume_demotions", str(ctx.exception))

    def test_assert_funnel_monotonic_rejects_09_14_smoke_shape(self):
        """Host smoke backfill had theo=6 after_G=0 after_vol=3 — must refuse."""
        bad = {
            "buys_theoretical": 6,
            "buys_after_option_g": 0,
            "buys_after_volume_gate": 3,
            "volume_demotions": [
                {"ticker": "DE", "reason": "volume_gate"},
                {"ticker": "GILD", "reason": "volume_gate"},
                {"ticker": "BIIB", "reason": "volume_gate"},
            ],
        }
        with self.assertRaises(ValueError) as ctx:
            assert_funnel_monotonic(bad)
        msg = str(ctx.exception)
        self.assertTrue(
            "non-monotonic" in msg or "volume_demotions" in msg,
            msg,
        )

    def test_shared_option_g_threshold_constant(self):
        self.assertEqual(OPTION_G_SPY_ADX_THRESHOLD, 25)
        # Gates and summary comparison must use the same constant
        just_below = apply_shadow_gates(
            _theo_buy_row(), "control", spy_adx=OPTION_G_SPY_ADX_THRESHOLD - 0.001
        )
        at = apply_shadow_gates(
            _theo_buy_row(), "control", spy_adx=float(OPTION_G_SPY_ADX_THRESHOLD)
        )
        self.assertEqual(just_below, "WATCH")
        self.assertEqual(at, "BUY")

    def test_build_summary_missing_spy_adx(self):
        funnel = {
            "buys_theoretical": 1,
            "buys_after_option_g": 1,
            "buys_after_volume_gate": 1,
            "volume_demotions": [],
        }
        summary = build_summary(
            session=date(2026, 9, 14),
            pack_path="/tmp/pack.json",
            spy_f=None,
            theo_buys=["AAA"],
            funnel=funnel,
            preds_count=0,
        )
        self.assertIsNone(summary["option_g_active"])
        self.assertEqual(summary["option_g_skipped"], "missing_spy_adx")
        self.assertIsNone(summary["spy_adx"])
        self.assertIn("missing spy_adx", summary["note"])

    def test_build_summary_option_g_active_uses_shared_threshold(self):
        funnel = {
            "buys_theoretical": 0,
            "buys_after_option_g": 0,
            "buys_after_volume_gate": 0,
            "volume_demotions": [],
        }
        low = build_summary(
            session=date(2026, 9, 14),
            pack_path="/tmp/pack.json",
            spy_f=OPTION_G_SPY_ADX_THRESHOLD - 1,
            theo_buys=[],
            funnel=funnel,
            preds_count=0,
        )
        high = build_summary(
            session=date(2026, 9, 14),
            pack_path="/tmp/pack.json",
            spy_f=float(OPTION_G_SPY_ADX_THRESHOLD),
            theo_buys=[],
            funnel=funnel,
            preds_count=0,
        )
        self.assertTrue(low["option_g_active"])
        self.assertFalse(high["option_g_active"])
        self.assertNotIn("option_g_skipped", low)
        self.assertNotIn("option_g_skipped", high)

    def test_dmi_promo_excluded_from_funnel(self):
        """DMI can lift WATCH->effective BUY; must not break theo ≥ after_G."""
        row = {
            "ticker": "DMI",
            "bracket": "WATCH",
            "tm_score": 55,
            "dmi_shift": 1,
            "volume_ratio": 2.0,
            "score_breakdown": {"volume": 14},
        }
        row = _with_option_g(row, spy_adx=30.0)
        self.assertEqual(row["effective_bracket"], "BUY")

        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 0)
        self.assertEqual(funnel["buys_after_option_g"], 0)
        self.assertEqual(funnel["buys_after_volume_gate"], 0)
        self.assertEqual(funnel["volume_demotions"], [])
        self.assertNotIn("volume_gated_bracket", row)

    def test_watch_score60_counts_as_theoretical(self):
        """Live WATCH demotion must not drop score≥60 from Theoretical BUY."""
        from pack_meta_stamp import stamp_tm_pack

        stamped = stamp_tm_pack(
            {
                "date": "2026-09-14",
                "spy_adx": 30.0,
                "results": [
                    {
                        "ticker": "BBB",
                        "daily_score": 70,
                        "daily_bracket": "WATCH",
                        "volume_ratio": 1.5,
                        "score_breakdown": {"volume": 14},
                    }
                ],
            }
        )
        row = stamped["results"][0]
        self.assertEqual(row["theoretical_bracket"], "BUY")
        self.assertEqual(row["bracket"], "WATCH")
        row = _with_option_g(row, spy_adx=30.0)
        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 1)
        self.assertEqual(funnel["buys_after_option_g"], 1)
        self.assertEqual(funnel["buys_after_volume_gate"], 1)

    def test_buy_score40_excluded_from_theoretical(self):
        """Live BUY promotion must not inflate Theoretical BUY without score≥60."""
        from pack_meta_stamp import stamp_tm_pack

        stamped = stamp_tm_pack(
            {
                "date": "2026-09-14",
                "spy_adx": 30.0,
                "results": [
                    {
                        "ticker": "CCC",
                        "daily_score": 40,
                        "daily_bracket": "BUY",
                        "volume_ratio": 2.0,
                        "score_breakdown": {"volume": 14},
                    }
                ],
            }
        )
        row = stamped["results"][0]
        self.assertEqual(row["theoretical_bracket"], "NO_SIGNAL")
        self.assertEqual(row["bracket"], "BUY")
        row = _with_option_g(row, spy_adx=30.0)
        funnel = compute_funnel_counts([row])
        self.assertEqual(funnel["buys_theoretical"], 0)
        self.assertEqual(funnel["buys_after_option_g"], 0)
        self.assertEqual(funnel["buys_after_volume_gate"], 0)


if __name__ == "__main__":
    unittest.main()
