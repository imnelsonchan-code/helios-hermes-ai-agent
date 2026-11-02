#!/usr/bin/env python3
"""Unit tests for tm_score_publish.py (CLIP+RAW)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"


def _load(name: str):
    path = HOST / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TmScorePublishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load("tm_score_publish")

    def test_clip_over_100(self):
        self.assertEqual(self.mod.clip_published(118.2), 100.0)
        pair = self.mod.publish_pair(118.2)
        self.assertEqual(pair["published"], 100.0)
        self.assertEqual(pair["weighted_total_raw"], 118.2)

    def test_unchanged_in_band(self):
        self.assertEqual(self.mod.clip_published(93.6), 93.6)
        pair = self.mod.publish_pair(93.6)
        self.assertEqual(pair["published"], 93.6)
        self.assertEqual(pair["weighted_total_raw"], 93.6)

    def test_clip_just_over_100(self):
        self.assertEqual(self.mod.clip_published(100.8), 100.0)
        pair = self.mod.publish_pair(100.8)
        self.assertEqual(pair["published"], 100.0)
        self.assertEqual(pair["weighted_total_raw"], 100.8)

    def test_negative_safety(self):
        self.assertEqual(self.mod.clip_published(-3.2), 0.0)
        pair = self.mod.publish_pair(-3.2)
        self.assertEqual(pair["published"], 0.0)
        self.assertEqual(pair["weighted_total_raw"], -3.2)

    def test_exact_100(self):
        self.assertEqual(self.mod.clip_published(100.0), 100.0)
        pair = self.mod.publish_pair(100)
        self.assertEqual(pair["published"], 100.0)
        self.assertEqual(pair["weighted_total_raw"], 100.0)


if __name__ == "__main__":
    unittest.main()
