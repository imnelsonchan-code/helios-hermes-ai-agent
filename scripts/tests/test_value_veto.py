#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from value_veto import evaluate_pack, evaluate_vetoes  # noqa: E402


def _clean_row(**kw):
    base = {
        "ticker": "AAA",
        "current_ratio": 2.0,
        "cumulative_fcf_5y": 100,
        "interest_coverage": 5.0,
        "share_count_dilution_5y": 0.05,
        "roe_10y_avg": 0.15,
        "f_score": 7,
        "valuation_score": 72,
    }
    base.update(kw)
    return base


class ValueVetoTests(unittest.TestCase):
    def test_clean_row_allowed(self):
        out = evaluate_vetoes(_clean_row())
        self.assertTrue(out["allowed_candidate"])
        self.assertEqual(out["vetoes"], [])

    def test_current_ratio_veto(self):
        out = evaluate_vetoes(_clean_row(current_ratio=1.2))
        self.assertFalse(out["allowed_candidate"])
        self.assertTrue(any("current_ratio" in v for v in out["vetoes"]))

    def test_f_score_veto(self):
        out = evaluate_vetoes(_clean_row(f_score=3))
        self.assertFalse(out["allowed_candidate"])

    def test_financial_skips_interest_coverage(self):
        out = evaluate_vetoes(
            _clean_row(sector="Banks", interest_coverage=0.5)
        )
        self.assertTrue(out["allowed_candidate"])

    def test_mna_skips_dilution(self):
        out = evaluate_vetoes(
            _clean_row(mna_flag=True, share_count_dilution_5y=0.35)
        )
        self.assertTrue(out["allowed_candidate"])

    def test_accounting_alert_veto(self):
        out = evaluate_vetoes(_clean_row(accounting_alert=True))
        self.assertFalse(out["allowed_candidate"])

    def test_does_not_mutate_valuation_score(self):
        row = _clean_row(valuation_score=72)
        evaluate_vetoes(row)
        self.assertEqual(row["valuation_score"], 72)

    def test_evaluate_pack(self):
        pack = {"tracks": {"A": {"rankings": [_clean_row(), _clean_row(f_score=2)]}}}
        out = evaluate_pack(pack)
        self.assertEqual(len(out["rows"]), 2)
        self.assertTrue(out["rows"][0]["allowed_candidate"])
        self.assertFalse(out["rows"][1]["allowed_candidate"])


if __name__ == "__main__":
    unittest.main()
