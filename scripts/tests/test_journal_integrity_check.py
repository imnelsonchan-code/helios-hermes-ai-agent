#!/usr/bin/env python3
"""Unit tests for scripts/host/journal_integrity_check.py (synthetic journal)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
JIC_PATH = HOST_DIR / "journal_integrity_check.py"

HEADER = (
    "Date,Ticker,Action,Shares,Price,Total USD,GBP Amount,Status,Notes\n"
)


def _load():
    spec = importlib.util.spec_from_file_location("journal_integrity_check", JIC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class JournalIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _run(self, body: str) -> int:
        with tempfile.TemporaryDirectory() as td:
            jp = Path(td) / "journal.csv"
            jp.write_text(HEADER + body, encoding="utf-8")
            orig = self.mod.JOURNAL
            self.mod.JOURNAL = str(jp)
            try:
                return self.mod.main()
            finally:
                self.mod.JOURNAL = orig

    def _run_capture(self, body: str):
        """Run and return (rc, stdout text) using stdout redirection."""
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            jp = Path(td) / "journal.csv"
            jp.write_text(HEADER + body, encoding="utf-8")
            orig = self.mod.JOURNAL
            self.mod.JOURNAL = str(jp)
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    rc = self.mod.main()
            finally:
                self.mod.JOURNAL = orig
        return rc, buf.getvalue()

    def test_open_partial_position_is_healthy(self):
        rows = (
            "2026-01-01,ACME,BUY,100,10.0,,,OPEN,PARTIAL_EXIT_ACK\n"
            "2026-01-05,ACME,SELL,25,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 0, out)
        self.assertIn("acknowledged", out)

    def test_void_buy_does_not_spuriously_mismatch(self):
        """An OPEN 100 with full close + VOID 50 BUY must ORPHAN, not MISMATCH.

        Regression (P1 #10): VOID shares used to inflate total BUY, producing
        a spurious POSITION MISMATCH while masking the ORPHAN signature.
        """
        rows = (
            "2026-01-01,ACME,BUY,100,10.0,,,OPEN,\n"
            "2026-01-02,ACME,BUY,50,10.0,,,VOID,\n"
            "2026-01-03,ACME,SELL,100,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 1)
        self.assertIn("ORPHAN OPEN BUY", out)
        self.assertNotIn("POSITION MISMATCH", out)

    def test_ack_on_specific_open_buy_row_suppresses_that_residual(self):
        rows = (
            "2026-02-01,BETA,BUY,20,5.0,,,OPEN,\n"
            "2026-02-02,BETA,BUY,20,5.0,,,OPEN,PARTIAL_EXIT_ACK verified\n"
            "2026-02-03,BETA,SELL,25,6.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 0)
        self.assertIn("acknowledged", out)

    def test_ack_in_other_row_notes_does_not_hide_mismatch(self):
        """ACK quoted in a SELL's Notes must not silence check #3 (per-row)."""
        rows = (
            "2026-02-01,BETA,BUY,20,5.0,,,OPEN,\n"
            "2026-02-02,BETA,BUY,20,5.0,,,OPEN,\n"
            "2026-02-03,BETA,SELL,25,6.0,,,CLOSED, owner wrote PARTIAL_EXIT_ACK\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 1)
        self.assertIn("POSITION MISMATCH", out)

    def test_phantom_sell_flagged(self):
        rows = (
            "2026-01-01,ACME,BUY,100,10.0,,,OPEN,\n"
            "2026-01-05,ACME,SELL,,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 1)
        self.assertIn("PHANTOM SELL", out)

    def test_thousands_separator_shares_parse_and_unparsed_flagged(self):
        rows = (
            "2026-01-01,ACME,BUY,\"1,000\",10.0,,,OPEN,PARTIAL_EXIT_ACK\n"
            "2026-01-05,ACME,SELL,400,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 0, out)  # 1,000 − 400 leaves an acked open position

        bad = (
            "2026-01-01,ACME,BUY,many,10.0,,,OPEN,\n"
        )
        rc, out = self._run_capture(bad)
        self.assertEqual(rc, 1)
        self.assertIn("UNPARSED SHARES", out)

    def test_skipped_rows_excluded_from_every_total(self):
        rows = (
            "2026-01-01,ACME,BUY,100,10.0,,,OPEN,\n"
            "2026-01-05,ACME,SELL,100,12.0,,,PENDING,\n"
            "2026-01-06,ACME,SELL,50,12.0,,,CANCEL,\n"
        )
        rc = self._run(rows)
        self.assertEqual(rc, 0)  # no CLOSED sells → no orphan/mismatch checks

    def test_fully_closed_ticker_is_not_an_orphan(self):
        """BUY rows whose Status flipped to CLOSED + matching sells = a normal trade.

        Regression: pre-rewrite HEAD iterated OPEN-lot tickers only; the
        rewrite flagged every fully-realized ticker as ORPHAN OPEN BUY.
        """
        rows = (
            "2026-01-02,GAMA,BUY,100,10.0,,,CLOSED,\n"
            "2026-01-20,GAMA,SELL,100,10.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("ORPHAN", out)

    def test_sells_never_consume_closed_buy_lots(self):
        """FIFO must attribute sells to OPEN lots only (position_watch rule).

        Regression: closed-lot-first file order used to absorb sells into a
        CLOSED BUY lot, inflating the reported residual (90 instead of 40).
        """
        rows = (
            "2026-01-01,YEN,BUY,50,10.0,,,CLOSED,\n"
            "2026-01-02,YEN,BUY,100,10.0,,,OPEN,\n"
            "2026-01-05,YEN,SELL,60,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 1)
        self.assertIn("40 un-acked open shares", out)

    def test_untouched_open_lot_is_not_a_partial_exit_residual(self):
        """A sell that fully consumed an acked lot leaves the other lot alone.

        BUY 100 (ack) + BUY 50 (plain), SELL 60 → sells consume the open lots;
        the acked lot's 40-share remainder is owner-verified, the untouched
        50-share lot is just an open position. No mismatch.
        """
        rows = (
            "2026-01-01,ACME,BUY,100,10.0,,,OPEN,PARTIAL_EXIT_ACK\n"
            "2026-01-02,ACME,BUY,50,10.0,,,OPEN,\n"
            "2026-01-05,ACME,SELL,60,12.0,,,CLOSED,\n"
        )
        rc, out = self._run_capture(rows)
        self.assertEqual(rc, 0, out)
        self.assertIn("acknowledged", out)
        self.assertNotIn("POSITION MISMATCH", out)
