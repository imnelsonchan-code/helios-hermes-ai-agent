#!/usr/bin/env python3
"""Contract tests for christina P2 profile files (no network)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from public_snapshot import skip_unless_host_file

ROOT = Path(__file__).resolve().parents[2]
APPLY_SCRIPT = ROOT / "scripts" / "apply-to-hermes.sh"
HERMES_CTL = ROOT / "scripts" / "hermes-ctl.sh"
CHRISTINA = ROOT / "profiles" / "christina"
SKILLS = [
    "curve-watch",
    "real-rates",
    "fedwatch-consume",
    "bond-etf-tape",
    "fx-us-uk-bridge",
    "rates-session-report",
]
LADDER = [
    "TLT",
    "LQD",
    "HYG",
    "SHY",
    "DX-Y",
]

INBOX_CONTRACT = (
    "$REPORTS_INBOX/",
    "❌ `~/.hermes/shared/inbox/`",
    "shared/reports/<profile>/inbox/",
)


class TestChristinaP2Contracts(unittest.TestCase):
    def test_soul_and_checklist_exist(self) -> None:
        self.assertTrue((CHRISTINA / "SOUL.md").is_file())
        self.assertTrue((CHRISTINA / "skills-checklist.md").is_file())

    def test_six_skills(self) -> None:
        for name in SKILLS:
            path = CHRISTINA / "skills" / name / "SKILL.md"
            self.assertTrue(path.is_file(), msg=f"missing {path}")

    def test_firewall_and_b_signals(self) -> None:
        soul = (CHRISTINA / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("christina", soul)
        self.assertIn("observation only", soul.lower())
        self.assertIn("B_LONG", soul)
        self.assertIn("B_WAIT", soul)
        self.assertIn("B_HOLD", soul)
        self.assertIn("B_SHORT", soul)
        self.assertIn("rates_signal", soul)
        self.assertIn("rates-session", soul)
        self.assertIn("*-revised.md", soul)
        self.assertRegex(soul, r"bare\s*`?BUY`?|❌.*BUY|bare `BUY`", re.I)

    def test_trunk_has_scaffolds_and_ladder(self) -> None:
        trunk = (
            CHRISTINA / "skills" / "rates-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("shared/reports/christina/", trunk)
        self.assertIn("rates-session.md", trunk)
        self.assertIn("<job-id>", trunk)
        self.assertGreaterEqual(trunk.count("## Session summary"), 2)
        self.assertIn("inbox/rates-session", trunk)
        for token in INBOX_CONTRACT:
            self.assertIn(token, trunk)
        self.assertIn("*-revised.md", trunk)
        for t in LADDER:
            self.assertIn(t, trunk)

    def test_portal_inbox_unlock(self) -> None:
        """P3: lift shared-only / no-Jobs ban; require portal revised path."""
        soul = (CHRISTINA / "SOUL.md").read_text(encoding="utf-8")
        checklist = (CHRISTINA / "skills-checklist.md").read_text(
            encoding="utf-8"
        )
        trunk = (
            CHRISTINA / "skills" / "rates-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        blob = soul + checklist + trunk
        self.assertRegex(
            blob,
            r"inbox/rates-session|rates-session/.*revised",
        )
        for token in INBOX_CONTRACT:
            self.assertIn(token, soul)
        self.assertRegex(
            blob,
            r"draft\s*->\s*Zoe|Zoe.*christina\s*revise|christina revise",
            re.I,
        )

    def test_fedwatch_consume_only(self) -> None:
        fw = (
            CHRISTINA / "skills" / "fedwatch-consume" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("<job-id>", fw)
        self.assertIn("consume", fw.lower())
        self.assertRegex(fw, r"cron-run|❌.*cron", re.I)
        self.assertIn("latest.json", fw)
        self.assertIn("YYYY-MM-DD-fedwatch.json", fw)
        self.assertIn("shared/reports/alice/fedwatch", fw)

    def test_signal_enum_no_c_star_map(self) -> None:
        bond = (
            CHRISTINA / "skills" / "bond-etf-tape" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in ("B_LONG", "B_SHORT", "B_HOLD", "B_WAIT", "NO_SETUP"):
            self.assertIn(token, bond)
        soul = (CHRISTINA / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("C_*", soul)
        self.assertRegex(soul, r"C_\*.*B_\*|B_\*.*C_\*|C_\*↔B_\*")

    def test_alice_rates_cite_stub(self) -> None:
        alice = (ROOT / "profiles" / "alice" / "SOUL.md").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            alice,
            r"shared/reports/christina|inbox/rates-session",
        )
        self.assertIn("cite", alice.lower())

    def test_emily_no_longer_offline_christina(self) -> None:
        emily_root = ROOT / "profiles" / "emily"
        texts = [
            (emily_root / "SOUL.md").read_text(encoding="utf-8"),
            (emily_root / "skills-checklist.md").read_text(encoding="utf-8"),
            (
                emily_root
                / "skills"
                / "commodity-session-report"
                / "SKILL.md"
            ).read_text(encoding="utf-8"),
        ]
        joined = "\n".join(texts)
        self.assertNotRegex(
            joined,
            r"christina[^\n]{0,40}(offline|not live)|(offline|not live)[^\n]{0,40}christina",
            msg="emily must not mark christina as offline",
        )
        self.assertIn(
            "shared/reports/christina",
            joined,
            msg="emily should cite christina rates path",
        )

    @skip_unless_host_file(APPLY_SCRIPT, "apply-to-hermes.sh absent in public snapshot")
    def test_apply_script_lists_christina(self) -> None:
        script = APPLY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("CHRISTINA_SKILLS", script)
        self.assertIn("rates-session-report", script)
        self.assertIn("christina", script)

    @skip_unless_host_file(HERMES_CTL, "hermes-ctl.sh absent in public snapshot")
    def test_hermes_ctl_chat_routes_christina(self) -> None:
        ctl = HERMES_CTL.read_text(encoding="utf-8")
        self.assertRegex(
            ctl,
            r"alice\|renee\|eliza\|zoe\|emily\|christina\|sarah",
            msg="hermes-ctl chat usage must list christina",
        )
        self.assertRegex(
            ctl,
            r"\^\(default\|alice\|renee\|eliza\|zoe\|emily\|christina\|sarah\)\$",
            msg="hermes-ctl chat profile regex must include christina",
        )

    def test_bond_etf_conf_stacking(self) -> None:
        bond = (
            CHRISTINA / "skills" / "bond-etf-tape" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("proxy-only", bond)
        self.assertRegex(bond, r"Conf\s*≤\s*L|Conf≤L")
        self.assertRegex(bond, r"min\s*\(|min\(\)|≤\s*L|\*\*≤L\*\*")

    def test_trunk_ccy_fx_basis_news_gate(self) -> None:
        trunk = (
            CHRISTINA / "skills" / "rates-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Ccy", trunk)
        self.assertIn("FX forecast", trunk)
        self.assertIn("FX_*", trunk)
        self.assertRegex(trunk, r"FX.*≤\s*2|full Obs ≤2")
        self.assertIn("DXY", trunk)
        self.assertRegex(trunk, r"require Basis|no Basis")
        self.assertRegex(
            trunk,
            r"Before forecast finalize.*News|News/Market check.*before forecast finalize|Christina-topic",
        )

    def test_zoe_christina_reject_ic(self) -> None:
        zoe = (ROOT / "profiles" / "zoe" / "SOUL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Christina rates", zoe)
        self.assertIn("Basis", zoe)
        self.assertIn("Ccy", zoe)
        self.assertRegex(zoe, r"full Obs levels \*\*>3\*\*|FX full Obs \*\*>2\*\*")
        self.assertIn("unauthorized FedWatch cron", zoe)
        self.assertRegex(zoe, r"calendar miss|no high impact")
        self.assertIn("Bond Obs / Est before FX handoff", zoe)
        self.assertRegex(zoe, r"Reviser.*christina|reviser=`christina`")

    def test_four_specialist_integrate_skill_exists(self) -> None:
        path = (
            ROOT
            / "profiles"
            / "alice"
            / "skills"
            / "four-specialist-integrate"
            / "SKILL.md"
        )
        self.assertTrue(
            path.is_file(),
            msg="P3 requires four-specialist-integrate skill",
        )

    def test_alice_e5_thin_no_shadow_blend(self) -> None:
        alice = (ROOT / "profiles" / "alice" / "SOUL.md").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            alice,
            r"shadow_rates_score|E5\+\+",
            msg="Alice integrator must ban rates/commodity shadow blend",
        )
        self.assertIn("B_*", alice)
        self.assertIn("FX_*", alice)

    def test_fedwatch_stale_hygiene_and_cite_lock(self) -> None:
        fw = (
            CHRISTINA / "skills" / "fedwatch-consume" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("<job-id>", fw)
        self.assertRegex(fw, r"stale|age flagged")
        self.assertIn("data_delay", fw)
        self.assertRegex(
            fw,
            r"entire `## FedWatch`|## FedWatch.*miss",
            msg="stale/age must miss the whole FedWatch section or qualify delay",
        )
        self.assertIn("qualitative bias", fw)
        self.assertIn("Polymarket", fw)
        self.assertIn("ZQ=F", fw)
        self.assertIn("predictmarketcap", fw)
        self.assertRegex(
            fw,
            r"meeting-by-meeting",
            msg="must ban substitute meeting-by-meeting probability tables",
        )
        self.assertRegex(
            fw,
            r"FedWatch cite.*artifact path|artifact path or `miss`",
        )
        self.assertRegex(
            fw,
            r"Polymarket.*FedWatch primary|as FedWatch primary",
            msg="substitutes must not be treated as FedWatch primary",
        )

    def test_fx_obs_geometry_and_wait_slots(self) -> None:
        fx = (
            CHRISTINA / "skills" / "fx-us-uk-bridge" / "SKILL.md"
        ).read_text(encoding="utf-8")
        trunk = (
            CHRISTINA / "skills" / "rates-session-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("FX_LONG", fx)
        self.assertRegex(fx, r"TP\s*>\s*Last")
        self.assertRegex(fx, r"cut\s*<\s*Last")
        self.assertRegex(fx, r"TP\s*<\s*Last")
        self.assertRegex(fx, r"cut\s*>\s*Last")
        self.assertRegex(
            fx,
            r"delete full Obs|full Obs set",
        )
        self.assertIn("FX_WAIT", fx)
        self.assertRegex(fx, r"LLM invent|invent/swap")
        self.assertRegex(
            fx,
            r"FX_WAIT.*does not consume|Daily full Obs TP slot",
        )
        self.assertRegex(
            trunk,
            r"B_WAIT.*FX_WAIT|FX_WAIT.*Daily",
            msg="Daily checklist must keep WAIT out of full Obs TP slots",
        )
        self.assertIn("shared/reports/christina/", trunk)
        self.assertIn("inbox/rates-session", trunk)
        self.assertGreaterEqual(trunk.count("## Session summary"), 2)


if __name__ == "__main__":
    unittest.main()
