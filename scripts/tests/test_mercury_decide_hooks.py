#!/usr/bin/env python3
"""Prompt hooks must reference mercury_decide.py, ENFORCE, and fail-open wording."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "host"


def _load_module(name: str, filename: str):
    path = HOST / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class MercuryDecideHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily = _load_module("desk_pack_daily_train_prompts", "desk_pack_daily_train_prompts.py")
        cls.weekly = _load_module("desk_pack_weekly_prompts", "desk_pack_weekly_prompts.py")

    def _assert_hook_contract(self, hook: str) -> None:
        self.assertIn("mercury_decide.py", hook)
        self.assertIn("ENFORCE", hook)
        self.assertIn("Fail-open", hook)
        self.assertIn("DECIDE_UNAVAILABLE", hook)
        self.assertIn("MERCURY_DECIDE_MODE=off", hook)
        self.assertRegex(hook, r"(?i)must be absolute|\*\*\s*absolute\s*\*\*")
        self.assertIn("final_verdict", hook)
        self.assertIn("~/.hermes/shared/reports/zoe/", hook)

    def test_daily_zoe_hook(self):
        self._assert_hook_contract(self.daily.MERCURY_DECIDE_ZOE_HOOK)

    def test_weekly_zoe_hook(self):
        self._assert_hook_contract(self.weekly.MERCURY_DECIDE_ZOE_HOOK)


if __name__ == "__main__":
    unittest.main()
