#!/usr/bin/env python3
"""Unit tests for Desk Pack daily completion gate (no live host write)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"


def _load(name: str):
    path = HOST / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


DATE = "2026-10-06"


class DeskPackDailyCompletionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("desk_pack_daily_completion_gate")

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.inbox = self.root / "workspace" / "reports" / "inbox"
        self.hermes = self.root / ".hermes"
        self.inbox.mkdir(parents=True)
        self.hermes.mkdir(parents=True)

        self._env_backup = {
            k: os.environ.get(k) for k in ("GATE_HOME", "REPORTS_INBOX", "HERMES_HOME")
        }
        os.environ["GATE_HOME"] = str(self.root)
        os.environ["REPORTS_INBOX"] = str(self.inbox)
        os.environ["HERMES_HOME"] = str(self.hermes)

    def tearDown(self):
        for key, val in self._env_backup.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        self._tmpdir.cleanup()

    def _write(self, rel: str, body: str = "ok\n") -> Path:
        path = self.inbox / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def _full_fixtures(self) -> None:
        self._write(f"market-close/{DATE}-summary-revised.md")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"desk-pack-exit/{DATE}-tm-exits.md")

    def test_missing_market_close_exit_2(self):
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"desk-pack-exit/{DATE}-tm-exits.md")

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["status"], "incomplete")
        self.assertEqual(payload["market_close"], "miss")
        self.assertEqual(payload["daily_social"], "ok")
        self.assertEqual(payload["exit_evidence"], "ok")

    def test_full_fixtures_exit_0(self):
        self._full_fixtures()

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["market_close"], "ok")
        self.assertEqual(payload["daily_social"], "ok")
        self.assertEqual(payload["exit_evidence"], "ok")

    def test_empty_market_close_counts_as_miss(self):
        self._write(f"market-close/{DATE}-summary-revised.md", "")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"desk-pack-exit/{DATE}-tm-exits.md")

        with redirect_stdout(StringIO()):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)

    def test_position_watch_alone_not_exit_evidence(self):
        self._write(f"market-close/{DATE}-summary-revised.md")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"position-watch/{DATE}-position-watch.md")

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["exit_evidence"], "miss")
        self.assertEqual(payload["status"], "incomplete")

    def test_failed_overlay_receipt_is_not_success_evidence(self):
        """`status: checker_rc=3` = the overlay crashed; pack must be incomplete."""
        self._write(f"market-close/{DATE}-summary-revised.md")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(
            f"desk-pack-exit/{DATE}-tm-exits.md",
            "TM BUY digest body\n\nstatus: checker_rc=3\n",
        )
        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["exit_evidence"], "failed-overlay")
        self.assertEqual(payload["status"], "incomplete")

    def test_healthy_receipt_statuses_still_ok(self):
        body = "TM BUY digest body\n\nstatus: no-OPEN-skip\n"
        self._write(f"market-close/{DATE}-summary-revised.md")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"desk-pack-exit/{DATE}-tm-exits.md", body)
        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["exit_evidence"], "ok")

    def test_exit_receipt_fallback_same_dir(self):
        self._write(f"market-close/{DATE}-summary-revised.md")
        self._write(f"daily-social/{DATE}-summary-revised.md")
        self._write(f"desk-pack-exit/{DATE}-run-tm-exits.md")

        with redirect_stdout(StringIO()):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
