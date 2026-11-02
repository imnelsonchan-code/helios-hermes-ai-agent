#!/usr/bin/env python3
"""Suppressed BUY list includes every non-BUY at score >= 60 (no network)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "scripts" / "host" / "renee" / "daily_trend_momentum.py"

SEP22 = [
    ("MU", 92.2),
    ("DE", 87.6),
    ("GILD", 82.8),
    ("BIIB", 78.0),
    ("INTC", 76.6),
    ("PANW", 75.4),
    ("MRK", 71.8),
    ("MDT", 60.8),
    ("CAT", 60.2),
    ("C", 60.0),
    ("LOW", 59.9),
]


def _load_builder():
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "build_suppressed_buy_section":
            ns: dict = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(GEN), "exec"), ns)
            return ns["build_suppressed_buy_section"]
    raise AssertionError("build_suppressed_buy_section not found")


build_suppressed_buy_section = _load_builder()


def _rows(verdict: str, *, key: str = "total"):
    out = []
    for ticker, score in SEP22:
        row = {
            "ticker": ticker,
            "verdict": verdict,
            "bracket": ">=90" if score >= 90 else "60-69",
            "base_5indicator_total": score,
        }
        row[key] = score
        if key != "verdict":
            pass
        out.append(row)
    return out


class SuppressedBuySectionTests(unittest.TestCase):
    def test_choppy_lists_all_scores_at_least_60_and_states_no_trade(self):
        md = build_suppressed_buy_section(
            _rows("NO SIGNAL (choppy market)"),
            "choppy",
            12.5,
        )
        self.assertIn("SPY ADX 12.5", md)
        self.assertIn("ADX < 25", md)
        self.assertIn("no trades today", md)
        for ticker, score in SEP22:
            if score >= 60:
                self.assertIn(f"| {ticker} |", md)
            else:
                self.assertNotIn(f"| {ticker} |", md)
        self.assertIn("≥60", md)
        self.assertNotIn("≥90 candidates", md)

    def test_saved_pack_keys_daily_score_and_daily_verdict(self):
        rows = []
        for ticker, score in SEP22:
            rows.append({
                "ticker": ticker,
                "daily_score": score,
                "daily_verdict": "NO SIGNAL (choppy market)",
                "daily_bracket": ">=90" if score >= 90 else "70-79",
            })
        md = build_suppressed_buy_section(rows, "choppy", 12.5)
        self.assertIn("| MU |", md)
        self.assertIn("| C |", md)
        self.assertNotIn("| LOW |", md)

    def test_effective_buy_is_omitted(self):
        rows = [
            {"ticker": "MU", "total": 92.2, "verdict": "BUY"},
            {"ticker": "DE", "total": 87.6, "verdict": "WATCH (bearish trend)"},
        ]
        md = build_suppressed_buy_section(rows, "trending", 29.6)
        self.assertNotIn("| MU |", md)
        self.assertIn("| DE |", md)
        self.assertNotIn("no trades today", md)
        self.assertIn("DMI gating", md)

    def test_prints_entry_sl_tp(self):
        rows = [{
            "ticker": "GILD",
            "total": 82.8,
            "verdict": "NO SIGNAL (choppy market)",
            "bracket": "80-89",
            "entry_price": 154.47,
            "stop_loss": 151.77,
            "take_profit": 159.87,
        }, {
            "ticker": "MDT",
            "total": 60.8,
            "verdict": "NO SIGNAL (choppy market)",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
        }]
        md = build_suppressed_buy_section(rows, "choppy", 12.5)
        self.assertIn("| GILD |", md)
        self.assertIn("$154.47", md)
        self.assertIn("$151.77", md)
        self.assertIn("$159.87", md)
        self.assertIn("| MDT |", md)
        self.assertIn("| — | — | — |", md)
        self.assertNotIn("non-WL", md)

    def test_levels_follow_atr_ladder_including_choppy(self):
        fn = _load_compute_entry_sl_tp()
        gild = fn(152.67, 3.60, regime="choppy")
        self.assertEqual(gild["entry_price"], 154.47)
        self.assertEqual(gild["stop_loss"], 151.77)
        self.assertEqual(gild["take_profit"], 159.87)
        mdt = fn(90.77, 2.07, regime="choppy")
        self.assertEqual(mdt["entry_price"], round(90.77 + 0.5 * 2.07, 2))
        self.assertEqual(mdt["stop_loss"], round(90.77 - 0.25 * 2.07, 2))
        self.assertEqual(mdt["take_profit"], round(90.77 + 2.0 * 2.07, 2))
        mu = fn(1096.16, 50.50, regime="choppy")
        self.assertEqual(mu["entry_price"], round(1096.16 + 0.5 * 50.50, 2))
        self.assertEqual(mu["stop_loss"], round(1096.16 - 0.25 * 50.50, 2))
        trending = fn(152.67, 3.60, regime="trending")
        self.assertEqual(trending["entry_price"], gild["entry_price"])
        self.assertGreater(trending["take_profit"], gild["take_profit"])

    def test_generator_computes_levels_for_every_scored_name(self):
        src = GEN.read_text(encoding="utf-8")
        self.assertIn("Entry / SL / TP for every scored name", src)
        self.assertNotIn("non-WL no level", src)


def _load_compute_entry_sl_tp():
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if names and names[0] in {"ATR_ENTRY_OFFSET", "ATR_SL_OFFSET", "ATR_TP_OFFSET"}:
                nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "compute_entry_sl_tp":
            nodes.append(node)
    ns: dict = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(GEN), "exec"), ns)
    return ns["compute_entry_sl_tp"]


if __name__ == "__main__":
    unittest.main()
