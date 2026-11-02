#!/usr/bin/env python3
"""
Zoe Challenge→Revision Tracker — v3 (item-level tracking)

Purpose: Track Zoe challenges at the INDIVIDUAL ITEM level (B1/B2/M1/m1).
Instead of just checking "does a revised file exist?", we now:
  1. Parse each challenge file to extract all item IDs + severity + descriptions
  2. Parse the revision response table to see which items were addressed
  3. Cross-reference: which items are resolved, partial, or missing
  4. Detect recurring issues (same item ID seen again in new challenge)

Item Naming Convention (auto-inferred from challenge file):
  B1, B2, ... = 🔴 Blocker items (in order of appearance)
  M1, M2, ... = 🟡 Major items
  m1, m2, ... = 🔵 Minor items

Revision Response Standard Format (to be filled by Alice/Renee/Eliza):
  ## Zoe Step 3 Challenge Response          ← canonical (Zoe 2026-08-13 B1)
  ## Zoe Challenge Response Tracker         ← legacy, still parsed
  (Step 1d verification trackers use "Step 1d Verification " and are
   a DIFFERENT governance layer — never parsed as a challenge response.)

  | Item | Severity | Brief | Resolution | Status |
  |:----:|:--------:|:------|:-----------|:------:|
  | B1   | 🔴 Blocker | 2s10s spread 63bp error | Switched to FRED T10Y2Y | ✅ |
  | B2   | 🔴 Blocker | COST 1D% -1.57% → -0.29% | Fixed prev_close reference | ✅ |
  | M1   | 🟡 Major | META §8 copy-paste | Unified to +2.55% | 🟡 |

  Status values: ✅ = fully resolved, 🟡 = partially / deferred (⚙️), ❌ = not addressed

Usage:
    python3 zoe_tracker.py                        # full scan (14 days)
    python3 zoe_tracker.py --days 7               # scan last 7 days
    python3 zoe_tracker.py --all                  # show resolved challenges too
    python3 zoe_tracker.py --items                # show item-level detail
    python3 zoe_tracker.py --template <path>      # generate response template from challenge file
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────
ZOE_SHARED_DIR = Path.home() / ".hermes" / "shared" / "reports" / "zoe"
SHARED_REPORTS = Path.home() / ".hermes" / "shared" / "reports"
PROFILE_DIRS = {
    "alice": SHARED_REPORTS / "alice",
    "renee": SHARED_REPORTS / "renee",
    "eliza": SHARED_REPORTS / "eliza",
    "zoe": SHARED_REPORTS / "zoe",
}

STALE_HOURS = 48

# ── Item severity emoji mapping ───────────────────
SEVERITY_MAP = {
    "🔴": "Blocker",
    "🟡": "Major",
    "🔵": "Minor",
}

# Map severity name → short code
SEVERITY_CODE = {
    "Blocker": "B",
    "Major": "M",
    "Minor": "m",
}

# ── Non-challenge file detection ──────────────────

# Files/dirs that are Zoe's own internal docs, NOT challenges to other profiles
NON_CHALLENGE_DIRS = {
    "self-review",          # Zoe's own pipeline quality reviews
    "weekly-self-review",   # Zoe's own weekly self reviews
    "weekly-challenge-review",  # Zoe's own challenge quality reviews
    "lessons",              # Shared lesson docs
    "tracker",              # Zoe challenge→revision tracker internal files
}

# Files to ALWAYS skip
SKIP_FILENAMES = {"README.md"}

# Files that are Zoe internal reviews even if in other dirs
ZOE_INTERNAL_PATTERNS = [
    re.compile(r'zoe-review', re.IGNORECASE),
    re.compile(r'zoe-audit', re.IGNORECASE),
    re.compile(r'pipeline-quality-review', re.IGNORECASE),
    re.compile(r'detail-steps\.md$'),  # Usually zoe's own step docs
]


def _is_challenge_file(path: Path) -> bool:
    """Heuristic: is this file a challenge to another profile?"""
    name = path.name
    if name in SKIP_FILENAMES:
        return False
    if "archive" in path.parts:
        return False

    # ── Step 1d verification namespace separation (Zoe 2026-08-13 B1) ──
    # `-verification.md` files are data-quality audits (Step 1d), NOT Step 3
    # challenges. They reuse the same item-ID scheme (M1-M4/m1-m6/G1-G3) as
    # Step 3 challenges (B1/M1-M6/m1-m5), so scanning them here causes
    # item-ID collision and false recurrence. They are a different governance
    # layer and must be excluded from the challenge→revision tracker.
    if re.search(r'-verification\.md$', name, re.IGNORECASE):
        return False

    # Skip if in a non-challenge directory
    parts = set(path.parts)
    if parts & NON_CHALLENGE_DIRS:
        # Exception: explicitly named "challenge" files in these dirs
        # that target other profiles (rare but possible)
        if "challenge" in name.lower() and "zoe" not in name.lower():
            return True
        return False

    # Skip if matches Zoe internal patterns and NOT a challenge
    for pat in ZOE_INTERNAL_PATTERNS:
        if pat.search(name):
            # Only allow if it also has "challenge" or "review" targeting others
            head = _read_head(path, 15)
            has_challenge_target = (
                "Challenge by:" in head
                or "Target:" in head
                or "" in head
                or "" in head
                or "" in head
                or "" in head
            )
            if not has_challenge_target:
                return False
            # If it has a target, check it's not targeting zoe's own reports
            if "zoe" in head.lower() and "zoe" not in str(path.parent).lower():
                # Might be challenging zoe's own stuff → skip
                if "zoe-review" in name.lower() or "zoe-audit" in name.lower():
                    return False

    # Special: weekly-challenge-review dir files are all Zoe internal
    if "weekly-challenge-review" in str(path):
        return False

    return True


# ── Item-level parsing (v3 feature) ───────────────

# Pattern: ## <N>. <emoji> <Severity> — <Title>
ITEM_HEADING_PATTERN = re.compile(
    r'^##\s+(\d+)\.\s+([🔴🟡🔵])\s*(Blocker|Major|Minor)\s*[—–-]\s*(.+)$',
    re.MULTILINE
)


def parse_challenge_items(challenge_path: Path) -> list[dict]:
    """Extract individual challenge items from a Zoe challenge file.

    Returns list of dicts:
        {
            "item_id": "B1", "severity": "Blocker", "severity_emoji": "🔴",
            "title": "2s10s Spread ",
            "required_fix": " FRED T10Y2Y...", # from target section heading
        }
    """
    if not challenge_path.exists():
        return []

    head = _read_head(challenge_path, 500)
    if not head:
        return []

    matches = ITEM_HEADING_PATTERN.findall(head)
    if not matches:
        # Fallback: daily-social challenges (Zoe 2026-08-13+) use a
        # "Challenge Points" TABLE, not `## N. 🔴 Blocker — Title` headings.
        # Without this fallback item-level tracking silently returned [] for
        # the entire daily-social flow.
        return _parse_challenge_items_table(head)

    # Counters per severity for ID assignment
    counters = {"Blocker": 0, "Major": 0, "Minor": 0}
    items = []

    for seq, emoji, severity, title in matches:
        counters[severity] += 1
        code = SEVERITY_CODE.get(severity, "?")
        item_id = f"{code}{counters[severity]}"

        # Try to find "Required fix:" section after this heading
        fix_text = ""
        # Simple: find the line number of this match and look for "Required fix:" or "Required fix" after it
        match_pos = head.find(f"## {seq}. {emoji} {severity}")
        if match_pos >= 0:
            search_start = head.find("**Required fix:**", match_pos)
            if search_start < 0:
                search_start = head.find("Required fix:", match_pos)
            if search_start >= 0:
                # Read lines until next ## heading or end
                end_pos = head.find("\n## ", search_start + 15)
                if end_pos < 0:
                    end_pos = len(head)
                fix_text = head[search_start:end_pos].strip()
                # Clean up markdown bold markers
                fix_text = fix_text.replace("**Required fix:**", "").replace("Required fix:", "").strip()

        items.append({
            "item_id": item_id,
            "seq": int(seq),
            "severity": severity,
            "severity_emoji": emoji,
            "title": title.strip(),
            "required_fix": fix_text,
        })

    return items


def _parse_challenge_items_table(head: str) -> list[dict]:
    """Parse challenge items from the "Challenge Points" table format.

    Daily-social challenges (Zoe 2026-08-13+) use:
        | # | Issue | Severity | Evidence | Fix Recommendation |
        | B1 | **...** | 🔴 P0 | ... | ... |

    The item id (B1/M1/m1) is already in the first column; the severity emoji
    lives in the "Severity" column. Returns the same dict shape as the
    heading-based parser so cross_reference_items() works unchanged.
    """
    items = []
    in_table = False
    sev_col = 2  # default Severity column index (0-based)
    for line in head.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]

        if not in_table:
            has_hash = any(c in ("#", "Item", "No.", "ID") for c in cells)
            sev_idx = next((i for i, c in enumerate(cells) if "everity" in c), None)
            if has_hash and sev_idx is not None:
                in_table = True
                sev_col = sev_idx
            continue

        # Separator row (|---|:---:|...|)
        if all(set(c) <= set(":- ") for c in cells if c):
            continue

        if not cells:
            continue
        raw_id = cells[0].strip().strip("*").strip()
        if not re.fullmatch(r"[BMmG]\d+", raw_id):
            continue

        # Severity emoji is read ONLY from the Severity column — the Issue
        # column often embeds 🟡/🔴 emojis in prose and must not be scanned.
        sev_cell = cells[sev_col] if sev_col < len(cells) else ""
        sev, emoji = "Minor", "🔵"
        if "🔴" in sev_cell:
            sev, emoji = "Blocker", "🔴"
        elif "🟡" in sev_cell:
            sev, emoji = "Major", "🟡"
        elif "🔵" in sev_cell:
            sev, emoji = "Minor", "🔵"

        items.append({
            "item_id": raw_id,
            "seq": len(items) + 1,
            "severity": sev,
            "severity_emoji": emoji,
            "title": (cells[1][:160] if len(cells) > 1 else "").strip("*").strip(),
            "required_fix": "",
        })

    return items


def parse_revision_response(revised_path: Path) -> dict[str, dict]:
    """Parse the standardized revision response table.

    Looks for the "Zoe Challenge Response Tracker" table and extracts
    per-item resolution status.

    Expected table format:
        | Item | Severity | Brief | Resolution | Status |
        |:----:|:--------:|:------|:-----------|:------:|
        | B1   | 🔴 Blocker | ... | ... | ✅ |
        | B2   | 🔴 Blocker | ... | ... | 🟡 |
        | M1   | 🟡 Major | ... | ... | ❌ |

    Returns dict keyed by item_id:
        {"B1": {"severity": "🔴 Blocker", "brief": "...", "resolution": "...",
                "status": "✅", "status_label": "resolved",
                "status_emoji": "✅"}, ...}

    Also checks for alternate table headers:
    - "Zoe Challenge Resolution"
    - "# | Severity" format (older style)
    """
    if not revised_path or not revised_path.exists():
        return {}

    content = _read_head(revised_path, 500)
    if not content:
        return {}

    result = {}

    # ── Pattern 1: Standard format ──
    # Recognised Step 3 challenge-response section headers (namespace-aware).
    #   Canonical (new, Zoe 2026-08-13 B1 fix): "Zoe Step 3 Challenge Response"
    #   Legacy: "Zoe Challenge Response Tracker" / "Zoe Challenge Resolution"
 # Step 1d verification trackers ("Step 1d Verification ") are a
    # DIFFERENT governance layer and must NEVER be matched here — their item
    # IDs (M1-M4/m1-m6/G1-G3) collide with Step 3 IDs (B1/M1-M6/m1-m5).
    table_start = None
    for header in ["Zoe Step 3 Challenge Response",
                   "Zoe Challenge Response Tracker",
                   "Zoe Challenge Resolution"]:
        pos = content.find(header)
        if pos < 0:
            continue
        # Reject matches that live inside a Step 1d verification section.
        prefix = content[max(0, pos - 160):pos]
        if "Step 1d" in prefix or "Verification " in prefix or "1d Verification" in prefix:
            continue
        table_start = pos
        break

    if table_start is None:
        return result

    table_section = content[table_start:]
    lines = table_section.split("\n")
    in_table = False
    for line in lines:
        line_stripped = line.strip()
        # Skip header — supports both "| Item | Severity" and "| # | Severity"
        if in_table is False and ("Item" in line_stripped and "Severity" in line_stripped):
            in_table = True
            continue
        if in_table is False and line_stripped.startswith("| # |") and "Severity" in line_stripped:
            in_table = True
            continue
        if not in_table:
            continue
        # Separator line — skip
        if line_stripped.startswith("|:") or line_stripped.startswith("||:"):
            continue
        # Check for end of table (empty line or next heading)
        if line_stripped == "" or line_stripped.startswith("#") or line_stripped.startswith("---"):
            break
        if not line_stripped.startswith("|"):
            break

        # Parse table row
        parts = [p.strip() for p in line_stripped.split("|")]
        # Remove leading/trailing empty from split (the outer | chars)
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]

        # Handle both formats:
        # Format A (standard 5-col): ['B1', '🔴 Blocker', 'Brief', 'Resolution', '✅']
 # Format B (legacy 4-col, status embedded): ['B1', '🔴 Blocker', 'Issue', 'Resolution...✅ ']
        # Format C (double-pipe legacy): ['', 'B1', ... '', ''] → same as A/B after cleanup

        if len(parts) >= 5:
            item_id = parts[0].strip().strip("*").strip()   # strip **bold** markers
            severity = parts[1].strip()
            brief = parts[2].strip()
            resolution = parts[3].strip()
            status = _extract_status_emoji(parts[4])
        elif len(parts) == 4:
            # Legacy 4-col: status embedded in last column
            item_id = parts[0].strip().strip("*").strip()   # strip **bold** markers
            severity = parts[1].strip()
            brief = parts[2].strip()
            combined = parts[3].strip()
            # Extract status emoji from end of combined field
            status = _extract_trailing_emoji(combined)
            resolution = combined
        else:
            continue

        # Handle empty or combined status
        if not status or status == "":
            status = "✅"

        status_label = {
            "✅": "resolved",
            "🟡": "partial",
            "❌": "not_addressed",
            "⏳": "pending",
            "⚙️": "partial",  # deferred / code follow-up — not fully resolved
        }.get(status, "unknown")

        result[item_id] = {
            "severity": severity,
            "brief": brief,
            "resolution": resolution,
            "status": status,
            "status_label": status_label,
        }

    return result


def _extract_trailing_emoji(text: str) -> str:
    """Extract trailing status emoji from combined resolution text.
    e.g. ' FRED... ✅ ' → '✅'"""
    for emoji in ["✅", "🟡", "❌", "⏳"]:
        # Check last occurrence (status emoji near end)
        pos = text.rfind(emoji)
        if pos >= 0 and len(text) - pos < 30:  # emoji within last 30 chars
            return emoji
    return ""


def _extract_status_emoji(text: str) -> str:
    """Extract a status emoji from a status cell.

    Handles both bare emoji ('✅') and prose-prefixed cells
    ('✅ + escalate') — returns the first recognised status emoji.
    Leading ⚙️ (first non-space char) is deferred / acknowledged → 🟡
    (not fully resolved ✅, not forgotten ⏳).
    Falls back to trailing emoji for legacy cells ending in a status mark.
    """
    text = text.lstrip()
    if text.startswith("⚙️"):
        return "🟡"
    for emoji in ["✅", "🟡", "❌", "⏳"]:
        if text.startswith(emoji):
            return emoji
    trailing = _extract_trailing_emoji(text)
    if trailing:
        return trailing
    return text  # unrecognised → keep raw text (maps to 'unknown')


def generate_response_template(challenge_path: Path) -> str:
    """Generate a pre-filled revision response table for a challenge file.

    Outputs the standardized table with item IDs, severity, and brief
    filled in. Resolution and Status left blank for the responder to fill.
    """
    items = parse_challenge_items(challenge_path)
    if not items:
        return "(No challenge items found in file)"

    lines = [
        "## Zoe Step 3 Challenge Response",
        "",
        "| Item | Severity | Brief | Resolution | Status |",
        "|:----:|:--------:|:------|:-----------|:------:|",
    ]

    for item in items:
        emoji = item["severity_emoji"]
        sev = item["severity"]
        brief = item["title"]
        lines.append(f"| {item['item_id']} | {emoji} {sev} | {brief} | _(describe fix)_ | ⏳ |")

    lines.append("")
    lines.append("**Status key:** ✅ = fully resolved, 🟡 = partially, ❌ = not addressed, ⏳ = pending")
    lines.append("")

    return "\n".join(lines)


def cross_reference_items(
    challenge_items: list[dict],
    response_items: dict[str, dict]
) -> dict:
    """Cross-reference challenge items against revision response.

    Returns:
        {
            "total": 6,
            "resolved": 4,
            "partial": 1,
            "not_addressed": 0,
            "missing": 1,        # items in challenge but NOT in response
            "items": [
                {"item_id": "B1", "severity": "Blocker", "status": "resolved", ...},
                ...
            ]
        }
    """
    counts = {"resolved": 0, "partial": 0, "not_addressed": 0, "pending": 0, "missing": 0}
    item_results = []

    for ci in challenge_items:
        item_id = ci["item_id"]
        ridata = response_items.get(item_id)
        if ridata:
            label = ridata.get("status_label", "unknown")
            counts[label] = counts.get(label, 0) + 1
            item_results.append({
                "item_id": item_id,
                "severity": ci["severity"],
                "severity_emoji": ci["severity_emoji"],
                "title": ci["title"],
                "status": label,
                "status_emoji": ridata.get("status", "❓"),
                "resolution": ridata.get("resolution", ""),
            })
        else:
            counts["missing"] += 1
            item_results.append({
                "item_id": item_id,
                "severity": ci["severity"],
                "severity_emoji": ci["severity_emoji"],
                "title": ci["title"],
                "status": "missing",
                "status_emoji": "❌",
                "resolution": "(not addressed in revision)",
            })

    return {
        "total": len(challenge_items),
        "resolved": counts.get("resolved", 0),
        "partial": counts.get("partial", 0),
        "not_addressed": counts.get("not_addressed", 0),
        "pending": counts.get("pending", 0),
        "missing": counts.get("missing", 0),
        "items": item_results,
    }


# ── Target extraction ─────────────────────────────

def _read_head(path: Path, lines: int = 50) -> str:
    """Read first N lines of a file."""
    try:
        with open(path) as f:
            out = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                out.append(line)
            return "".join(out)
    except Exception:
        return ""


def _resolve_path(raw: str) -> str:
    """Normalize a path string to absolute."""
    raw = raw.strip()
    if raw.startswith("~"):
        return str(Path(raw).expanduser())
    if raw.startswith("/home/") or raw.startswith("/opt/"):
        # Map legacy /opt/data/reports/ → ~/.hermes/shared/reports/
        if "/opt/data/reports/" in raw:
            mapped = raw.replace("/opt/data/reports/", str(SHARED_REPORTS) + "/")
            # Only map if original doesn't exist but mapped does
            if not Path(raw).exists() and Path(mapped).exists():
                return mapped
        return raw
    if raw.startswith("shared/reports/"):
        return str(Path.home() / ".hermes" / raw)
    return raw


def _search_target_by_name(
    fname: str, profile_hint: str | None, challenge_dir: Path
) -> tuple[str | None, str | None]:
    """Search for a target file by name across profile directories."""
    # Try exact match in all profile dirs
    for prof, pdir in PROFILE_DIRS.items():
        for cand in pdir.rglob(fname):
            if cand.is_file():
                return str(cand), prof

    # Try common subdirs
    for prof, pdir in PROFILE_DIRS.items():
        for sub in ["weekly-deep-dive", "market-close", "daily-trend-momentum",
                     "daily-social", "self-review", "macro-daily", "inbox"]:
            cand = pdir / sub / fname
            if cand.exists():
                return str(cand), prof

    # If profile hint given, use it as best guess
    if profile_hint and profile_hint in PROFILE_DIRS:
        # Guess based on filename pattern
        if "W" in fname and fname[0:2] == "20":
            return str(PROFILE_DIRS[profile_hint] / "weekly-deep-dive" / fname), profile_hint
        if re.match(r"20\d\d-\d\d-\d\d", fname):
            return str(PROFILE_DIRS[profile_hint] / "market-close" / fname), profile_hint
        return str(PROFILE_DIRS[profile_hint] / "self-review" / fname), profile_hint

    return None, None


def _extract_target(challenge_path: Path) -> tuple[str | None, str | None]:
    """Parse challenge file to find target report path and profile.

    Returns (target_path, profile) or (None, None).
    """
    head = _read_head(challenge_path, 50)
    if not head:
        return None, None

    lines = head.split("\n")

    # ── Pattern 1: Explicit paths in backticks or plain ──
    path_patterns = [
        re.compile(r'`((?:~?/?(?:home/\w+/)?\.?hermes)?/?shared/reports/(\w+)/[^`]+\.md)`'),
        # Legacy /opt/data/reports/ paths
        re.compile(r'`(/opt/data/reports/(\w+)/[^`]+\.md)`'),
        # Absolute path without backticks: /home/.../.hermes/shared/reports/...
        re.compile(r'(/home/\w+/\.hermes/shared/reports/(\w+)/\S+\.md)'),
 # Report path prefix: **：** `/path`
        re.compile(r'[：:]\s*`?((?:/~?)?(?:home/\w+/)?\.?hermes/shared/reports/(\w+)/\S+\.md)`?'),
 # /: `/opt/data/reports/...`
        re.compile(r'(?:|)[：:]\s*`(/opt/data/reports/(\w+)/[^`]+\.md)`'),
    ]

    for pat in path_patterns:
        for m in pat.finditer(head):
            raw = m.group(1)
            profile = m.group(2)
            resolved = _resolve_path(raw)
            if Path(resolved).exists():
                return resolved, profile
            # Even if not exists, return it (might be a target that hasn't been created yet)
            return resolved, profile

 # ── Pattern 2: Relative filename in Target: / ──
    rel_patterns = [
        re.compile(r'(?:Target|||)[：:]\s*(?:[^`\n]*)?`([^`]+\.md)`'),
        re.compile(r'`(20\d\d-[^`\s]+\.md)`'),  # Any dated filename
        re.compile(r'`([0-9A-Za-z_-]+\.md)`'),   # Any .md filename in backticks
    ]

    for pat in rel_patterns:
        for m in pat.finditer(head):
            fname = m.group(1).strip()
            if "challenge" in fname.lower():
                continue
            if "/" in fname:
                continue  # already handled above
            # Try to find this file
            target, prof = _search_target_by_name(fname, None, challenge_path.parent)
            if target:
                return target, prof
            # Not found but might be future target → best guess
            prof_guess = "alice"  # default
            if "renee" in head.lower():
                prof_guess = "renee"
            elif "eliza" in head.lower():
                prof_guess = "eliza"
            return str(PROFILE_DIRS[prof_guess] / "self-review" / fname), prof_guess

    # ── Pattern 3: Descriptive target (no file path) ──
    desc_patterns = [
        re.compile(r'(?:Target||)[：:]\s*(\w+)\s+(.+?)(?:\n|$)'),
    ]

    for pat in desc_patterns:
        m = pat.search(head)
        if m:
            profile_hint = m.group(1).lower()
            desc = m.group(2).strip()
            if profile_hint not in PROFILE_DIRS:
                profile_hint = "alice"

            # Try to extract a date from description
            date_match = re.search(r'(20\d\d-\d\d-\d\d)', desc)
            week_match = re.search(r'(W\d\d)', desc)

            if date_match:
                date_str = date_match.group(1)
                for sub in ["daily-trend-momentum", "market-close", "daily-social",
                             "macro-daily"]:
                    cand = PROFILE_DIRS[profile_hint] / sub
                    for f in cand.glob(f"{date_str}*.md"):
                        if "challenge" not in f.name.lower():
                            return str(f), profile_hint
                return str(PROFILE_DIRS[profile_hint] / "market-close" / f"{date_str}-integrated.md"), profile_hint

            if week_match:
                week_str = week_match.group(1)
                cand = PROFILE_DIRS[profile_hint] / "weekly-deep-dive"
                for f in cand.glob(f"*-{week_str}*.md"):
                    if "challenge" not in f.name.lower():
                        return str(f), profile_hint
                return str(cand / f"2026-{week_str}-summary.md"), profile_hint

    # ── Pattern 4: Source hint in challenge filename ──
    for i, part in enumerate(challenge_path.parts):
        if part == "adhoc" and i + 2 < len(challenge_path.parts):
            ticker = challenge_path.parts[i + 2] if challenge_path.parts[i + 1] == "deep-dive" else None
            if ticker:
                for prof in ["alice", "eliza", "renee"]:
                    cand = PROFILE_DIRS[prof] / "adhoc" / "deep-dive" / ticker
                    if cand.exists():
                        for f in sorted(cand.glob("*.md")):
                            if "challenge" not in f.name.lower() and "revised" not in f.name.lower():
                                return str(f), prof

    # ── Pattern 5: Challenge filename gives clue ──
    fname = challenge_path.name
    week_match = re.match(r'(20\d\d-W\d\d)', fname)
    if week_match:
        week = week_match.group(1)
        for prof in ["alice", "renee", "eliza"]:
            for sub in ["self-review", "weekly-deep-dive"]:
                cand = PROFILE_DIRS[prof] / sub
                for f in cand.glob(f"{week}*integrated*.md"):
                    return str(f), prof
                for f in cand.glob(f"{week}*summary*.md"):
                    if "challenge" not in f.name.lower():
                        return str(f), prof

    date_match = re.match(r'(20\d\d-\d\d-\d\d)', fname)
    if date_match:
        date = date_match.group(1)
        challenge_subdir = challenge_path.parent.name if challenge_path.parent.name not in ("challenges", "zoe") else None
        search_subs = ["market-close", "daily-trend-momentum", "daily-social",
                        "daily-financial-data", "macro-daily"]
        if challenge_subdir and challenge_subdir not in search_subs:
            search_subs.insert(0, challenge_subdir)
        search_patterns = [
            f"{date}*integrated*.md",
            f"{date}*summary*.md",
            f"{date}*report*.md",
            f"{date}*market-close*.md",
            f"{date}*macro*.md",
            f"{date}*-summary*.md",
            f"{date}*-report*.md",
        ]
        for prof in ["alice", "renee", "eliza"]:
            for sub in search_subs:
                cand = PROFILE_DIRS[prof] / sub
                if not cand.exists():
                    continue
                for pat in search_patterns:
                    for f in cand.glob(pat):
                        if "challenge" not in f.name.lower() and "revised" not in f.name.lower():
                            return str(f), prof

    return None, None


# ── Revision detection ────────────────────────────

INBOX_DIR = Path.home() / "workspace" / "reports" / "inbox"

CATEGORY_ALIASES = {
    "daily-trend-momentum": ("trend-momentum", "weekly-trend-momentum"),
    "trend-momentum": ("daily-trend-momentum", "weekly-trend-momentum"),
    "daily-social": ("market-close",),
    "market-close": ("daily-social",),
}


def _date_or_week_prefix(stem: str) -> str | None:
    m = re.match(r"(20\d\d-\d\d-\d\d)", stem)
    if m:
        return m.group(1)
    m = re.match(r"(20\d\d-W\d\d)", stem)
    if m:
        return m.group(1)
    return None


def _challenge_category(path: Path) -> str:
    """Canonical folder for a challenge (treat zoe/challenges/<cat>/ as <cat>)."""
    parts = path.parts
    if "challenges" in parts:
        i = parts.index("challenges")
        if i + 1 < len(parts) - 1:
            return parts[i + 1]
    return path.parent.name


def _dedupe_challenges(challenge_files: list[tuple[Path, datetime]]) -> list[tuple[Path, datetime]]:
    """Keep one file per (category, name). Prefer the non-challenges/ copy."""
    best: dict[tuple[str, str], tuple[Path, datetime]] = {}
    for f, mtime in challenge_files:
        key = (_challenge_category(f), f.name.lower())
        prev = best.get(key)
        if prev is None:
            best[key] = (f, mtime)
            continue
        prev_dup = "challenges" in prev[0].parts
        cur_dup = "challenges" in f.parts
        if prev_dup and not cur_dup:
            best[key] = (f, mtime)
    return list(best.values())


def _revision_search_dirs(target: Path) -> list[Path]:
    category = target.parent.name
    dirs: list[Path] = []
    if target.parent.is_dir():
        dirs.append(target.parent)
    cats = (category,) + CATEGORY_ALIASES.get(category, ())
    for cat in cats:
        for prof in ("alice", "renee", "eliza"):
            d = PROFILE_DIRS[prof] / cat
            if d.is_dir() and d not in dirs:
                dirs.append(d)
        inbox = INBOX_DIR / cat
        if inbox.is_dir() and inbox not in dirs:
            dirs.append(inbox)
    return dirs


def _find_revision(target_path: str) -> str | None:
    """Find a same-date revision. Alice often revises next to her copy, not Renee's."""
    target = Path(target_path)
    prefix = _date_or_week_prefix(target.stem)
    candidates: list[Path] = []

    def consider(f: Path) -> None:
        if f == target or not f.is_file():
            return
        name = f.name.lower()
        if "challenge" in name:
            return
        if "revised" not in name and "revision" not in name:
            return
        if prefix and prefix.lower() not in name:
            return
        candidates.append(f)

    for d in _revision_search_dirs(target):
        for f in d.glob("*.md"):
            consider(f)

    if not candidates:
        return None

    def rank(f: Path) -> tuple[int, float]:
        score = 0
        if "inbox" in f.parts:
            score += 2
        if "alice" in f.parts:
            score += 1
        return (score, f.stat().st_mtime)

    return str(max(candidates, key=rank))


# ── Main scan function ────────────────────────────

def scan_challenges(days_back: int = 2) -> list[dict]:
    """Scan challenge files and track revision status.
    
    Default window: current day + T-1 (~48h). Older challenges are archived
    and not scanned (per user directive 2026-07-24).
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)
    results = []

    # Collect challenge files
    challenge_files = []
    for f in ZOE_SHARED_DIR.rglob("*.md"):
        if not _is_challenge_file(f):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime < cutoff:
            continue
        challenge_files.append((f, mtime))

    challenge_files = _dedupe_challenges(challenge_files)

    for f, challenge_mtime in sorted(challenge_files, key=lambda x: x[1], reverse=True):
        if f.stat().st_size == 0:
            continue

        target_path, target_profile = _extract_target(f)

        # ── Parse challenge items ──
        challenge_items = parse_challenge_items(f)
        item_count = {
            "Blockers": sum(1 for i in challenge_items if i["severity"] == "Blocker"),
            "Major": sum(1 for i in challenge_items if i["severity"] == "Major"),
            "Minor": sum(1 for i in challenge_items if i["severity"] == "Minor"),
            "total": len(challenge_items),
        }

        result = {
            "challenge_file": str(f),
            "challenge_date": challenge_mtime.strftime("%Y-%m-%d"),
            "target_report": target_path or "unknown",
            "target_profile": target_profile or "unknown",
            "revision_found": False,
            "revision_file": None,
            "hours_since_challenge": round(
                (now - challenge_mtime).total_seconds() / 3600, 1
            ),
            "status": "unknown",
            # v3 item-level fields
            "item_count": item_count,
            "item_resolution": None,  # filled if revision found
        }

        if not target_path:
            results.append(result)
            continue

        target = Path(target_path)
        if not target.exists():
            result["status"] = "orphaned"
            results.append(result)
            continue

        # Check for revision
        revision_path = _find_revision(target_path)
        rev_mtime = None
        if revision_path:
            rev = Path(revision_path)
            rev_mtime = datetime.fromtimestamp(rev.stat().st_mtime, tz=timezone.utc)
            prefix = _date_or_week_prefix(Path(target_path).stem)
            same_period = bool(prefix and prefix.lower() in rev.name.lower())
            if rev_mtime > challenge_mtime or same_period:
                result["revision_found"] = True
                result["revision_file"] = revision_path

                # ── v3: Parse item-level resolution from revision ──
                response = parse_revision_response(rev)
                if response and challenge_items:
                    xref = cross_reference_items(challenge_items, response)
                    result["item_resolution"] = xref
                    # Override status based on item count
                    if xref["missing"] > 0:
                        result["status"] = "partial"
                    elif xref["not_addressed"] > 0:
                        result["status"] = "partial"
                    elif xref["partial"] > 0:
                        result["status"] = "partial"
                    elif xref["resolved"] == xref["total"]:
                        result["status"] = "resolved"
                    else:
                        result["status"] = "partial"
                else:
                    # No item-level data → fall back to file-level
                    result["status"] = "resolved"
                results.append(result)
                continue

        # Check target itself modified after challenge (in-place revision)
        target_mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
        if target_mtime > challenge_mtime:
            result["revision_found"] = True
            result["revision_file"] = target_path

            # Try parsing in-place revision
            response = parse_revision_response(target)
            if response and challenge_items:
                xref = cross_reference_items(challenge_items, response)
                result["item_resolution"] = xref
                if xref["missing"] > 0 or xref["not_addressed"] > 0 or xref["partial"] > 0:
                    result["status"] = "partial"
                elif xref["resolved"] == xref["total"]:
                    result["status"] = "resolved"
                else:
                    result["status"] = "partial"
            else:
                result["status"] = "resolved"
            results.append(result)
            continue

        # No revision
        hours = result["hours_since_challenge"]
        result["status"] = "stale" if hours > STALE_HOURS else "unresolved"
        results.append(result)

    return results


def format_report(results: list[dict], show_all: bool = False, show_items: bool = False) -> str:
    """Format tracker results for Telegram delivery."""
    now = datetime.now(timezone.utc)
    resolved = [r for r in results if r.get("status") in ("resolved", "partial")]
    unresolved = [r for r in results if r.get("status") in ("unresolved", "stale")]
    orphaned = [r for r in results if r.get("status") == "orphaned"]
    unknown = [r for r in results if r.get("status") == "unknown"]

    status_icon = {
        "resolved": "✅", "partial": "🟡", "unresolved": "🟡",
        "stale": "🔴", "orphaned": "💀", "unknown": "❓",
    }

    # Count item-level stats across all results that have them
    total_items = sum(r.get("item_count", {}).get("total", 0) for r in results)
    resolved_items = 0
    partial_items = 0
    missing_items = 0
    for r in results:
        xr = r.get("item_resolution")
        if xr:
            resolved_items += xr.get("resolved", 0)
            partial_items += xr.get("partial", 0) + xr.get("not_addressed", 0)
            missing_items += xr.get("missing", 0)

    lines = [
        f"📋 Zoe Challenge → Revision Tracker",
        f"🕐 {now.strftime('%Y-%m-%d %H:%M UTC')} | Scan: {len(results)} challenges",
        f"  ✅ Fully resolved: {len(resolved)}",
        f"  🟡 Resolved (w/ items open): {len([r for r in results if r.get('status')=='partial'])}",
        f"  🟡 Unresolved (<{STALE_HOURS}h): {len([r for r in unresolved if r['status']=='unresolved'])}",
        f"  🔴 Stale (>{STALE_HOURS}h): {len([r for r in unresolved if r['status']=='stale'])}",
    ]
    if orphaned:
        lines.append(f"  💀 Orphaned (target missing): {len(orphaned)}")
    if unknown:
        lines.append(f"  ❓ Unknown target: {len(unknown)}")
    if total_items > 0 and resolved_items + partial_items + missing_items > 0:
        lines.append(f"  📊 Item-level: {resolved_items}✅ / {partial_items}🟡 / {missing_items}❌ ({total_items} total)")
    lines.append("")

    if unresolved:
        lines.append("━━━ ⚠️ UNRESOLVED (no revision found) ━━━")
        for r in unresolved:
            icon = status_icon.get(r["status"], "?")
            tgt_name = Path(r["target_report"]).name if r["target_report"] != "unknown" else "?"
            lines.append(f"  {icon} {Path(r['challenge_file']).name}")
            lines.append(f"     → {r['target_profile']}/{tgt_name}")
            lines.append(f"     → {r['hours_since_challenge']:.0f}h since challenge")
            if r.get("item_count", {}).get("total", 0):
                ic = r["item_count"]
                lines.append(f"     → Items: {ic.get('Blockers', 0)}B / {ic.get('Major', 0)}M / {ic.get('Minor', 0)}m")
        lines.append("")

    if orphaned:
        lines.append("━━━ 💀 ORPHANED (target missing) ━━━")
        for r in orphaned:
            lines.append(f"  💀 {Path(r['challenge_file']).name}")
            lines.append(f"     → Target: {r['target_report']}")
        lines.append("")

    # Show partial resolutions (revision exists but some items open)
    partial_resolved = [r for r in results if r.get("status") == "partial"]
    if partial_resolved:
        lines.append("━━━ 🟡 REVISED (w/ open items) ━━━")
        for r in partial_resolved:
            xr = r.get("item_resolution", {})
            items_line = ""
            if xr and xr.get("items"):
                item_parts = []
                for it in xr["items"]:
                    st = it["status"]
                    if st == "resolved":
                        item_parts.append(f"✅{it['item_id']}")
                    elif st == "partial":
                        item_parts.append(f"🟡{it['item_id']}")
                    elif st == "missing":
                        item_parts.append(f"❌{it['item_id']}")
                    elif st == "not_addressed":
                        item_parts.append(f"❌{it['item_id']}")
                    else:
                        item_parts.append(f"⏳{it['item_id']}")
                items_line = " | " + " ".join(item_parts)

            rev_name = Path(r["revision_file"]).name if r.get("revision_file") else "?"
            lines.append(f"  🟡 {Path(r['challenge_file']).name}{items_line}")
            lines.append(f"     → Revision: {rev_name}")
            if show_items and xr and xr.get("items"):
                for it in xr["items"]:
                    if it["status"] != "resolved":
                        lines.append(f"     {it['status_emoji']} {it['item_id']}: {it['title'][:60]}")
                        if it.get("resolution"):
                            lines.append(f"       Fix: {it['resolution'][:80]}")
        lines.append("")

    if show_all and resolved:
        lines.append("━━━ ✅ FULLY RESOLVED ━━━")
        for r in resolved:
            if r.get("status") == "resolved":  # only fully, not partial
                rev_name = Path(r["revision_file"]).name if r.get("revision_file") else "in-place"
                lines.append(f"  ✅ {Path(r['challenge_file']).name} → {rev_name}")
        lines.append("")

    if not results:
        lines.append("(No challenges found in scan range)")

    return "\n".join(lines)


# ── Persistent history DB ──────────────────────────────────
PERSISTENCE_DB = Path.home() / ".hermes" / "shared" / "reports" / "zoe" / "tracker" / "issue-history.json"


def load_issue_history() -> dict:
    """Load persistent issue history JSON."""
    if PERSISTENCE_DB.exists():
        try:
            with open(PERSISTENCE_DB) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"_meta": {"version": 2}, "issues": []}


def save_issue_history(history: dict):
    """Save persistent issue history JSON."""
    PERSISTENCE_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(PERSISTENCE_DB, "w") as f:
        json.dump(history, f, indent=2, default=str)


def cross_reference_with_history(results: list[dict], history: dict) -> list[dict]:
    """Cross-reference scan results with persistent history.
    
    v3: Also tracks per-item recurrence by item_id within each challenge.
    """
    issues = {i["challenge_file"]: i for i in history.get("issues", [])}
    now = datetime.now(timezone.utc).isoformat()

    for r in results:
        key = r.get("challenge_file", "")
        if not key:
            continue
        existing = issues.get(key)
        if existing:
            r["recurrence_count"] = existing.get("recurrence_count", 1)
            r["first_seen"] = existing.get("first_seen", now)
            existing["last_seen"] = now
            existing["status"] = r.get("status", "unknown")
            if r.get("status") in ("resolved", "partial"):
                existing["resolved_at"] = existing.get("resolved_at") or now
        else:
            r["recurrence_count"] = 0
            r["first_seen"] = now
            issues[key] = {
                "challenge_file": key,
                "first_seen": now,
                "last_seen": now,
                "status": r.get("status", "unknown"),
                "target_profile": r.get("target_profile", "?"),
                "challenge_name": Path(key).name,
            }

    history["issues"] = list(issues.values())
    history["_meta"]["last_scan"] = now
    save_issue_history(history)
    return results


def annotate_with_recurrence(report: str, results: list[dict]) -> str:
    """Add recurrence summary section to the report output."""
    recurring = [r for r in results if r.get("recurrence_count", 0) > 0]
    if not recurring:
        return report

    lines = report.split("\n")
    lines.append("")
    lines.append("━━━ 📊 RECURRENCE HISTORY ━━━")
    for r in recurring:
        name = Path(r["challenge_file"]).name
        count = r["recurrence_count"]
        first = r.get("first_seen", "?")[:10]
        icon = "🔴" if count >= 3 else "🟡"
        lines.append(f"  {icon} {name} — seen {count+1}x since {first}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Zoe challenge→revision tracker (item-level)")
    parser.add_argument("--days", type=int, default=14, help="Days back to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--all", action="store_true", help="Show resolved challenges too")
    parser.add_argument("--items", action="store_true", help="Show item-level detail in unresolved")
    parser.add_argument("--template", type=str, default=None,
                        help="Path to challenge file: generate response template")
    parser.add_argument("--format", action="store_true",
                        help="Show the standard response format documentation")
    args = parser.parse_args()

    # ── Format documentation mode ──
    if args.format:
        print("""## Zoe Challenge Response Tracker 

， item resolution status：

| Item | Severity | Brief | Resolution | Status |
|:----:|:--------:|:------|:-----------|:------:|
| B1   | 🔴 Blocker | 2s10s spread error | Switched to FRED T10Y2Y | ✅ |
| M1   | 🟡 Major | META §8 inconsistency | Unified to +2.55% | 🟡 |
| m1   | 🔵 Minor | Win rate methodology | Added footnote | ✅ |

Status key: ✅=resolved, 🟡=partial, ❌=not addressed, ⏳=pending
Auto-generate: python3 zoe_tracker.py --template <challenge_file>
Item IDs: B1/B2(Blocker), M1/M2(Major), m1/m2(Minor)
Reference: ~/.hermes/shared/reports/zoe/tracker/RESPONSE_FORMAT.md""")
        return

    # ── Template generation mode ──
    if args.template:
        template_path = Path(args.template)
        if not template_path.exists():
            print(f"Error: file not found: {args.template}", file=sys.stderr)
            sys.exit(1)
        print(generate_response_template(template_path))
        return

    # ── Scan mode ──
    results = scan_challenges(days_back=args.days)

    # Persistent history cross-reference
    history = load_issue_history()
    results = cross_reference_with_history(results, history)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        report = format_report(results, show_all=args.all, show_items=args.items)
        report = annotate_with_recurrence(report, results)
        print(report)

    unresolved = [r for r in results if r.get("status") in ("unresolved", "stale", "orphaned")]
    sys.exit(1 if unresolved else 0)


if __name__ == "__main__":
    main()
