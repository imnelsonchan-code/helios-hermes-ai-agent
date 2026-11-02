#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from excursion_ledger import compute_excursion  # noqa: E402
from market_data import DailyBar  # noqa: E402


def _bar(session, close, high=None, low=None):
    close_d = Decimal(str(close))
    return DailyBar(
        session=session,
        open=close_d,
        high=Decimal(str(high if high is not None else close)),
        low=Decimal(str(low if low is not None else close)),
        close=close_d,
        volume=1000,
    )


class ExcursionLedgerTests(unittest.TestCase):
    def test_mae_mfe_high_vs_close_divergence(self):
        entry = date(2026, 9, 1)
        bars = (
            _bar(entry, 100, high=101, low=99),
            _bar(entry + timedelta(days=1), 102, high=110, low=101),
            _bar(entry + timedelta(days=2), 105, high=106, low=95),
        )
        mae, mfe_h, mfe_c, capture, realised, held, issues = compute_excursion(
            fill_price=Decimal("100"),
            risk_per_share=Decimal("10"),
            bars=bars,
            entry_session=entry,
            exit_session=entry + timedelta(days=2),
            exit_price=Decimal("105"),
        )
        self.assertEqual(mae, Decimal("0.5"))  # (100-95)/10
        self.assertEqual(mfe_h, Decimal("1.0"))  # (110-100)/10
        self.assertEqual(mfe_c, Decimal("0.5"))  # (105-100)/10
        self.assertEqual(realised, Decimal("0.5"))
        self.assertEqual(capture, Decimal("0.5"))
        self.assertEqual(held, 3)
        self.assertEqual(issues, ())


if __name__ == "__main__":
    unittest.main()
