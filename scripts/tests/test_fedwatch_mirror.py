#!/usr/bin/env python3
"""Path-regression: host FedWatch mirror keeps alice/fedwatch BASE."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIRROR = ROOT / "scripts" / "host" / "fedwatch_daily_fetch.py"


class TestFedwatchMirror(unittest.TestCase):
    def test_mirror_exists(self) -> None:
        self.assertTrue(MIRROR.is_file(), msg=f"missing {MIRROR}")

    def test_base_alice_fedwatch(self) -> None:
        text = MIRROR.read_text(encoding="utf-8")
        self.assertIn("alice/fedwatch", text)
        self.assertIn('os.environ.get("HERMES_HOME")', text)
        self.assertIn("shared/reports/alice/fedwatch", text)
        self.assertRegex(text, r"BASE\s*=")
        self.assertIn("REPO MIRROR", text)
        # No secrets in mirror
        lower = text.lower()
        for needle in ("api_key", "secret", "bearer ", "password"):
            self.assertNotIn(needle, lower)


if __name__ == "__main__":
    unittest.main()
