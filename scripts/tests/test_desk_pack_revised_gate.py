#!/usr/bin/env python3
"""Unit tests for commodities desk-pack revised gate (no live host write)."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
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


DATE = "2026-09-29"

DRAFT_BODY = """# commodities session

portal `inbox/commodities-session/*-revised.md`

this draft did not use shadow

**Train:** should be dropped

body line
"""


class DeskPackRevisedGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("desk_pack_revised_gate")

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

    def _draft_path(self) -> Path:
        p = self.inbox / "commodities-session" / f"{DATE}-commodity-session.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _challenge_path(self) -> Path:
        p = (
            self.hermes
            / "shared"
            / "reports"
            / "zoe"
            / "commodities-session"
            / f"{DATE}-challenge.md"
        )
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _inbox_revised(self) -> Path:
        return (
            self.inbox
            / "commodities-session"
            / f"{DATE}-commodities-session-revised.md"
        )

    def _emily_shared_revised(self) -> Path:
        return (
            self.hermes
            / "shared"
            / "reports"
            / "emily"
            / "commodities-session"
            / f"{DATE}-commodity-session-revised.md"
        )

    def _emily_workspace_revised(self) -> Path:
        return (
            self.hermes
            / "profiles"
            / "emily"
            / "workspace"
            / "commodities-session"
            / f"{DATE}-commodity-session-revised.md"
        )

    def _write_draft_and_challenge(
        self,
        *,
        draft_age: float = 10.0,
        challenge_age: float = 60.0,
        body: str = DRAFT_BODY,
    ) -> Path:
        now = time.time()
        draft = self._draft_path()
        draft.write_text(body, encoding="utf-8")
        os.utime(draft, (now - draft_age, now - draft_age))

        challenge = self._challenge_path()
        challenge.write_text("zoe challenge\n", encoding="utf-8")
        os.utime(challenge, (now - challenge_age, now - challenge_age))
        return draft

    def test_promote(self):
        draft = self._write_draft_and_challenge(draft_age=10.0, challenge_age=60.0)
        draft_size = draft.stat().st_size

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)

        inbox_rev = self._inbox_revised()
        shared_rev = self._emily_shared_revised()
        ws_rev = self._emily_workspace_revised()
        self.assertTrue(inbox_rev.is_file())
        self.assertTrue(shared_rev.is_file())
        self.assertTrue(ws_rev.is_file())
        self.assertTrue(draft.is_file())
        self.assertEqual(draft.stat().st_size, draft_size)

        text = inbox_rev.read_text(encoding="utf-8")
        self.assertIn(
            f"portal `inbox/commodities-session/{DATE}-commodities-session-revised.md`",
            text,
        )
        self.assertNotIn("*-revised.md", text)
        self.assertNotIn("**Train:**", text)
        self.assertIn("this revised did not use shadow", text)
        self.assertNotIn("this draft did not use shadow", text)
        self.assertEqual(text, shared_rev.read_text(encoding="utf-8"))
        self.assertEqual(text, ws_rev.read_text(encoding="utf-8"))

    def test_already(self):
        draft = self._write_draft_and_challenge()
        revised = self._inbox_revised()
        revised.parent.mkdir(parents=True, exist_ok=True)
        revised.write_text("existing revised body\n", encoding="utf-8")
        size_before = revised.stat().st_size

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertEqual(revised.stat().st_size, size_before)
        self.assertEqual(revised.read_text(encoding="utf-8"), "existing revised body\n")
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertTrue(draft.is_file())

    def test_no_challenge(self):
        self._draft_path().write_text(DRAFT_BODY, encoding="utf-8")

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertFalse(self._inbox_revised().exists())
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertFalse(self._emily_workspace_revised().exists())

    def test_draft_older_than_challenge(self):
        self._write_draft_and_challenge(draft_age=120.0, challenge_age=10.0)

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertFalse(self._inbox_revised().exists())
        self.assertFalse(self._emily_shared_revised().exists())

    def test_flat_ssot_draft_beats_older_inbox(self):
        now = time.time()
        inbox_draft = self._draft_path()
        inbox_draft.write_text("old inbox draft\n", encoding="utf-8")
        os.utime(inbox_draft, (now - 500, now - 500))

        flat = self.hermes / "shared" / "reports" / "emily" / f"{DATE}-commodity-session.md"
        flat.parent.mkdir(parents=True, exist_ok=True)
        flat.write_text(DRAFT_BODY, encoding="utf-8")
        os.utime(flat, (now - 10, now - 10))

        challenge = self._challenge_path()
        challenge.write_text("zoe challenge\n", encoding="utf-8")
        os.utime(challenge, (now - 60, now - 60))

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        text = self._inbox_revised().read_text(encoding="utf-8")
        self.assertIn("this revised did not use shadow", text)
        self.assertNotIn("old inbox draft", text)
        self.assertTrue(inbox_draft.is_file())
        self.assertTrue(flat.is_file())

    def test_secondary_date_hard_miss_does_not_fail(self):
        self._write_draft_and_challenge()
        revised = self._inbox_revised()
        revised.parent.mkdir(parents=True, exist_ok=True)
        revised.write_text("existing revised body\n", encoding="utf-8")

        other = "2026-09-28"
        orphan = self.inbox / "commodities-session" / f"{other}-commodity-session.md"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_text("orphan draft\n", encoding="utf-8")

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE, "--date", other])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn(f"{DATE} already", out)
        self.assertIn(f"{other} miss-no-challenge", out)
        self.assertFalse(
            (
                self.inbox / "commodities-session" / f"{other}-commodities-session-revised.md"
            ).exists()
        )

    def test_min_age_wait(self):
        self._write_draft_and_challenge(draft_age=1.0, challenge_age=60.0)

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE, "--min-age", "30"])
        self.assertEqual(code, 0)
        self.assertIn("wait", buf.getvalue())
        self.assertFalse(self._inbox_revised().exists())
        self.assertFalse(self._emily_shared_revised().exists())

    def test_direction_gate_blocks_revised_write(self):
        bad = DRAFT_BODY + "\n| Gold | spot +1.20% bullish | x |\n"
        self._write_draft_and_challenge(body=bad)
        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertIn(f"{DATE} miss-direction-gate", buf.getvalue())
        self.assertFalse(self._inbox_revised().exists())
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertFalse(self._emily_workspace_revised().exists())
        self.assertTrue(self._draft_path().is_file())

    def test_clean_price_rows_still_promote(self):
        clean = (
            DRAFT_BODY
            + "\n| Gold | GLD prev close +0.40% | up |\n"
            + "| Silver | SLV prev close +0.20% | up |\n"
            + "| Oil | BZ=F ICE Brent financial futures +0.10% | flat |\n"
            + "CL versus BZ spread is same-source.\n"
        )
        self._write_draft_and_challenge(body=clean)
        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertTrue(self._inbox_revised().is_file())
        self.assertTrue(self._emily_shared_revised().is_file())
        text = self._inbox_revised().read_text(encoding="utf-8")
        self.assertIn("GLD", text)
        self.assertIn("same-source", text)

    def test_clone_blocks_revised_write(self):
        body = f"session {DATE}\nshared commodity note\n"
        draft = self._write_draft_and_challenge(body=body)
        older = draft.parent / "2026-09-22-commodity-session.md"
        older.write_text(
            "session 2026-09-22\nshared commodity note\n",
            encoding="utf-8",
        )
        now = time.time()
        os.utime(older, (now - 100000, now - 100000))

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertIn(f"{DATE} miss-clone", buf.getvalue())
        self.assertFalse(self._inbox_revised().exists())
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertFalse(self._emily_workspace_revised().exists())
        self.assertTrue(draft.is_file())

    def test_older_different_note_is_not_a_clone(self):
        draft = self._write_draft_and_challenge()
        older = draft.parent / "2026-09-22-commodity-session.md"
        older.write_text("a different wheat note\n", encoding="utf-8")
        now = time.time()
        os.utime(older, (now - 100000, now - 100000))

        code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertTrue(self._inbox_revised().is_file())

    def test_older_identical_ignored_when_newer_sibling_differs(self):
        body = f"session {DATE}\nshared commodity note\n"
        draft = self._write_draft_and_challenge(body=body)
        now = time.time()
        ancient = draft.parent / "2026-09-15-commodity-session.md"
        ancient.write_text(
            "session 2026-09-15\nshared commodity note\n",
            encoding="utf-8",
        )
        # Newer mtime than the middle file, but an older date.
        os.utime(ancient, (now - 10, now - 10))
        middle = draft.parent / "2026-09-22-commodity-session.md"
        middle.write_text("a different wheat note\n", encoding="utf-8")
        os.utime(middle, (now - 100000, now - 100000))

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertIn(f"{DATE} promoted", buf.getvalue())
        self.assertNotIn("miss-clone", buf.getvalue())
        self.assertTrue(self._inbox_revised().is_file())
        self.assertIn(
            "shared commodity note",
            self._inbox_revised().read_text(encoding="utf-8"),
        )

    def test_undated_template_does_not_block_promotion(self):
        draft = self._write_draft_and_challenge()
        template = draft.parent / "template-commodity-session.md"
        template.write_text(DRAFT_BODY, encoding="utf-8")
        now = time.time()
        os.utime(template, (now - 100000, now - 100000))

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertIn(f"{DATE} promoted", buf.getvalue())
        self.assertTrue(self._inbox_revised().is_file())
        self.assertTrue(template.is_file())

    def test_existing_revised_matching_newest_older_is_miss_clone(self):
        draft = self._write_draft_and_challenge(
            body="today draft that is not the revised\n"
        )
        now = time.time()
        ancient = draft.parent / "2026-09-15-commodity-session.md"
        ancient.write_text("ancient different note\n", encoding="utf-8")
        os.utime(ancient, (now - 200000, now - 200000))
        older_date = "2026-09-22"
        older = draft.parent / f"{older_date}-commodity-session.md"
        older.write_text(
            f"session {older_date}\nshared commodity note\n",
            encoding="utf-8",
        )
        os.utime(older, (now - 100000, now - 100000))

        revised = self._inbox_revised()
        revised_body = f"session {DATE}\nshared commodity note\n"
        revised.write_text(revised_body, encoding="utf-8")

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertIn(f"{DATE} miss-clone", buf.getvalue())
        self.assertTrue(revised.is_file())
        self.assertEqual(revised.read_text(encoding="utf-8"), revised_body)
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertFalse(self._emily_workspace_revised().exists())

    def test_existing_revised_different_from_newest_older_is_already(self):
        draft = self._write_draft_and_challenge()
        now = time.time()
        ancient_date = "2026-09-15"
        ancient = draft.parent / f"{ancient_date}-commodity-session.md"
        revised_body = f"session {DATE}\nshared commodity note\n"
        ancient.write_text(
            f"session {ancient_date}\nshared commodity note\n",
            encoding="utf-8",
        )
        os.utime(ancient, (now - 200000, now - 200000))
        older = draft.parent / "2026-09-22-commodity-session.md"
        older.write_text("a different wheat note\n", encoding="utf-8")
        os.utime(older, (now - 100000, now - 100000))

        revised = self._inbox_revised()
        revised.write_text(revised_body, encoding="utf-8")
        size_before = revised.stat().st_size

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertIn(f"{DATE} already", buf.getvalue())
        self.assertNotIn("miss-clone", buf.getvalue())
        self.assertEqual(revised.stat().st_size, size_before)
        self.assertEqual(revised.read_text(encoding="utf-8"), revised_body)
        self.assertFalse(self._emily_shared_revised().exists())
        self.assertTrue(draft.is_file())

    def test_friday_clone_in_other_directory_blocks_existing_revised(self):
        flat = (
            self.hermes
            / "shared"
            / "reports"
            / "emily"
            / f"{DATE}-commodity-session.md"
        )
        flat.parent.mkdir(parents=True, exist_ok=True)
        flat.write_text("monday draft that is not the revised\n", encoding="utf-8")
        now = time.time()
        os.utime(flat, (now - 5, now - 5))

        friday = "2026-09-26"
        older = self.inbox / "commodities-session" / f"{friday}-commodity-session.md"
        older.parent.mkdir(parents=True, exist_ok=True)
        older.write_text(
            f"session {friday}\nshared commodity note\n",
            encoding="utf-8",
        )
        os.utime(older, (now - 100000, now - 100000))

        revised = self._inbox_revised()
        revised_body = f"session {DATE}\nshared commodity note\n"
        revised.write_text(revised_body, encoding="utf-8")

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 2)
        self.assertIn(f"{DATE} miss-clone", buf.getvalue())
        self.assertEqual(revised.read_text(encoding="utf-8"), revised_body)

    def test_newer_sibling_in_other_directory_is_the_clone_baseline(self):
        body = f"session {DATE}\nshared commodity note\n"
        draft = self._write_draft_and_challenge(body=body)
        now = time.time()
        local_old = draft.parent / "2026-09-22-commodity-session.md"
        local_old.write_text(
            "session 2026-09-22\nshared commodity note\n",
            encoding="utf-8",
        )
        os.utime(local_old, (now - 100000, now - 100000))

        friday = "2026-09-26"
        newer = (
            self.hermes
            / "shared"
            / "reports"
            / "emily"
            / f"{friday}-commodity-session.md"
        )
        newer.parent.mkdir(parents=True, exist_ok=True)
        newer.write_text("a different wheat note\n", encoding="utf-8")
        os.utime(newer, (now - 50000, now - 50000))

        buf = StringIO()
        with redirect_stdout(buf):
            code = self.mod.main(["--date", DATE])
        self.assertEqual(code, 0)
        self.assertIn(f"{DATE} promoted", buf.getvalue())
        self.assertNotIn("miss-clone", buf.getvalue())
        self.assertTrue(self._inbox_revised().is_file())


if __name__ == "__main__":
    unittest.main()
