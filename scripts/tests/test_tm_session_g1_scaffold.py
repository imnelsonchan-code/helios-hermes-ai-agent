#!/usr/bin/env python3
"""Unit tests for daily T&M G1 session scaffold (no network)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "scripts" / "host" / "renee" / "daily_trend_momentum.py"
SKILL = ROOT / "profiles" / "renee" / "skills" / "tm-session-report" / "SKILL.md"

G1_HEADINGS = (
    "## Session summary",
    "## Market insight",
    "## News/Market check (Renee-topic)",
    "## Lenses",
)


def _load_g1():
    """Exec only ``g1_session_scaffold`` — skip hermes / yfinance imports."""
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "g1_session_scaffold":
            ns = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(GEN), "exec"), ns)
            return ns["g1_session_scaffold"]
    raise AssertionError("g1_session_scaffold not found in daily_trend_momentum.py")


g1_session_scaffold = _load_g1()


class TmSessionG1ScaffoldTests(unittest.TestCase):
    def test_headings_in_order_before_section_1(self):
        md = g1_session_scaffold("2026-09-22", "choppy", 12.5, True)
        positions = [md.find(h) for h in G1_HEADINGS]
        self.assertTrue(all(p >= 0 for p in positions), msg=md)
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Section 1", md)
        src = GEN.read_text(encoding="utf-8")
        call_at = src.find("g1_session_scaffold(")
        section1_at = src.find('## 📊 Section 1 — Daily Overview')
        self.assertGreater(call_at, 0)
        self.assertGreater(section1_at, call_at)

    def test_alice_pull_and_news(self):
        md = g1_session_scaffold("2026-09-22", "trending", 28, False)
        self.assertIn("Alice pull", md)
        self.assertTrue("News: miss" in md or "News" in md)

    def test_skill_fail_closed_phrases(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Revise MUST insert the four headings", text)
        self.assertIn("this report has no ## Market insight", text)
        self.assertIn("Tracker as substitute", text)
        self.assertIn("wrong-day tape", text)
        self.assertIn("do not delete the section", text)
        self.assertIn("$REPORTS_INBOX/", text)
        self.assertIn("❌ `~/.hermes/shared/inbox/`", text)
        self.assertIn("shared/reports/<profile>/inbox/", text)


if __name__ == "__main__":
    unittest.main()
