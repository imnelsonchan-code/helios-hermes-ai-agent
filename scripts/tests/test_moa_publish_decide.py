#!/usr/bin/env python3
"""Tests for MOA publish Mercury scoring (threshold 90) + rework gate."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOST = Path(__file__).resolve().parents[1] / "host"


def _load(name: str, filename: str):
    path = HOST / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class MoaPublishDecideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = _load("mercury_decide_moa", "mercury_decide.py")
        cls.gate = _load("moa_rework_gate", "moa_rework_gate.py")

    def test_threshold_is_90(self):
        self.assertEqual(self.md.MOA_PUBLISH_THRESHOLD, 90)

    def test_compute_accept_high_quality(self):
        answers = {
            "completeness": {"score": 0.95},
            "coherence": {"score": 0.95},
            "sources_cited": {"noul": 0.95},
            "invented_numbers": {"noul": 0.05},
        }
        out = self.md.compute_moa_publish_score(answers)
        self.assertEqual(out["decision"], "ACCEPT")
        self.assertGreaterEqual(out["publish_score"], 90)

    def test_compute_rework_below_threshold(self):
        answers = {
            "completeness": {"score": 0.75},
            "coherence": {"score": 0.75},
            "sources_cited": {"noul": 0.8},
            "invented_numbers": {"noul": 0.05},
        }
        out = self.md.compute_moa_publish_score(answers)
        self.assertEqual(out["decision"], "REWORK")
        self.assertLess(out["publish_score"], 90)

    def test_invented_numbers_hard_gate(self):
        answers = {
            "completeness": {"score": 1.0},
            "coherence": {"score": 1.0},
            "sources_cited": {"noul": 1.0},
            "invented_numbers": {"noul": 0.7},
        }
        out = self.md.compute_moa_publish_score(answers)
        self.assertEqual(out["decision"], "REWORK")
        self.assertLessEqual(out["publish_score"], 59)
        self.assertTrue(any(d["id"] == "invented_numbers" for d in out["defects"]))

    def test_missing_dimension_rework(self):
        out = self.md.compute_moa_publish_score({"completeness": {"score": 0.9}})
        self.assertEqual(out["decision"], "REWORK")
        self.assertEqual(out["publish_score"], 0)

    def test_decide_moa_off_fail_open(self):
        out = self.md.decide_moa_publish("hello report", mode="off", artifact_path="/tmp/r.md")
        self.assertEqual(out["status"], "OFF")
        self.assertEqual(out["decision"], "ACCEPT")
        self.assertEqual(out["action"], "FAIL-OPEN")

    def test_decide_moa_empty_rework(self):
        out = self.md.decide_moa_publish("  ", mode="enforce", artifact_path="/tmp/r.md")
        self.assertEqual(out["decision"], "REWORK")
        self.assertEqual(out["status"], "EMPTY_REPORT")

    def test_decide_moa_unavailable_fail_open(self):
        with mock.patch.object(self.md, "call_decisions", return_value=(None, "http 502")):
            out = self.md.decide_moa_publish(
                "# MOA report\nbody", mode="enforce", artifact_path="/tmp/r.md"
            )
        self.assertEqual(out["status"], "DECIDE_UNAVAILABLE")
        self.assertEqual(out["decision"], "ACCEPT")
        self.assertEqual(out["action"], "FAIL-OPEN")

    def test_telegram_moa_prefix(self):
        msg = self.md.format_telegram(
            {
                "mode": "enforce",
                "scope": "moa_publish",
                "status": "OK",
                "artifact": "/x.md",
                "attempt": 0,
                "publish_score": 88,
                "threshold": 90,
                "decision": "REWORK",
                "action": "REWORK",
                "dims": {"completeness": 80, "coherence": 80, "sources_cited": 90, "invented_numbers_yes": 0.1},
                "defects": [{"id": "below_threshold", "severity": "major"}],
                "ledger_path": "/tmp/l.json",
            }
        )
        self.assertTrue(msg.startswith("ENFORCE"))
        self.assertIn("publish_score=88", msg)
        self.assertIn("threshold=90", msg)
        self.assertIn("REWORK", msg)
        self.assertNotIn("score ", msg)

    def test_cli_moa_rework_rc1(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "report.md"
            report.write_text("# MOA\nweak report\n", encoding="utf-8")
            out = root / "decide.json"

            def fake_call(*, state, questions, timeout=45.0, retries=1):
                return {
                    "answers": {
                        "completeness": {"score": 0.7},
                        "coherence": {"score": 0.7},
                        "sources_cited": {"noul": 0.7},
                        "invented_numbers": {"noul": 0.1},
                        "blends_e5": {"noul": 0.1},
                    }
                }, "ok"

            with mock.patch.object(self.md, "hermes_home", return_value=root):
                with mock.patch.object(self.md, "call_decisions", side_effect=fake_call):
                    with mock.patch.object(self.md, "send_telegram"):
                        rc = self.md.main(
                            [
                                "--scope",
                                "moa_publish",
                                "--artifact",
                                str(report),
                                "--out",
                                str(out),
                                "--no-telegram",
                            ]
                        )
            self.assertEqual(rc, 1)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["decision"], "REWORK")

    def test_cli_moa_missing_artifact_refuse_rc2(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "missing.md"
            out = root / "decide.json"

            with mock.patch.object(self.md, "hermes_home", return_value=root):
                with mock.patch.object(self.md, "send_telegram"):
                    rc = self.md.main(
                        [
                            "--scope",
                            "moa_publish",
                            "--artifact",
                            str(missing),
                            "--out",
                            str(out),
                            "--no-telegram",
                        ]
                    )
            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())

    def test_gate_writes_rework_brief(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "moa-report.md"
            report.write_text("# title\nbody enough\n", encoding="utf-8")
            out = root / "d.json"
            brief = root / "brief.json"

            def fake_decide(text, *, mode, artifact_path, attempt=0):
                return {
                    "mode": mode,
                    "scope": "moa_publish",
                    "status": "OK",
                    "decision": "REWORK",
                    "action": "REWORK",
                    "publish_score": 80,
                    "threshold": 90,
                    "defects": [{"id": "below_threshold", "severity": "major"}],
                    "dims": {},
                    "attempt": attempt,
                    "artifact": artifact_path,
                }

            with mock.patch.object(self.gate, "_load_mercury", return_value=self.md):
                with mock.patch.object(self.md, "hermes_home", return_value=root):
                    with mock.patch.object(self.md, "decide_moa_publish", side_effect=fake_decide):
                        with mock.patch.object(self.md, "send_telegram"):
                            rc = self.gate.main(
                                [
                                    "--report",
                                    str(report),
                                    "--out",
                                    str(out),
                                    "--rework-brief-out",
                                    str(brief),
                                    "--no-telegram",
                                ]
                            )
            self.assertEqual(rc, 1)
            self.assertTrue(brief.is_file())
            body = json.loads(brief.read_text(encoding="utf-8"))
            self.assertEqual(body["decision"], "REWORK")
            self.assertIn("rework_instructions", body)


if __name__ == "__main__":
    unittest.main()
