#!/usr/bin/env python3
"""Review-pass regressions for mercury_decide (key resolution, fail-open, stamp-only, paths)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOST = Path(__file__).resolve().parents[1] / "host"


def _load():
    path = HOST / "mercury_decide.py"
    spec = importlib.util.spec_from_file_location("mercury_decide_review", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _cand(tid: str, **kw):
    d = {"topic_id": tid, "title": tid, "assignee": "alice", "priority": "High", "actionable": True}
    d.update(kw)
    return d


class KeyResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def _clean_env(self):
        env = {k: v for k, v in os.environ.items() if k not in ("OPENROUTER_API_KEY", "HERMES_HOME")}
        return mock.patch.dict(os.environ, env, clear=True)

    def test_key_from_hermes_dotenv(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("OTHER=1\nOPENROUTER_API_KEY=sk-test-hermes\n", encoding="utf-8")
            with self._clean_env(), mock.patch.object(self.m, "hermes_home", return_value=root):
                self.assertEqual(self.m.openrouter_api_key(), "sk-test-hermes")

    def test_key_env_wins_over_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("OPENROUTER_API_KEY=from-file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "from-env"}):
                with mock.patch.object(self.m, "hermes_home", return_value=root):
                    self.assertEqual(self.m.openrouter_api_key(), "from-env")

    def test_dotenv_export_quotes_and_comment(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            for body, want in (
                ('export OPENROUTER_API_KEY="abc 123"  # note\n', "abc 123"),
                ("OPENROUTER_API_KEY='q-key'\n", "q-key"),
                ("OPENROUTER_API_KEY=plain # trailing\n", "plain"),
                ("# OPENROUTER_API_KEY=commented\n", ""),
                ("OPENROUTER_API_KEY=\n", ""),
            ):
                p.write_text(body, encoding="utf-8")
                self.assertEqual(self.m._env_file_key(p), want, body)

    def test_profile_home_normalised_to_root(self):
        with mock.patch.dict(os.environ, {"HERMES_HOME": "/x/.hermes/profiles/zoe"}):
            self.assertEqual(self.m.hermes_home(), Path("/x/.hermes"))
        with mock.patch.dict(os.environ, {"HERMES_HOME": "/x/.hermes"}):
            self.assertEqual(self.m.hermes_home(), Path("/x/.hermes"))

    def test_missing_key_is_unavailable_not_crash(self):
        with self._clean_env(), mock.patch.object(self.m, "hermes_home", return_value=Path("/nonexistent/h")):
            with mock.patch.object(self.m, "_env_file_key", return_value=""):
                payload, detail = self.m.call_decisions(state={}, questions={})
        self.assertIsNone(payload)
        self.assertIn("unset", detail)

    def test_key_never_in_detail_or_telegram(self):
        secret = "sk-SECRET-VALUE-123"

        class Boom(Exception):
            pass

        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": secret}):
            with mock.patch("urllib.request.urlopen", side_effect=Boom("net down")):
                payload, detail = self.m.call_decisions(state={}, questions={}, retries=0)
        self.assertIsNone(payload)
        self.assertNotIn(secret, detail)


class FailOpenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def test_sat_empty_answers_is_unavailable(self):
        with mock.patch.object(self.m, "call_decisions", return_value=({"answers": {}}, "ok")):
            out = self.m.decide_sat_topics([_cand("a")], mode="enforce", week="2026-W42")
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")
        self.assertEqual(out["approve_topic_ids"], ["a"])
        msg = self.m.format_telegram(out)
        self.assertIn("FAIL-OPEN", msg)
        self.assertTrue(msg.startswith("ENFORCE"))

    def test_sat_foreign_answer_keys_is_unavailable(self):
        with mock.patch.object(self.m, "call_decisions", return_value=({"answers": {"zzz": {"noul": 0.1}}}, "ok")):
            out = self.m.decide_sat_topics([_cand("a")], mode="enforce", week="2026-W42")
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")

    def test_sat_partial_missing_noul_flagged(self):
        def fake(*, state, questions, timeout=45.0, retries=1):
            return {"answers": {"spawn_a": {"noul": 0.9}, "roi_a": {"score": 0.5}}}, "ok"

        with mock.patch.object(self.m, "call_decisions", side_effect=fake):
            out = self.m.decide_sat_topics([_cand("a"), _cand("b")], mode="enforce", week="2026-W42")
        self.assertEqual(out["status"], "PARTIAL_FAIL_OPEN")
        self.assertEqual(out["fail_open_topic_ids"], ["b"])
        self.assertEqual(out["approve_topic_ids"], ["a", "b"])
        self.assertIn("FAIL-OPEN", self.m.format_telegram(out))

    def test_zoe_empty_answers_is_unavailable(self):
        text = '{"verdict":"CONDITIONAL"}'
        with mock.patch.object(self.m, "call_decisions", return_value=({"answers": {}}, "ok")):
            out = self.m.decide_zoe_challenge(text, mode="enforce", profile="zoe", artifact_path="/t/c.md")
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")
        self.assertEqual(out["final_verdict"], "CONDITIONAL")
        self.assertEqual(out["action"], "FAIL-OPEN")
        self.assertIn("FAIL-OPEN", self.m.format_telegram(out))

    def test_zoe_off_telegram_says_fail_open(self):
        out = self.m.decide_zoe_challenge('{"verdict":"PASS"}', mode="off", profile="zoe", artifact_path="a.md")
        msg = self.m.format_telegram(out)
        self.assertTrue(msg.startswith("OFF"))
        self.assertIn("FAIL-OPEN", msg)

    def test_zoe_never_relaxes(self):
        def fake(*, state, questions, timeout=45.0, retries=1):
            return {
                "answers": {
                    "publishable": {"noul": 0.99},
                    "invented_numbers": {"noul": 0.0},
                    "has_session_summary": {"noul": 1.0},
                    "would_verdict": {"choice": "PASS"},
                }
            }, "ok"

        with mock.patch.object(self.m, "call_decisions", side_effect=fake):
            out = self.m.decide_zoe_challenge('{"verdict":"REJECT"}', mode="enforce", profile="zoe", artifact_path="a")
        self.assertEqual(out["final_verdict"], "REJECT")
        self.assertEqual(out["action"], "keep")

    def test_unparsed_zoe_verdict_flagged(self):
        v, parsed = self.m.parse_zoe_verdict("## IC vote\nlooks fine")
        self.assertEqual((v, parsed), ("PASS", False))
        self.assertEqual(self.m.parse_zoe_verdict("verdict: **REJECT**"), ("REJECT", True))
        out = self.m.decide_zoe_challenge("no verdict here", mode="off", profile="zoe", artifact_path="a")
        self.assertFalse(out["zoe_verdict_parsed"])
        self.assertIn("UNPARSED", self.m.format_telegram(out))

    def test_http_auth_error_not_retried(self):
        import urllib.error

        calls = []

        def boom(req, timeout=0):
            calls.append(1)
            raise urllib.error.HTTPError("u", 401, "no", {}, None)

        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "k"}):
            with mock.patch("urllib.request.urlopen", side_effect=boom):
                payload, detail = self.m.call_decisions(state={}, questions={}, retries=3)
        self.assertIsNone(payload)
        self.assertEqual(detail, "http 401")
        self.assertEqual(len(calls), 1)

    def test_question_key_collision_and_duplicates(self):
        keys = self.m.question_keys([_cand("a-b"), _cand("a_b")])
        self.assertEqual(len(set(keys.values())), 2)

        seen = {}

        def fake(*, state, questions, timeout=45.0, retries=1):
            seen["q"] = list(questions)
            return {"answers": {k: {"noul": 0.9} for k in questions if k.startswith("spawn_")}}, "ok"

        with mock.patch.object(self.m, "call_decisions", side_effect=fake):
            out = self.m.decide_sat_topics(
                [_cand("dup"), _cand("dup"), _cand("x", actionable=False)], mode="enforce", week="W"
            )
        self.assertEqual(out["approve_topic_ids"], ["dup"])
        self.assertEqual(len(seen["q"]), 2)

    def test_actionable_string_false(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps([{"topic_id": "t", "priority": "High", "actionable": "false"}]), encoding="utf-8")
            self.assertFalse(self.m.load_candidates(p)[0]["actionable"])


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def _stamp_dir(self, root: Path) -> Path:
        d = root / "shared" / "reports" / "mercury" / "spawned"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_stamp_only_week_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lp = root / "l.json"
            lp.write_text(json.dumps({"week": "2026-W41", "approve_topic_ids": ["a"]}), encoding="utf-8")
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                rc = self.m.main(["--scope", "sat", "--stamp-only", "--week", "2026-W42", "--ledger", str(lp)])
            self.assertEqual(rc, 2)
            self.assertFalse((self._stamp_dir(root) / "2026-W42.json").exists())

    def test_stamp_only_defaults_to_ledger_week(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lp = root / "l.json"
            lp.write_text(json.dumps({"week": "2026-W41", "approve_topic_ids": ["a"]}), encoding="utf-8")
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                rc = self.m.main(["--scope", "sat", "--stamp-only", "--ledger", str(lp)])
            self.assertEqual(rc, 0)
            stamp = json.loads((self._stamp_dir(root) / "2026-W41.json").read_text(encoding="utf-8"))
            self.assertEqual(stamp["topic_ids"], ["a"])

    def test_stamp_only_only_ids_subset_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lp = root / "l.json"
            lp.write_text(json.dumps({"week": "W1", "approve_topic_ids": ["a", "b", "c"]}), encoding="utf-8")
            argv = ["--scope", "sat", "--stamp-only", "--week", "W1", "--ledger", str(lp), "--only-ids", "a,c"]
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                self.assertEqual(self.m.main(argv), 0)
                self.assertEqual(self.m.main(argv), 0)  # re-run safe
            stamp = json.loads((self._stamp_dir(root) / "W1.json").read_text(encoding="utf-8"))
            self.assertEqual(stamp["topic_ids"], ["a", "c"])

    def test_stamp_only_corrupt_ledger_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lp = root / "l.json"
            lp.write_text("{nope", encoding="utf-8")
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                rc = self.m.main(["--scope", "sat", "--stamp-only", "--week", "W1", "--ledger", str(lp)])
            self.assertEqual(rc, 2)

    def test_sat_bad_candidates_still_writes_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "o.json"
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "send_telegram") as tg:
                    rc = self.m.main(
                        [
                            "--scope", "sat", "--week", "W1",
                            "--candidates", str(root / "missing.json"), "--out", str(out),
                        ]
                    )
            self.assertEqual(rc, 2)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "CANDIDATES_INVALID")
            self.assertEqual(data["approve_topic_ids"], [])
            tg.assert_called_once()

    def test_sat_off_kill_switch_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cands = root / "c.json"
            cands.write_text(json.dumps([_cand("t1")]), encoding="utf-8")
            out = root / "o.json"
            with mock.patch.dict(os.environ, {"MERCURY_DECIDE_MODE": "off"}):
                with mock.patch.object(self.m, "hermes_home", return_value=root):
                    with mock.patch.object(self.m, "call_decisions") as api:
                        rc = self.m.main(
                            ["--scope", "sat", "--mode", "enforce", "--week", "W1",
                             "--candidates", str(cands), "--out", str(out), "--no-telegram"]
                        )
            self.assertEqual(rc, 0)
            api.assert_not_called()
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["status"], "OFF")

    def test_zoe_relative_artifact_anchored_at_hermes_home(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            art = root / "shared" / "reports" / "zoe" / "rates-session" / "2026-10-13-challenge.md"
            art.parent.mkdir(parents=True)
            art.write_text('{"verdict":"PASS"}', encoding="utf-8")
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "call_decisions", return_value=(None, "http 502")):
                    rc = self.m.main(
                        ["--scope", "zoe", "--artifact", "shared/reports/zoe/rates-session/2026-10-13-challenge.md",
                         "--no-telegram"]
                    )
            self.assertEqual(rc, 0)
            self.assertTrue(list((root / "shared" / "reports" / "mercury" / "zoe").glob("*.decide.json")))

    def test_zoe_ledgers_do_not_collide_across_legs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for cat in ("rates-session", "daily-trend-momentum"):
                art = root / "shared" / "reports" / "zoe" / cat / "2026-10-13-challenge.md"
                art.parent.mkdir(parents=True)
                art.write_text('{"verdict":"PASS"}', encoding="utf-8")
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "call_decisions", return_value=(None, "timeout")):
                    for cat in ("rates-session", "daily-trend-momentum"):
                        a = root / "shared" / "reports" / "zoe" / cat / "2026-10-13-challenge.md"
                        self.assertEqual(self.m.main(["--scope", "zoe", "--artifact", str(a), "--no-telegram"]), 0)
            files = list((root / "shared" / "reports" / "mercury" / "zoe").glob("*.decide.json"))
            self.assertEqual(len(files), 2)

    def test_zoe_missing_artifact_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(self.m, "hermes_home", return_value=Path(td)):
                rc = self.m.main(["--scope", "zoe", "--artifact", "shared/nope.md", "--no-telegram"])
            self.assertEqual(rc, 2)

    def test_send_telegram_nonzero_returns_false_without_leak(self):
        proc = mock.Mock(returncode=1, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=proc):
            self.assertFalse(self.m.send_telegram("hello"))
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0)):
            self.assertTrue(self.m.send_telegram("hello"))
        with mock.patch("subprocess.run", side_effect=OSError("no cli")):
            self.assertFalse(self.m.send_telegram("hello"))


if __name__ == "__main__":
    unittest.main()
