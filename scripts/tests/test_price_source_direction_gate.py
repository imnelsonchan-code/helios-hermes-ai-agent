#!/usr/bin/env python3
"""Unit tests for the price-source direction gate (no live host write)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"
MOD_PATH = HOST / "validate_price_source_direction_gate.py"

PASS_MD = """# commodity session

| Gold | GLD prev close +0.40% | up |
| Silver | SLV prev close +0.20% | up |
| Oil | BZ=F ICE Brent financial futures +0.10% | flat |

CL versus BZ spread is same-source.
"""

PRECIOUS_FAIL_MD = """# commodity session

| Gold | spot +1.20% bullish | x |
| Silver | spot -0.40% bearish | y |
"""

BRENT_FAIL_MD = """# commodity session

UK oil basis BZ=F +0.80% on the session.
"""

SPREAD_FAIL_MD = """# commodity session

The CL-BZ crack widened overnight.
"""


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_price_source_direction_gate", MOD_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class PriceSourceDirectionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _run(self, texts: list[tuple[str, str]]) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            root = Path(tmp)
            for name, body in texts:
                path = root / name
                path.write_text(body, encoding="utf-8")
                paths.append(str(path))
            buf = StringIO()
            with redirect_stdout(buf):
                code = self.mod.main(paths)
            return code, buf.getvalue()

    def test_pass_fixture_exits_0(self):
        code, out = self._run([("pass.md", PASS_MD)])
        self.assertEqual(code, 0)
        self.assertNotIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", out)
        self.assertNotIn("OIL_BZ_F_DISTORTION_DISCLOSURE_MISSING", out)
        self.assertNotIn("OIL_SPREAD_SAME_SOURCE", out)
        self.assertIn("ALL CHECKS PASSED", out)

    def test_precious_fail_exits_1(self):
        code, out = self._run([("precious.md", PRECIOUS_FAIL_MD)])
        self.assertEqual(code, 1)
        self.assertIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", out)
        self.assertNotIn("OIL_BZ_F_DISTORTION_DISCLOSURE_MISSING", out)
        self.assertNotIn("OIL_SPREAD_SAME_SOURCE", out)

    def test_brent_fail_exits_1(self):
        code, out = self._run([("brent.md", BRENT_FAIL_MD)])
        self.assertEqual(code, 1)
        self.assertIn("OIL_BZ_F_DISTORTION_DISCLOSURE_MISSING", out)
        self.assertNotIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", out)
        self.assertNotIn("OIL_SPREAD_SAME_SOURCE", out)

    def test_spread_fail_exits_1(self):
        code, out = self._run([("spread.md", SPREAD_FAIL_MD)])
        self.assertEqual(code, 1)
        self.assertIn("OIL_SPREAD_SAME_SOURCE", out)
        self.assertNotIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", out)
        self.assertNotIn("OIL_BZ_F_DISTORTION_DISCLOSURE_MISSING", out)

    def test_no_files_exits_2(self):
        buf = StringIO()
        err = StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = self.mod.main([])
        self.assertEqual(code, 2)

    def test_lean_row_and_bz_miss_are_not_violations(self):
        text = (
            "| Gold | lean: base |\n"
            "| Silver | lean: base |\n"
            "| Oil | BZ=F miss |\n"
            "| CL vs BZ | miss |\n"
        )
        self.assertEqual(self.mod.check_text(text, "lean.md"), [])

    def test_gold_api_previous_close_still_fails(self):
        text = "| Gold | gold-api previous close +1.2% | up |\n"
        codes = [item.code for item in self.mod.check_text(text, "spot.md")]
        self.assertIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", codes)

    def test_check_text_importable(self):
        found = self.mod.check_text(PRECIOUS_FAIL_MD, "mem.md")
        codes = [item.code for item in found]
        self.assertIn("PRECIOUS_1D_MISSING_CANONICAL_SRC", codes)
        self.assertEqual(self.mod.check_text(PASS_MD, "mem.md"), [])


if __name__ == "__main__":
    unittest.main()
