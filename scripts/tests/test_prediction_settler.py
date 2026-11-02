#!/usr/bin/env python3
"""Unit tests for scripts/host/prediction_settler.py (not copied to the live host)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
SETTLER_PATH = HOST_DIR / "prediction_settler.py"


def _load_module(name: str = "prediction_settler"):
    if not SETTLER_PATH.is_file():
        raise FileNotFoundError(f"missing {SETTLER_PATH}")
    spec = importlib.util.spec_from_file_location(name, SETTLER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {SETTLER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _pred(**kwargs):
    base = {
        "sleeve": "tm",
        "ticker": "AAA",
        "direction": "long",
        "as_of": "2026-09-01",
        "horizon_end": "2026-09-10",
        "status": "pending",
    }
    base.update(kwargs)
    return _load_module().parse_prediction(base)


class PredictionSettlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_settle_long_hit_and_miss(self):
        hit = self.mod.settle(_pred(direction="long"), entry_price=100.0, mark_price=105.0)
        miss = self.mod.settle(_pred(direction="long"), entry_price=100.0, mark_price=99.0)
        self.assertTrue(hit.hit)
        self.assertEqual(hit.status, "settled")
        self.assertFalse(miss.hit)

    def test_settle_short_hit_and_miss(self):
        hit = self.mod.settle(_pred(direction="short"), entry_price=100.0, mark_price=95.0)
        miss = self.mod.settle(_pred(direction="short"), entry_price=100.0, mark_price=101.0)
        self.assertTrue(hit.hit)
        self.assertFalse(miss.hit)

    def test_settle_flat_near_zero_return(self):
        ok = self.mod.settle(_pred(direction="flat"), entry_price=100.0, mark_price=100.00001, eps=1e-4)
        bad = self.mod.settle(_pred(direction="flat"), entry_price=100.0, mark_price=102.0, eps=1e-4)
        self.assertTrue(ok.hit)
        self.assertEqual(ok.status, "settled")
        self.assertEqual(bad.status, "invalid")
        self.assertIsNone(bad.hit)

    def test_missing_prices_stay_pending(self):
        missing_entry = self.mod.settle(_pred(), entry_price=None, mark_price=100.0)
        self.assertEqual(missing_entry.status, "pending")
        self.assertIsNone(missing_entry.hit)
        self.assertEqual(
            missing_entry.settle_reason, "deferred: missing entry_price or mark_price"
        )

        missing_mark = self.mod.settle(_pred(entry_price=100.0), mark_price=None)
        self.assertEqual(missing_mark.status, "pending")
        self.assertIsNone(missing_mark.hit)
        self.assertEqual(
            missing_mark.settle_reason, "deferred: missing entry_price or mark_price"
        )

        nonpositive_entry = self.mod.settle(
            _pred(), entry_price=0.0, mark_price=100.0
        )
        self.assertEqual(nonpositive_entry.status, "pending")
        self.assertIsNone(nonpositive_entry.hit)
        self.assertEqual(
            nonpositive_entry.settle_reason,
            "deferred: missing entry_price or mark_price",
        )

    def test_missing_mark_deferred_then_settles_when_mark_provided(self):
        pred = _pred(entry_price=100.0)
        deferred = self.mod.settle(pred, mark_price=None)
        self.assertEqual(deferred.status, "pending")
        self.assertIsNone(deferred.hit)
        self.assertEqual(
            deferred.settle_reason, "deferred: missing entry_price or mark_price"
        )

        # Later pass with mark available — must settle successfully (not stuck invalid).
        settled = self.mod.settle(deferred, mark_price=105.0)
        self.assertEqual(settled.status, "settled")
        self.assertTrue(settled.hit)
        self.assertEqual(settled.entry_price, 100.0)
        self.assertEqual(settled.mark_price, 105.0)

    def test_invalid_if_move_threshold(self):
        pred = _pred(invalid_if="move>5%")
        out = self.mod.settle(pred, entry_price=100.0, mark_price=106.0)
        self.assertEqual(out.status, "invalid")

    def test_separate_hit_rates_never_blended(self):
        preds = [
            self.mod.parse_prediction(
                {
                    "sleeve": "tm",
                    "ticker": "AAA",
                    "direction": "long",
                    "as_of": "2026-09-01",
                    "horizon_end": "2026-09-10",
                    "entry_price": 100.0,
                }
            ),
            self.mod.parse_prediction(
                {
                    "sleeve": "tm",
                    "ticker": "BBB",
                    "direction": "long",
                    "as_of": "2026-09-01",
                    "horizon_end": "2026-09-10",
                    "entry_price": 50.0,
                }
            ),
            self.mod.parse_prediction(
                {
                    "sleeve": "value",
                    "ticker": "CCC",
                    "direction": "short",
                    "as_of": "2026-09-01",
                    "horizon_end": "2026-09-10",
                    "entry_price": 20.0,
                }
            ),
        ]
        marks = {"AAA": 110.0, "BBB": 45.0, "CCC": 21.0}
        report = self.mod.settle_all(preds, marks)
        self.assertEqual(report.tm_settled, 2)
        self.assertEqual(report.tm_hits, 1)
        self.assertEqual(report.tm_hit_rate, 0.5)
        self.assertEqual(report.value_settled, 1)
        self.assertEqual(report.value_hits, 0)
        self.assertEqual(report.value_hit_rate, 0.0)
        self.assertNotIn("desk_hit_rate", report.__dict__)

    def test_load_predictions_json_and_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            jpath = Path(tmp) / "preds.json"
            lpath = Path(tmp) / "preds.jsonl"
            one = {
                "sleeve": "value",
                "ticker": "ZZZ",
                "direction": "long",
                "as_of": "2026-09-01",
                "horizon_end": "2026-09-10",
                "entry_price": 10.0,
            }
            jpath.write_text(json.dumps([one]), encoding="utf-8")
            lpath.write_text(json.dumps(one) + "\n", encoding="utf-8")
            self.assertEqual(len(self.mod.load_predictions(str(jpath))), 1)
            self.assertEqual(len(self.mod.load_predictions(str(lpath))), 1)

    def test_cli_writes_out_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_path = Path(tmp) / "preds.json"
            out_path = Path(tmp) / "out.json"
            pred_path.write_text(
                json.dumps(
                    [
                        {
                            "sleeve": "tm",
                            "ticker": "AAA",
                            "direction": "long",
                            "as_of": "2026-09-01",
                            "horizon_end": "2026-09-10",
                            "entry_price": 100.0,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            rc = self.mod.main(
                [
                    "--predictions",
                    str(pred_path),
                    "--marks-json",
                    json.dumps({"AAA": 105.0}),
                    "--out",
                    str(out_path),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["tm_hit_rate"], 1.0)
            self.assertIsNone(payload["value_hit_rate"])
            self.assertNotIn("desk_hit_rate", payload)


if __name__ == "__main__":
    unittest.main()
