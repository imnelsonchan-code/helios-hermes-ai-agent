#!/usr/bin/env python3
"""Contract tests for emily P1 profile files (no network)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from public_snapshot import skip_unless_host_file

ROOT = Path(__file__).resolve().parents[2]
APPLY_SCRIPT = ROOT / "scripts" / "apply-to-hermes.sh"
APPLY_MD = ROOT / "docs" / "APPLY.md"
HERMES_CTL = ROOT / "scripts" / "hermes-ctl.sh"
EMILY = ROOT / "profiles" / "emily"
SKILLS = [
    "commodity-session-report",
    "commodity-signal-table",
    "world-to-commodity",
    "commodity-puzzle",
    "commodity-sources-crawl",
]
TICKERS = [
    "XAUUSD=X",
    "XAGUSD=X",
    "HG=F",
    "ZS=F",
    "ZW=F",
    "ZC=F",
    "CL=F",
    "BZ=F",
    "CC=F",
    "SB=F",
    "KC=F",
    "SGLN.L",
    "PHAG.L",
    "COPA.L",
    "SOYB",
    "WEAT",
    "CORN",
    "NIB",
    "CANE",
    "JO",
]


class TestEmilyP1Contracts(unittest.TestCase):
    def test_soul_and_checklist_exist(self) -> None:
        self.assertTrue((EMILY / "SOUL.md").is_file())
        self.assertTrue((EMILY / "skills-checklist.md").is_file())

    def test_five_skills(self) -> None:
        for name in SKILLS:
            path = EMILY / "skills" / name / "SKILL.md"
            self.assertTrue(path.is_file(), msg=f"missing {path}")

    def test_firewall_and_risk(self) -> None:
        soul = (EMILY / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("emily", soul)
        self.assertRegex(soul, r"Emily.*broker|broker.*Emily|≠ Emily", re.I)
        self.assertIn("Risk-on", soul)
        self.assertIn("commodity_signal", soul)
        self.assertIn("C_BUY", soul)
        self.assertIn("commodity_regime", soul)
        self.assertIn("commodities-session", soul)
        self.assertIn("*-revised.md", soul)

    def test_trunk_has_scaffolds(self) -> None:
        trunk = (
            EMILY / "skills" / "commodity-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Daily scaffold", trunk)
        self.assertIn("Weekly scaffold", trunk)
        self.assertIn("shared/reports/emily/", trunk)
        self.assertGreaterEqual(trunk.count("## Session summary"), 2)
        self.assertIn("inbox/commodities-session", trunk)
        self.assertRegex(trunk, r"\$REPORTS_INBOX/|workspace/reports/inbox")
        self.assertIn("❌ `~/.hermes/shared/inbox/`", trunk)
        self.assertIn("shared/reports/<profile>/inbox/", trunk)
        self.assertIn("*-revised.md", trunk)
        self.assertIn("commodity_regime", trunk)
        for t in TICKERS:
            self.assertIn(t, trunk)

    def test_portal_inbox_unlock(self) -> None:
        """P3: lift shared-only / no-Jobs ban; require portal revised path."""
        soul = (EMILY / "SOUL.md").read_text(encoding="utf-8")
        checklist = (EMILY / "skills-checklist.md").read_text(encoding="utf-8")
        trunk = (
            EMILY / "skills" / "commodity-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        blob = soul + checklist + trunk
        self.assertRegex(
            blob,
            r"inbox/commodities-session|commodities-session/.*revised",
        )
        self.assertIn("$REPORTS_INBOX/", soul)
        self.assertIn("❌ `~/.hermes/shared/inbox/`", soul)
        self.assertRegex(
            blob,
            r"draft\s*->\s*Zoe|Zoe.*emily\s*revise|emily revise",
            re.I,
        )
        # Must not still hard-ban portal Jobs / inbox as the only policy
        self.assertNotRegex(
            soul,
 r"❌\s* Jobs light\s*·\s*❌\s* session `inbox/`",
        )
        self.assertNotRegex(
            trunk,
 r"❌\s*do not `inbox/` session \s*·\s*❌\s*do not Jobs light",
        )

    def test_no_xag_crypto(self) -> None:
        for name in SKILLS:
            text = (EMILY / "skills" / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            # Allow ban mentions of XAG-USD but not as primary ticker assignment
            if "XAG-USD" in text:
                self.assertRegex(
                    text,
 r"(❌||do not |ban).{0,40}XAG-USD|XAG-USD.{0,40}(crypto||❌)",
                    msg=f"{name} mentions XAG-USD without ban context",
                )

    def test_signal_enum(self) -> None:
        sig = (
            EMILY / "skills" / "commodity-signal-table" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in ("C_BUY", "C_WAIT", "C_HOLD", "C_REDUCE", "NO_SETUP"):
            self.assertIn(token, sig)
        self.assertIn("commodity_signal_breakdown", sig)
        self.assertIn("tm_score", sig)  # banned mention expected

    def test_alice_stub(self) -> None:
        alice = (ROOT / "profiles" / "alice" / "SOUL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("shared/reports/emily/", alice)
        self.assertIn("cite", alice.lower())

    @skip_unless_host_file(APPLY_SCRIPT, "apply-to-hermes.sh absent in public snapshot")
    def test_apply_script_lists_emily(self) -> None:
        script = APPLY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EMILY_SKILLS", script)
        self.assertIn("commodity-session-report", script)
        self.assertIn("emily", script)
        self.assertIn("eia-wpsr", script)
        self.assertIn("usda-wasde-psd", script)
        self.assertIn("cftc-cot-disagg", script)

    @skip_unless_host_file(APPLY_MD, "docs/APPLY.md absent in public snapshot")
    def test_apply_md_documents_emily_later_stubs(self) -> None:
        apply = APPLY_MD.read_text(encoding="utf-8")
        self.assertIn("eia-wpsr", apply)
        self.assertIn("usda-wasde-psd", apply)
        self.assertIn("cftc-cot-disagg", apply)
        self.assertRegex(
            apply,
 r"Later stubs.*NOT.*Keep|Later stubs.*do not |NOT.*Keep daily",
            re.I,
        )

    def test_christina_macro_bridge_prefer1_inbox_before_shared_t1_miss(self) -> None:
        """Wave2 lock: inbox/rates-session is prefer-1; T-1 / yesterday shared lock must miss."""
        text = (
            EMILY / "skills" / "christina-macro-bridge" / "SKILL.md"
        ).read_text(encoding="utf-8")
        inbox = "inbox/rates-session"
        shared = "shared/reports/christina"
        self.assertIn("prefer-1", text)
        self.assertIn(inbox, text)
        self.assertIn(shared, text)
        self.assertLess(
            text.find(inbox),
            text.find(shared),
            msg="inbox/rates-session must list before shared/reports/christina as prefer-1",
        )
        self.assertIn("T-1", text)
        self.assertIn("yesterday", text)
        self.assertRegex(
            text,
            r"(T-1|yesterday).{0,160}miss",
            msg="T-1 / yesterday lock must miss",
        )

    @skip_unless_host_file(HERMES_CTL, "hermes-ctl.sh absent in public snapshot")
    def test_hermes_ctl_chat_routes_emily(self) -> None:
        ctl = HERMES_CTL.read_text(encoding="utf-8")
        self.assertRegex(
            ctl,
            r"alice\|renee\|eliza\|zoe\|emily(\|christina)?\|sarah",
            msg="hermes-ctl chat usage must list emily",
        )
        self.assertRegex(
            ctl,
            r"\^\(default\|alice\|renee\|eliza\|zoe\|emily(\|christina)?\|sarah\)\$",
            msg="hermes-ctl chat profile regex must include emily",
        )


if __name__ == "__main__":
    unittest.main()
