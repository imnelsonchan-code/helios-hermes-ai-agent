#!/usr/bin/env python3
"""Unit tests for scripts/host/portfolio_tracker.py (not copied to the live host)."""

from __future__ import annotations

import csv
import importlib.util
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
if str(HOST_DIR) not in sys.path:
    sys.path.insert(0, str(HOST_DIR))

TRACKER_PATH = HOST_DIR / "portfolio_tracker.py"
GBP_USD_RATE = 1.31
TOL = 0.02
SYN2_POISON_GBP = 10000.0

# Shares × Price (VOID 50 ignored): 68 × 60.08, 25×63.4 + 10×65.05 + 33×65.69
TST1_BUY_GBP = 68 * 60.08  # 4085.44
TST1_SELL_GBP = 25 * 63.4 + 10 * 65.05 + 33 * 65.69  # 4403.27
TST1_PNL_GBP = TST1_SELL_GBP - TST1_BUY_GBP  # 317.83
TST1_PNL_USD = TST1_PNL_GBP * GBP_USD_RATE  # 416.3573


def _row(
    ticker: str,
    action: str,
    status: str,
    shares,
    price,
    total_usd="",
    gbp_amount="",
) -> dict:
    return {
        "Date": "2026-08-01",
        "Ticker": ticker,
        "Action": action,
        "Shares": str(shares),
        "Price": str(price),
        "Total USD": "" if total_usd == "" else str(total_usd),
        "GBP Amount": "" if gbp_amount == "" else str(gbp_amount),
        "SL": "",
        "TP1": "",
        "TP2": "",
        "Status": status,
        "Notes": "",
    }


# In-memory rows; same columns as live ~/.hermes/trade_journal.csv.
# SYN2 SELL GBP Amount is a poison ~10k cell (unreliable; must not enter GBP totals).
FIXTURE_ROWS = [
    _row("SYN1", "BUY", "CLOSED", 90, 24.69, total_usd=2222.1),
    _row("SYN1", "SELL", "CLOSED", 90, 24.27, total_usd=2184.3),
    _row("SYN2", "BUY", "CLOSED", 120, 223.51, total_usd=26821.2),
    _row("SYN2", "SELL", "CLOSED", 60, 223.86, total_usd=13431.60, gbp_amount=SYN2_POISON_GBP),
    _row("SYN2", "SELL", "CLOSED", 60, 223.50, total_usd=13410.00, gbp_amount=SYN2_POISON_GBP),
    _row("TST1.L", "BUY", "OPEN", 100, 60.08, total_usd=0, gbp_amount=6008.00),
    _row("TST1.L", "SELL", "VOID", 50, 63.11, total_usd="", gbp_amount=3155.5),
    _row("TST1.L", "SELL", "CLOSED", 25, 63.4, total_usd="", gbp_amount=1585.0),
    _row("TST1.L", "SELL", "CLOSED", 10, 65.05, total_usd="", gbp_amount=""),
    _row("TST1.L", "SELL", "CLOSED", 33, 65.69, total_usd="", gbp_amount=2167.77),
]


def _load_tracker(name: str = "portfolio_tracker"):
    if not TRACKER_PATH.is_file():
        raise FileNotFoundError(
            f"missing {TRACKER_PATH} — sibling host script has not landed yet"
        )
    spec = importlib.util.spec_from_file_location(name, TRACKER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {TRACKER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sgln(pnl: dict) -> dict:
    for key in ("TST1.L", "TST1"):
        if key in pnl:
            return pnl[key]
    raise AssertionError(f"TST1.L missing from pnl keys: {sorted(pnl)}")


def _almost(test: unittest.TestCase, got, expected, msg: str) -> None:
    test.assertAlmostEqual(float(got), float(expected), delta=TOL, msg=msg)


def _call_write_report(mod, pnl, summary) -> str:
    spy = {"error": "unit-test", "spy_return_pct": 0, "spy_start": 0, "spy_end": 0}
    fn = mod.write_report
    sig = inspect.signature(fn)
    params = list(sig.parameters)
    kwargs = {}
    if "spy" in params:
        kwargs["spy"] = spy
    if "bracket_alerts" in params:
        kwargs["bracket_alerts"] = []
    if "alerts" in params and "bracket_alerts" not in params:
        kwargs["alerts"] = []
    try:
        out = fn(pnl, summary, **kwargs)
    except TypeError:
        try:
            out = fn(pnl, summary, spy, [])
        except TypeError:
            out = fn(pnl, summary)
    if isinstance(out, str) and out.strip():
        return out
    report_dir = getattr(mod, "REPORT_DIR", None)
    if report_dir:
        mds = sorted(Path(report_dir).glob("*.md"))
        if mds:
            return mds[-1].read_text()
    raise AssertionError("write_report returned no markdown and wrote no .md file")


class TestPortfolioTracker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_tracker()

    def setUp(self):
        self.pnl = self.mod.compute_pnl(FIXTURE_ROWS, gbp_usd_rate=GBP_USD_RATE)
        self.summary = self.mod.compute_portfolio_summary(self.pnl)

    def test_void_ignored_sgln_remains_open(self):
        sgln = _sgln(self.pnl)
        self.assertEqual(int(sgln["sell_shares"]), 68)
        self.assertEqual(int(sgln["remaining_shares"]), 32)
        self.assertEqual(sgln["status"], "OPEN")

    def test_sgln_uses_shares_times_price_not_gbp_amount(self):
        sgln = _sgln(self.pnl)
        _almost(self, sgln["pnl_gbp"], TST1_PNL_GBP, "pnl_gbp")
        _almost(self, sgln["buy_gbp"], TST1_BUY_GBP, "buy_gbp")
        _almost(self, sgln["sell_gbp"], TST1_SELL_GBP, "sell_gbp")

    def test_sgln_usd_companion_from_gbp_rate(self):
        sgln = _sgln(self.pnl)
        _almost(self, sgln["pnl_usd"], TST1_PNL_USD, "pnl_usd")

    def test_cmcsa_and_ibm_closed_usd(self):
        cmcsa = self.pnl["SYN1"]
        ibm = self.pnl["SYN2"]
        _almost(self, cmcsa["pnl_usd"], -37.80, "SYN1 pnl_usd")
        self.assertEqual(cmcsa["status"], "CLOSED")
        _almost(self, ibm["pnl_usd"], 20.40, "SYN2 pnl_usd")
        self.assertEqual(ibm["status"], "CLOSED")

    def test_summary_closed_open_and_win_rate(self):
        self.assertEqual(self.summary["total_closed_trades"], 2)
        self.assertEqual(self.summary["total_open_trades"], 1)
        self.assertEqual(float(self.summary["win_rate"]), 50.0)
        self.assertEqual(self.summary["win_count"], 1)
        self.assertEqual(self.summary["loss_count"], 1)

    def test_ibm_poison_gbp_amount_not_in_summary(self):
        gbp_fields = {
            k: v
            for k, v in self.summary.items()
            if "gbp" in k.lower() and isinstance(v, (int, float))
        }
        self.assertTrue(gbp_fields, "summary should expose GBP totals")
        for key, val in gbp_fields.items():
            self.assertGreater(
                abs(float(val) - SYN2_POISON_GBP),
                1.0,
                f"{key}={val} looks like SYN2 SELL GBP Amount leaked",
            )
            self.assertGreater(
                abs(float(val) - 2 * SYN2_POISON_GBP),
                1.0,
                f"{key}={val} looks like two SYN2 SELL GBP Amount cells summed",
            )

    def test_write_report_sgln_line_has_usd_and_gbp(self):
        with tempfile.TemporaryDirectory() as td:
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            if hasattr(self.mod, "REPORT_DIR"):
                self.mod.REPORT_DIR = str(report_dir)
            with patch.dict(os.environ, {"HOME": td}):
                md = _call_write_report(self.mod, self.pnl, self.summary)
        sgln_lines = [ln for ln in md.splitlines() if "TST1" in ln]
        self.assertTrue(sgln_lines, "write_report markdown missing an TST1 position line")
        pos = next((ln for ln in sgln_lines if "|" in ln), sgln_lines[0])
        self.assertIn("$", pos)
        self.assertIn("£", pos)

    def test_import_and_compute_pnl_without_creating_hermes_home(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"HOME": td}):
                isolated = _load_tracker("portfolio_tracker_nohome")
                isolated.compute_pnl(FIXTURE_ROWS, gbp_usd_rate=GBP_USD_RATE)
            hermes = Path(td) / ".hermes"
            self.assertFalse(
                hermes.exists(),
                "import / compute_pnl must not mkdir ~/.hermes",
            )

    def _write_journal(self, path: Path, rows=None) -> Path:
        rows = rows if rows is not None else FIXTURE_ROWS
        fieldnames = list(FIXTURE_ROWS[0].keys())
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _run_main(self, argv, **patches):
        spy = {"error": "unit-test", "spy_return_pct": 0, "spy_start": 0, "spy_end": 0}
        patchers = [
            patch.object(self.mod, "fetch_spy_benchmark", return_value=spy),
            patch.object(sys, "argv", argv),
        ]
        for name, kwargs in patches.items():
            if name == "send_telegram_alert":
                continue
            patchers.append(patch.object(self.mod, name, **kwargs))
        telegram = patch.object(
            self.mod,
            "send_telegram_alert",
            **patches.get("send_telegram_alert", {"return_value": True}),
        )
        started = []
        try:
            for p in patchers:
                started.append(p)
                p.start()
            with telegram as tg:
                return self.mod.main(), tg
        finally:
            for p in reversed(started):
                p.stop()

    def _bracket_state_path(self, td: str) -> str:
        return str(Path(td) / "state" / "portfolio_bracket_alert.json")

    def test_main_bracket_alert_exits_zero_and_sends_telegram(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self._write_journal(Path(td) / "journal.csv")
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            state_path = self._bracket_state_path(td)
            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(journal)],
                REPORT_DIR={"new": str(report_dir)},
                BRACKET_ALERT_STATE_PATH={"new": state_path},
                fetch_live_bracket_distribution={"return_value": {">=90": 0.112}},
                reconcile_brackets={
                    "return_value": [
                        "  >=90: live=11.2% vs backtest=22.0% (↓10.8%)",
                    ]
                },
            )
        self.assertEqual(rc, 0)
        tg.assert_called_once()
        sent = tg.call_args[0][0]
        self.assertIn("Backtest bracket divergence", sent)
        self.assertIn("vs stale v2.3 baseline", sent)
        self.assertIn(">=90", sent)
        self.assertRegex(sent, r"11\.2%|22\.0%|10\.8%")

    def test_main_bracket_alert_suppressed_after_n_consecutive_fires(self):
        n = self.mod.BRACKET_ALERT_SUPPRESS_AFTER_N
        self.assertEqual(n, 3)
        with tempfile.TemporaryDirectory() as td:
            journal = self._write_journal(Path(td) / "journal.csv")
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            state_path = self._bracket_state_path(td)
            bracket_line = "  >=90: live=11.2% vs backtest=22.0% (↓10.8%)"
            patches = dict(
                REPORT_DIR={"new": str(report_dir)},
                BRACKET_ALERT_STATE_PATH={"new": state_path},
                fetch_live_bracket_distribution={"return_value": {">=90": 0.112}},
                reconcile_brackets={"return_value": [bracket_line]},
            )
            for i in range(n):
                rc, tg = self._run_main(
                    ["portfolio_tracker.py", "--journal", str(journal)],
                    **patches,
                )
                self.assertEqual(rc, 0, f"fire #{i + 1}")
                tg.assert_called_once()
                sent = tg.call_args[0][0]
                self.assertIn("vs stale v2.3 baseline", sent)
                self.assertIn(">=90", sent)

            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(journal)],
                **patches,
            )
            self.assertEqual(rc, 0)
            tg.assert_not_called()
            streak = self.mod.load_bracket_alert_streak(state_path)
            self.assertEqual(streak, n + 1)

    def test_main_bracket_alert_streak_resets_when_no_divergence(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self._write_journal(Path(td) / "journal.csv")
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            state_path = self._bracket_state_path(td)
            self.mod.save_bracket_alert_streak(2, state_path)
            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(journal)],
                REPORT_DIR={"new": str(report_dir)},
                BRACKET_ALERT_STATE_PATH={"new": state_path},
                fetch_live_bracket_distribution={"return_value": {}},
            )
            self.assertEqual(rc, 0)
            tg.assert_not_called()
            self.assertEqual(self.mod.load_bracket_alert_streak(state_path), 0)

    def test_build_bracket_divergence_alert_includes_label_and_bracket(self):
        msg = self.mod.build_bracket_divergence_alert(
            ["  <50: live=32.7% vs backtest=11.0% (↑21.7%)"]
        )
        self.assertIn("vs stale v2.3 baseline", msg)
        self.assertIn("<50", msg)
        self.assertIn("32.7%", msg)

    def test_main_drawdown_alert_exits_zero_and_sends_telegram(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self._write_journal(Path(td) / "journal.csv")
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            state_path = self._bracket_state_path(td)
            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(journal)],
                REPORT_DIR={"new": str(report_dir)},
                BRACKET_ALERT_STATE_PATH={"new": state_path},
                fetch_live_bracket_distribution={"return_value": {}},
                compute_drawdown={"return_value": -0.09},
            )
        self.assertEqual(rc, 0)
        tg.assert_called_once()
        sent = tg.call_args[0][0]
        self.assertIn("PORTFOLIO DRAWDOWN", sent)

    def test_main_dry_run_skips_telegram_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self._write_journal(Path(td) / "journal.csv")
            report_dir = Path(td) / "reports"
            report_dir.mkdir()
            state_path = self._bracket_state_path(td)
            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(journal), "--dry-run"],
                REPORT_DIR={"new": str(report_dir)},
                BRACKET_ALERT_STATE_PATH={"new": state_path},
                fetch_live_bracket_distribution={"return_value": {">=90": 0.112}},
                reconcile_brackets={
                    "return_value": [
                        "  >=90: live=11.2% vs backtest=22.0% (↓10.8%)",
                    ]
                },
            )
        self.assertEqual(rc, 0)
        tg.assert_not_called()
        self.assertFalse(Path(state_path).exists())

    def test_main_missing_journal_exits_one(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "no-such-journal.csv"
            rc, tg = self._run_main(
                ["portfolio_tracker.py", "--journal", str(missing)],
            )
        self.assertEqual(rc, 1)
        tg.assert_not_called()


if __name__ == "__main__":
    unittest.main()
