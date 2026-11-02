#!/usr/bin/env python3
"""P3a Alice four-specialist-integrate contracts (no network)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from public_snapshot import skip_unless_host_file

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "profiles"
APPLY_SCRIPT = ROOT / "scripts" / "apply-to-hermes.sh"
APPLY_MD = ROOT / "docs" / "APPLY.md"
SKILL = (
    PROFILES / "alice" / "skills" / "four-specialist-integrate" / "SKILL.md"
)

INBOX_CONTRACT = (
    "$REPORTS_INBOX/",
    "❌ `~/.hermes/shared/inbox/`",
    "shared/reports/<profile>/inbox/",
)


class TestAliceFourSpecialistContracts(unittest.TestCase):
    def test_skill_fourteen_sections(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for n in range(1, 15):
            self.assertRegex(text, re.compile(rf"^## {n}\. ", re.M))

    def test_skill_smoke_strings(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for token in (
            "Session summary",
            "Macro view",
            "Market insight",
            "Risk-on",
            "Relationships",
            "callback",
            "≤4",
            "material_gap",
            "four-specialist-integrate",
            "Not investment advice",
            "shared/reports/christina",
            "shared/reports/emily",
        ):
            self.assertIn(token, text)
        self.assertRegex(text, r"commodities-session|rates-session")
        self.assertRegex(text, r"miss.*still|still ships")
        for token in INBOX_CONTRACT:
            self.assertIn(token, text)
        self.assertRegex(text, r"stem-only|stem shorthand")

    def test_skill_callback_budgets(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, r"Daily.*≤1|≤1.*material_gap")
        self.assertRegex(text, r"Weekly.*≤4|≤4.*total")

    def test_alice_soul_and_checklist_wired(self) -> None:
        alice = (PROFILES / "alice" / "SOUL.md").read_text(encoding="utf-8")
        checklist = (PROFILES / "alice" / "skills-checklist.md").read_text(
            encoding="utf-8"
        )
        blob = alice + checklist
        self.assertIn("four-specialist-integrate", blob)
        self.assertIn("E5++", alice)
        self.assertIn("shadow_rates_score", alice)
        self.assertRegex(alice, r"cite christina|christina.*cite", re.I)
        self.assertRegex(alice, r"DXY|FX_\*")
        self.assertIn("Cadence (P3a", checklist)
        self.assertIn("Daily lite", checklist)
        self.assertIn("Sun deep-dive", checklist)
        self.assertIn("Macro view", checklist)

    @skip_unless_host_file(APPLY_SCRIPT, "apply-to-hermes.sh absent in public snapshot")
    def test_apply_lists_four_specialist(self) -> None:
        script = APPLY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("four-specialist-integrate", script)
        self.assertRegex(
            script,
            r"ALICE_SKILLS=\([\s\S]*four-specialist-integrate",
        )
        self.assertRegex(
            script,
            r"for skill in \$\{ALICE_SKILLS\[\*\]\}",
        )
        self.assertIn("four-specialist-integrate", script)

    def test_zoe_daily_callback_budget_reject(self) -> None:
        zoe = (PROFILES / "zoe" / "SOUL.md").read_text(encoding="utf-8")
        self.assertRegex(zoe, r"Daily overall callbacks >1|material_gap: true")

    def test_zoe_four_way_reject(self) -> None:
        zoe = (PROFILES / "zoe" / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Alice four-way integrate", zoe)
        for needle in (
            "Namespace mix",
            "Callback changes lock",
            "cross-link changing",
            "shadow regime",
            "desk composite",
        ):
            self.assertIn(needle, zoe)
        self.assertRegex(zoe, r"reviser=`alice`|Reviser for overall.*alice", re.I)

    def test_renee_callback_anti_mix(self) -> None:
        renee = (PROFILES / "renee" / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Alice callback anti-mix", renee)
        self.assertIn("tm_score", renee)

    def test_eliza_callback_anti_mix(self) -> None:
        eliza = (PROFILES / "eliza" / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Alice callback anti-mix", eliza)
        self.assertRegex(eliza, r"valuation_score|FV")

    def test_hyg_credit_and_dxy_fence(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, r"HYG|credit-spread|credit\(HYG\)")
        self.assertRegex(text, r"DXY.*cite|cite christina")
        self.assertRegex(text, r"❌.*desk Risk-on|map to desk Risk-on")

    def test_skill_four_path_pending_rechallenge(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("pending-rechallenge", text)
        self.assertRegex(
            text, r"ok[`\s]*\|[`\s]*miss[`\s]*\|[`\s]*pending-rechallenge"
        )
        self.assertIn("as-of T-1", text)
        self.assertIn("5/5 revision stands", text)
        self.assertIn("Zoe re-votes", text)
        self.assertRegex(text, r"✅.*Zoe PASS|❌ `✅`")

    def test_skill_daily_relationships_sentences_not_table(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, r"≤2–4 \*\*SENTENCES\*\*|≤2–4 SENTENCES")
        self.assertRegex(text, r"daily MUST NOT.*weekly-style table")
        self.assertIn("table >4 rows = self-check fail", text)

    def test_skill_callback_targets_train_blocking_gap(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("train-blocking", text)
        self.assertIn("material_gap", text)
        self.assertRegex(text, r"unre-challenged")
        self.assertRegex(text, r"T-1 lock")
        self.assertRegex(text, r"same-day Wave1")
        self.assertIn("5bp", text)

    def test_zoe_four_path_overclaim_conditional(self) -> None:
        zoe = (PROFILES / "zoe" / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Alice four-way integrate", zoe)
        self.assertIn("four-path overclaim", zoe)
        self.assertIn("Z-MI-05", zoe)
        self.assertIn("5/5 revision stands", zoe)
        self.assertRegex(zoe, r"T-1|unre-challenged")
        self.assertRegex(zoe, r"Major.*CONDITIONAL|CONDITIONAL")

    def test_news_social_and_yaml_honesty(self) -> None:
        close = (
            PROFILES
            / "alice"
            / "skills"
            / "market-close-news-social"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        yaml = (
            PROFILES / "desk" / "workflows" / "desk-pack-daily.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("pending-rechallenge", close)
        self.assertRegex(close, r"unre-challenged|T-1")
        self.assertIn("same-session Wave1 inbox", yaml)
        self.assertIn("honest four-path", yaml)
        self.assertIn("Zoe ran ≠ PASS", yaml)
        self.assertNotRegex(yaml, r"[0-9a-f]{12}")

    def test_overall_trunk_is_ten_headings_with_own_summary(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        fmt = (
            PROFILES / "alice" / "skills" / "market-close-report-format" / "SKILL.md"
        ).read_text(encoding="utf-8")
        weekly = (
            PROFILES / "alice" / "skills" / "alice-weekly-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        headings = (
            "## Header",
            "## Session summary",
            "## News / social / macro",
            "## Four Market insights",
            "## Four Session summaries",
            "## Macro view",
            "## Relationships",
            "## Desk Risk-on/off",
            "## Gaps / callbacks",
            "## Sources",
        )
        for text in (skill, fmt, weekly):
            for heading in headings:
                self.assertIn(heading, text)
            for token in INBOX_CONTRACT:
                self.assertIn(token, text)
        close = (
            PROFILES
            / "alice"
            / "skills"
            / "market-close-news-social"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in INBOX_CONTRACT:
            self.assertIn(token, close)
        self.assertIn("market-close-news-social` **D**", skill)
        self.assertNotIn("market-close-news-social` C +", skill)
        self.assertIn("Legacy twelve sections", fmt)
        self.assertIn("§3.3", weekly)
        self.assertIn("GICS 11", weekly)
        soul = (PROFILES / "alice" / "SOUL.md").read_text(encoding="utf-8")
        for token in INBOX_CONTRACT:
            self.assertIn(token, soul)
        self.assertIn("daily ≤1", soul)
        self.assertIn("weekly ≤4", soul)
        # Public scrub: SOUL must not embed live-looking 12-hex cron IDs
        self.assertNotRegex(soul, r"(?i)(?<!\w)[0-9a-f]{12}(?!\w)")
        self.assertRegex(soul, r"Adhoc:")
        self.assertNotIn("callback ≤4(daily ≤1", soul)
        if APPLY_MD.is_file():
            apply = APPLY_MD.read_text(encoding="utf-8")
            self.assertNotIn("no second Jobs light", apply)
            self.assertIn("own** portal Jobs lights", apply)


if __name__ == "__main__":
    unittest.main()
