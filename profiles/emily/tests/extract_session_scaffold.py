#!/usr/bin/env python3
"""Extract Daily/Weekly blank scaffold markdown from commodity-session-report SKILL."""
from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_session_scaffold.py SKILL.md Daily|Weekly", file=sys.stderr)
        return 2
    path, label = sys.argv[1], sys.argv[2]
    text = open(path, encoding="utf-8").read()
    marker = f"## Blank report template — {label} scaffold"
    idx = text.find(marker)
    if idx < 0:
        print(f"scaffold heading not found: {marker}", file=sys.stderr)
        return 2
    rest = text[idx:]
    m = re.search(r"```markdown\n(.*?)```", rest, re.S)
    if not m:
        print(f"no ```markdown fence after {marker}", file=sys.stderr)
        return 2
    sys.stdout.write(m.group(1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
