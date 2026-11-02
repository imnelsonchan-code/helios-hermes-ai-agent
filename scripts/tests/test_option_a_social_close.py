#!/usr/bin/env python3
"""Option A contract checks for social watcher + market-close cite-only + news analysis."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

from public_snapshot import skip_unless_host_file

ROOT = Path(__file__).resolve().parents[2]
ALICE_SOUL = ROOT / "profiles/alice/SOUL.md"
ALICE_CHECK = ROOT / "profiles/alice/skills-checklist.md"
LEADERS = ROOT / "profiles/alice/x-finance-leaders.md"
CLOSE_SKILL = ROOT / "profiles/alice/skills/market-close-news-social/SKILL.md"
ZOE_SOUL = ROOT / "profiles/zoe/SOUL.md"
CRON_DOCS = ROOT / "docs/cron-jobs.md"
PROFILES = ROOT / "docs/PROFILES.md"
APPLY = ROOT / "docs/APPLY.md"


class OptionASocialCloseContracts(unittest.TestCase):
    def test_leaders_file_has_tiers_and_twenty(self):
        text = LEADERS.read_text(encoding="utf-8")
        self.assertIn("tier-1", text)
        self.assertIn("rotate", text)
        self.assertGreaterEqual(len(re.findall(r"@[A-Za-z0-9_]+", text)), 20)
        for handle in ("@elonmusk", "@CathieDWood", "@BillAckman", "@zerohedge"):
            self.assertIn(handle, text)

    def test_alice_soul_snapshot_and_cite_only(self):
        text = ALICE_SOUL.read_text(encoding="utf-8")
        checklist = ALICE_CHECK.read_text(encoding="utf-8")
        self.assertIn("Social snapshot (Mon–Sat", text)
        self.assertIn("x-finance-leaders.md", checklist)
        self.assertIn("Anti-wrap", text)
        self.assertIn("cite-only", text)
        self.assertIn("do not re-run Top-20", text)
        self.assertIn("weak_signal", text)

    def test_anti_wrap_hard_ban_standalone_macro_notes(self):
        soul = ALICE_SOUL.read_text(encoding="utf-8")
        check = ALICE_CHECK.read_text(encoding="utf-8")
        leaders = LEADERS.read_text(encoding="utf-8")
        for blob in (soul, check, leaders):
            self.assertRegex(blob, r"[Mm]acro/policy Notes")
        self.assertIn("Anti-wrap hard ban", check)
        self.assertIn("regime_chatter", soul)
        self.assertRegex(check, r"ApeWisdom")
        if CRON_DOCS.is_file():
            cron = CRON_DOCS.read_text(encoding="utf-8")
            self.assertIn("hard anti-wrap", cron)

    def test_alice_checklist_splits_watcher_and_close(self):
        text = ALICE_CHECK.read_text(encoding="utf-8")
        self.assertIn("Social snapshot (Mon–Sat watcher)", text)
        self.assertIn("daily-social/` companion ≠ `social-watch/", text)
        self.assertIn("skills/market-close-news-social", text)
        self.assertIn("news_macro", text)
        self.assertIn("bear_risk", text)

    def test_alice_close_news_lenses_and_analysis(self):
        soul = ALICE_SOUL.read_text(encoding="utf-8")
        self.assertIn("news_macro", soul)
        self.assertIn("social_discussion", soul)
        self.assertIn("bear_risk", soul)
        self.assertRegex(
            soul + CLOSE_SKILL.read_text(encoding="utf-8"),
            r"[Ff]inancial news analysis|headline ledger",
        )
        self.assertIn("headline ledger", soul)
        close = CLOSE_SKILL.read_text(encoding="utf-8")
        self.assertIn("not headlines-only", close)
        self.assertIn("x_influence", soul)
        self.assertIn("market-close-news-social", soul)

    def test_close_skill_template_exists(self):
        self.assertTrue(CLOSE_SKILL.is_file(), f"missing {CLOSE_SKILL}")
        text = CLOSE_SKILL.read_text(encoding="utf-8")
        self.assertIn("name: market-close-news-social", text)
        self.assertIn("news_macro", text)
        self.assertIn("social_discussion", text)
        self.assertIn("bear_risk", text)
        self.assertIn("Headline ledger", text)
        self.assertIn("Alice analysis", text)
        self.assertIn("not headlines-only", text)
        self.assertIn("Sources", text)
        self.assertIn("social-watch snapshot", text)
        self.assertIn("does **not** re-run Top-20", text)
        self.assertNotIn("live x crawl required", text.lower())

    def test_zoe_market_close_social_cite_rule(self):
        text = ZOE_SOUL.read_text(encoding="utf-8")
        self.assertIn("Market-close social claims", text)
        self.assertIn("social-watch/*-snapshot.md", text)
        self.assertIn("does **not** re-scan", text)
        self.assertIn("Financial news analysis", text)
        self.assertIn("headlines-only", text)
        self.assertIn("missing Sources", text)

    @skip_unless_host_file(CRON_DOCS, "docs/cron-jobs.md absent in public snapshot")
    def test_docs_separate_paths_and_cite_only(self):
        cron = CRON_DOCS.read_text(encoding="utf-8")
        profiles = PROFILES.read_text(encoding="utf-8")
        self.assertIn("tier-1 X leaders", cron)
        self.assertIn("social cite-only", cron)
        self.assertIn("path ≠ `social-watch/`", cron)
        self.assertIn("news_macro", cron)
        self.assertIn("skills/market-close-news-social", cron)
        self.assertIn("daily-social/` is the **market-close companion**", profiles)
        self.assertIn("cite-only", profiles)
        self.assertIn("financial news analysis", profiles)
        if APPLY.is_file():
            apply = APPLY.read_text(encoding="utf-8")
            self.assertIn("market-close-news-social", apply)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
