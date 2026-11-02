#!/usr/bin/env python3
"""Unit tests for mercury_decide ENFORCE sidecar (no live API / Telegram)."""
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
    spec = importlib.util.spec_from_file_location("mercury_decide", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class MercuryDecideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def test_stricter_verdict(self):
        self.assertEqual(self.m.stricter_verdict("PASS", "CONDITIONAL"), "CONDITIONAL")
        self.assertEqual(self.m.stricter_verdict("REJECT", "PASS"), "REJECT")
        self.assertEqual(self.m.stricter_verdict("PASS", "PASS"), "PASS")

    def test_mode_off_sat_fail_open_approve(self):
        cands = [
            {
                "topic_id": "t-a",
                "title": "Cite checker",
                "assignee": "eliza",
                "priority": "High",
                "actionable": True,
            }
        ]
        out = self.m.decide_sat_topics(cands, mode="off", week="2026-W42")
        self.assertEqual(out["status"], "OFF")
        self.assertEqual(out["approve_topic_ids"], ["t-a"])
        self.assertEqual(out["items"][0]["decision"], "APPROVE")

    def test_sat_unavailable_fail_open(self):
        cands = [
            {
                "topic_id": "t-b",
                "title": "Topic B",
                "assignee": "alice",
                "priority": "High",
                "actionable": True,
            }
        ]
        with mock.patch.object(self.m, "call_decisions", return_value=(None, "http 502")):
            out = self.m.decide_sat_topics(cands, mode="enforce", week="2026-W42")
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")
        self.assertEqual(out["approve_topic_ids"], ["t-b"])

    def test_sat_enforce_thresholds(self):
        cands = [
            {"topic_id": "hi", "title": "Hi", "assignee": "alice", "priority": "High", "actionable": True},
            {"topic_id": "mid", "title": "Mid", "assignee": "renee", "priority": "High", "actionable": True},
            {"topic_id": "lo", "title": "Lo", "assignee": "emily", "priority": "High", "actionable": True},
        ]

        def fake_call(*, state, questions, timeout=45.0, retries=1):
            answers = {
                "spawn_hi": {"noul": 0.9},
                "roi_hi": {"score": 0.8},
                "spawn_mid": {"noul": 0.4},
                "roi_mid": {"score": 0.4},
                "spawn_lo": {"noul": 0.1},
                "roi_lo": {"score": 0.1},
            }
            return {"answers": answers}, "ok"

        with mock.patch.object(self.m, "call_decisions", side_effect=fake_call):
            out = self.m.decide_sat_topics(cands, mode="enforce", week="2026-W42")
        self.assertEqual(out["status"], "OK")
        by_id = {i["topic_id"]: i["decision"] for i in out["items"]}
        self.assertEqual(by_id["hi"], "APPROVE")
        self.assertEqual(by_id["mid"], "DEFER")
        self.assertEqual(by_id["lo"], "REJECT")
        self.assertEqual(out["approve_topic_ids"], ["hi"])

    def test_zoe_escalate_only(self):
        text = '{"verdict":"PASS","severity":"ok","summary":"ok","items":[]}'

        def fake_call(*, state, questions, timeout=45.0, retries=1):
            return {
                "answers": {
                    "publishable": {"noul": 0.2},
                    "invented_numbers": {"noul": 0.8},
                    "has_session_summary": {"noul": 0.9},
                    "invention_risk": {"score": 0.9},
                    "agree_with_zoe": {"score": 0.2},
                    "would_verdict": {"choice": "REJECT"},
                }
            }, "ok"

        with mock.patch.object(self.m, "call_decisions", side_effect=fake_call):
            out = self.m.decide_zoe_challenge(
                text, mode="enforce", profile="zoe", artifact_path="/tmp/c.md"
            )
        self.assertEqual(out["zoe_verdict"], "PASS")
        self.assertEqual(out["final_verdict"], "REJECT")
        self.assertTrue(str(out["action"]).startswith("escalate"))

    def test_zoe_unavailable_keeps_verdict(self):
        text = '{"verdict":"CONDITIONAL","severity":"major","summary":"x","items":[]}'
        with mock.patch.object(self.m, "call_decisions", return_value=(None, "timeout")):
            out = self.m.decide_zoe_challenge(
                text, mode="enforce", profile="zoe", artifact_path="/tmp/c.md"
            )
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")
        self.assertEqual(out["final_verdict"], "CONDITIONAL")
        self.assertEqual(out["action"], "FAIL-OPEN")

    def test_telegram_format_has_yes_no_and_scores(self):
        ledger = {
            "mode": "enforce",
            "scope": "zoe_challenge",
            "status": "OK",
            "profile": "zoe",
            "artifact": "x.md",
            "zoe_verdict": "PASS",
            "decide_verdict": "CONDITIONAL",
            "final_verdict": "CONDITIONAL",
            "action": "escalate->CONDITIONAL",
            "items": [
                {
                    "yes_no": [{"id": "publishable", "yes": 0.3, "no": 0.7}],
                    "scores": [{"id": "invention_risk", "value": 0.55}],
                }
            ],
            "ledger_path": "/tmp/x.decide.json",
        }
        msg = self.m.format_telegram(ledger)
        self.assertTrue(msg.startswith("ENFORCE"), msg[:40])
        self.assertIn("Yes 0.30", msg)
        self.assertIn("No 0.70", msg)
        self.assertIn("metric invention_risk=0.55", msg)
        self.assertNotIn("score ", msg)

    def test_env_off_overrides_cli_enforce(self):
        with mock.patch.dict(os.environ, {"MERCURY_DECIDE_MODE": "off"}, clear=False):
            self.assertEqual(self.m.resolve_mode("enforce"), "off")

    def test_env_off_overrides_cli_enforce_when_cli_missing(self):
        env = {k: v for k, v in os.environ.items() if k != "MERCURY_DECIDE_MODE"}
        env["MERCURY_DECIDE_MODE"] = "off"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.m.resolve_mode(None), "off")

    def test_openrouter_api_key_empty_when_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(self.m, "hermes_home", return_value=Path("/nonexistent/hermes_empty")):
                self.assertEqual(self.m.openrouter_api_key(), "")

    def test_load_candidates_wrapper_object(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "c.json"
            path.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "topic_id": "w1",
                                "title": "Wrapped",
                                "assignee": "alice",
                                "priority": "High",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            loaded = self.m.load_candidates(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["topic_id"], "w1")

    def test_format_telegram_off_prefix_no_bare_score(self):
        for mode in ("off", "enforce"):
            ledger = {
                "mode": mode,
                "scope": "zoe_challenge",
                "status": "OFF" if mode == "off" else "OK",
                "profile": "zoe",
                "artifact": "a.md",
                "zoe_verdict": "PASS",
                "decide_verdict": "PASS",
                "final_verdict": "PASS",
                "action": "keep",
                "items": [
                    {
                        "yes_no": [{"id": "publishable", "yes": 0.5, "no": 0.5}],
                        "scores": [{"id": "invention_risk", "value": 0.1}],
                    }
                ],
            }
            msg = self.m.format_telegram(ledger)
            self.assertTrue(
                msg.startswith("ENFORCE") or msg.startswith("OFF"),
                msg[:40],
            )
            self.assertNotIn("score ", msg)

    def test_stamp_only_marks_spawned_no_api(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            week = "2026-W42"
            ledger_path = root / "ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "mode": "enforce",
                        "scope": "sat_topics",
                        "week": week,
                        "approve_topic_ids": ["t-stamp", "t-skip"],
                        "items": [],
                    }
                ),
                encoding="utf-8",
            )
            stamp_dir = root / "shared" / "reports" / "mercury" / "spawned"
            stamp_dir.mkdir(parents=True)
            (stamp_dir / f"{week}.json").write_text(
                json.dumps({"week": week, "topic_ids": ["t-skip"]}),
                encoding="utf-8",
            )
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "call_decisions") as api:
                    rc = self.m.main(
                        [
                            "--scope",
                            "sat",
                            "--week",
                            week,
                            "--stamp-only",
                            "--ledger",
                            str(ledger_path),
                        ]
                    )
            self.assertEqual(rc, 0)
            api.assert_not_called()
            stamp = json.loads((stamp_dir / f"{week}.json").read_text(encoding="utf-8"))
            self.assertIn("t-stamp", stamp["topic_ids"])
            self.assertIn("t-skip", stamp["topic_ids"])

    def test_cli_sat_filters_already_spawned(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            week = "2026-W99"
            cands = root / "c.json"
            cands.write_text(
                json.dumps(
                    [
                        {
                            "topic_id": "new-one",
                            "title": "New",
                            "assignee": "alice",
                            "priority": "High",
                            "actionable": True,
                        },
                        {
                            "topic_id": "old-one",
                            "title": "Old",
                            "assignee": "renee",
                            "priority": "High",
                            "actionable": True,
                        },
                    ]
                ),
                encoding="utf-8",
            )
            stamp_dir = root / "shared" / "reports" / "mercury" / "spawned"
            stamp_dir.mkdir(parents=True)
            (stamp_dir / f"{week}.json").write_text(
                json.dumps({"week": week, "topic_ids": ["old-one"]}),
                encoding="utf-8",
            )
            out = root / "out.json"

            def fake_call(*, state, questions, timeout=45.0, retries=1):
                answers = {}
                for c in state.get("candidates") or []:
                    tid = c["topic_id"].replace("-", "_")
                    answers[f"spawn_{tid}"] = {"noul": 0.9}
                    answers[f"roi_{tid}"] = {"score": 0.8}
                return {"answers": answers}, "ok"

            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "call_decisions", side_effect=fake_call):
                    with mock.patch.object(self.m, "send_telegram"):
                        rc = self.m.main(
                            [
                                "--scope",
                                "sat",
                                "--week",
                                week,
                                "--candidates",
                                str(cands),
                                "--out",
                                str(out),
                                "--no-telegram",
                            ]
                        )
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["approve_topic_ids"], ["new-one"])
            self.assertEqual(data["skipped_already_spawned"], ["old-one"])

    def test_cli_sat_no_telegram(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cands = root / "c.json"
            cands.write_text(
                json.dumps(
                    [
                        {
                            "topic_id": "t1",
                            "title": "A",
                            "assignee": "alice",
                            "priority": "High",
                            "actionable": True,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            out = root / "out.json"
            with mock.patch.object(self.m, "hermes_home", return_value=root):
                with mock.patch.object(self.m, "call_decisions", return_value=(None, "http 502")):
                    with mock.patch.object(self.m, "send_telegram") as tg:
                        rc = self.m.main(
                            [
                                "--scope",
                                "sat",
                                "--week",
                                "2026-W42",
                                "--candidates",
                                str(cands),
                                "--out",
                                str(out),
                                "--no-telegram",
                            ]
                        )
            self.assertEqual(rc, 0)
            tg.assert_not_called()
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["approve_topic_ids"], ["t1"])

    def test_missing_confidence_safe(self):
        """Optional confidence must not KeyError."""
        answers = {"spawn_x": {"noul": 0.7}, "roi_x": {"score": 0.6}}
        self.assertIsNone(answers.get("confidence"))
        yn = self.m._noul_pair(answers, "spawn_x")
        self.assertAlmostEqual(yn["yes"], 0.7)


if __name__ == "__main__":
    unittest.main()
