#!/usr/bin/env python3
"""Four-path gate: bold header replace, pending-rechallenge, inbox revised."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"
DATE = "2026-10-26"


def _load():
    path = HOST / "four_path_auto_derive_gate.py"
    spec = importlib.util.spec_from_file_location("four_path_auto_derive_gate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


HAND_BLOCK = """# close

## Header

- **Four-path status:**
  - commodities-session (emily): `old.md` → **miss** (revised artifact missing)
  - rates-session (christina): `old.md` → **miss** (revised artifact missing)
  - weekly-trend-momentum (renee): `old.md` → **miss** (revised artifact missing)
  - valuation-width (eliza): `old.md` → **miss** (revised artifact missing)

- As-of: 2026-10-26

## Body

keep me
"""


class FourPathGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.shared = self.root / "shared"
        self.inbox = self.root / "inbox"
        self.shared.mkdir()
        self.inbox.mkdir()
        self._env = {
            k: os.environ.get(k) for k in ("REPORTS_INBOX", "HERMES_SHARED", "HERMES_HOME")
        }
        os.environ["REPORTS_INBOX"] = str(self.inbox)
        os.environ["HERMES_SHARED"] = str(self.shared)
        os.environ["HERMES_HOME"] = str(self.root / "hermes")

    def tearDown(self):
        for key, val in self._env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        self._tmp.cleanup()

    def _write_revised(self, rel: Path, name: str) -> None:
        rel.mkdir(parents=True, exist_ok=True)
        (rel / name).write_text("revised body\n", encoding="utf-8")

    def _plant_all_revised(self) -> None:
        pairs = [
            (self.shared / "emily" / "commodities-session", f"{DATE}-commodity-session-revised.md"),
            (self.shared / "christina" / "rates-session", f"{DATE}-rates-session-revised.md"),
            (self.shared / "renee" / "daily-trend-momentum", f"{DATE}-daily-trend-momentum-revised.md"),
            (self.shared / "eliza" / "value-session", f"{DATE}-value-session-revised.md"),
        ]
        for folder, name in pairs:
            self._write_revised(folder, name)

    def test_bold_header_parses(self):
        parsed = self.mod._parse_report_four_path(HAND_BLOCK)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["rates-session"]["status"], "miss")
        self.assertEqual(parsed["commodities-session"]["status"], "miss")
        plain = HAND_BLOCK.replace("- **Four-path status:**", "- Four-path status:")
        parsed_plain = self.mod._parse_report_four_path(plain)
        self.assertEqual(parsed_plain["valuation-width"]["status"], "miss")

    def test_patch_replaces_once_then_check_passes(self):
        self._plant_all_revised()
        report = self.root / "summary.md"
        report.write_text(HAND_BLOCK, encoding="utf-8")
        code = self.mod.main(["--report", str(report), "--date", DATE, "--patch"])
        self.assertEqual(code, 0)
        text = report.read_text(encoding="utf-8")
        self.assertEqual(text.count("Four-path status:"), 1)
        self.assertNotIn("**Four-path status:**", text)
        self.assertNotIn("revised artifact missing", text)
        self.assertIn("pending-rechallenge", text)
        self.assertIn("keep me", text)
        self.assertIn("- As-of: 2026-10-26", text)
        again = self.mod.main(["--report", str(report), "--date", DATE])
        self.assertEqual(again, 0)
        self.assertEqual(report.read_text(encoding="utf-8").count("Four-path status:"), 1)

    def test_missing_header_patch_does_not_create_file(self):
        ghost = self.root / "no-such-report.md"
        code = self.mod.main(["--report", str(ghost), "--date", DATE, "--patch"])
        self.assertEqual(code, 1)
        self.assertFalse(ghost.exists())
        bare = self.root / "bare.md"
        bare.write_text("# title\n\nno header here\n", encoding="utf-8")
        before = bare.read_text(encoding="utf-8")
        code = self.mod.main(["--report", str(bare), "--date", DATE, "--patch"])
        self.assertEqual(code, 1)
        self.assertEqual(bare.read_text(encoding="utf-8"), before)

    def test_revised_without_challenge_name_is_pending(self):
        folder = self.shared / "emily" / "commodities-session"
        self._write_revised(folder, f"{DATE}-commodity-session-revised.md")
        (folder / f"{DATE}-notes.md").write_text("not a challenge file\n", encoding="utf-8")
        result = self.mod.derive_four_path(DATE)
        leg = result["legs"]["commodities-session"]
        self.assertEqual(leg["status"], "pending-rechallenge")
        self.assertNotEqual(leg["status"], "miss")
        bullets = self.mod.format_four_path_bullets(result)
        for line in bullets.splitlines():
            if "commodities-session" in line and line.strip().startswith("- commodities"):
                self.assertNotIn("revised artifact missing", line)

    def test_inbox_rates_revised_is_not_miss(self):
        self._write_revised(
            self.inbox / "rates-session",
            f"{DATE}-rates-session-revised.md",
        )
        result = self.mod.derive_four_path(DATE)
        leg = result["legs"]["rates-session"]
        self.assertEqual(leg["status"], "pending-rechallenge")
        self.assertNotEqual(leg["status"], "miss")
        self.assertTrue(str(leg["repr_path"]).endswith(f"{DATE}-rates-session-revised.md"))
        bullets = self.mod.format_four_path_bullets(result)
        for line in bullets.splitlines():
            if line.strip().startswith("- rates-session"):
                self.assertNotIn("revised artifact missing", line)
                self.assertIn("pending-rechallenge", line)


if __name__ == "__main__":
    unittest.main()
