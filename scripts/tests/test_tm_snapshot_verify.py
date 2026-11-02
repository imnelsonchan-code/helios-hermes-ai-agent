#!/usr/bin/env python3
"""Unit tests for scripts/host/tm_snapshot_verify.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
VERIFY_PATH = HOST_DIR / "tm_snapshot_verify.py"


def _load(name: str = "tm_snapshot_verify"):
    spec = importlib.util.spec_from_file_location(name, VERIFY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


PACK = {
    "results": [
        {
            "ticker": "BETA",
            "tm_score": 72.5,
            "close": 500.0,
            "score_breakdown": {"macd": 18.0, "rsi": 14.0},
        }
    ]
}


class TmSnapshotVerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_matching_claims_no_discrepancies(self):
        claims = [
            {"ticker": "BETA", "field": "tm_score", "claimed_value": 72.5},
            {"ticker": "BETA", "field": "close", "claimed_value": 500.0},
        ]
        d = self.mod.verify_claims(self.mod.extract_pack_rows(PACK), claims)
        self.assertEqual(d, [])

    def test_score_mismatch_detected(self):
        claims = [{"ticker": "BETA", "field": "tm_score", "claimed_value": 80.0}]
        d = self.mod.verify_claims(self.mod.extract_pack_rows(PACK), claims)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["status"], "mismatch")

    def test_price_within_one_percent(self):
        claims = [{"ticker": "BETA", "field": "close", "claimed_value": 504.9}]
        d = self.mod.verify_claims(self.mod.extract_pack_rows(PACK), claims)
        self.assertEqual(d, [])

    def test_rejects_value_sleeve_fields(self):
        claims = [{"ticker": "BETA", "field": "valuation_score", "claimed_value": 65}]
        d = self.mod.verify_claims(self.mod.extract_pack_rows(PACK), claims)
        self.assertEqual(d[0]["status"], "rejected")

    def test_cli_writes_out_json(self):
        claims = [{"ticker": "BETA", "field": "tm_score", "claimed_value": 72.5}]
        with tempfile.TemporaryDirectory() as td:
            pack_path = Path(td) / "pack.json"
            claims_path = Path(td) / "claims.json"
            out_path = Path(td) / "out.json"
            pack_path.write_text(json.dumps(PACK), encoding="utf-8")
            claims_path.write_text(json.dumps(claims), encoding="utf-8")
            rc = self.mod.main(
                ["--pack", str(pack_path), "--claims", str(claims_path), "--out", str(out_path)]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["discrepancy_count"], 0)
            self.assertEqual(payload["sleeve"], "tm")


if __name__ == "__main__":
    unittest.main()
