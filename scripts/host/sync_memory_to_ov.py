#!/usr/bin/env python3
"""
Sync each Hermes profile's local MEMORY.md into OpenViking user-memory namespace.

Per profile, the whole MEMORY.md is stored as ONE fixed-URI memory entry
(mem_LOCAL_MEMORY_<profile>.md) under patterns/. Idempotent: forget-then-create.

Usage:
    python3 sync_memory_to_ov.py
    python3 sync_memory_to_ov.py --dry-run
    python3 sync_memory_to_ov.py --no-alert
    python3 sync_memory_to_ov.py --quiet
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VIKING_HOST = os.environ.get("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933").rstrip("/")
VIKING_KEY = os.environ.get("OPENVIKING_API_KEY") or os.environ.get("VIKING_KEY") or ""
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HERMES_CLI = os.environ.get("HERMES_CLI", str(HERMES_HOME / "hermes-agent" / "venv" / "bin" / "hermes"))

# sarah = default profile (main Hermes memories/)
PROFILES = {
    "sarah": HERMES_HOME / "memories" / "MEMORY.md",
    "alice": HERMES_HOME / "profiles" / "alice" / "memories" / "MEMORY.md",
    "eliza": HERMES_HOME / "profiles" / "eliza" / "memories" / "MEMORY.md",
    "renee": HERMES_HOME / "profiles" / "renee" / "memories" / "MEMORY.md",
    "zoe": HERMES_HOME / "profiles" / "zoe" / "memories" / "MEMORY.md",
}


def _headers(user: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-API-Key": VIKING_KEY,
        "X-OpenViking-Account": "default",
        "X-OpenViking-User": user,
        "X-OpenViking-Actor-Peer": "hermes",
    }


def _alert(msg: str) -> None:
    if "--no-alert" in sys.argv:
        return
    try:
        subprocess.run(
            [HERMES_CLI, "send", "--to", "telegram", msg],
            timeout=30,
            capture_output=True,
        )
    except Exception:
        pass


def _health_ok() -> bool:
    try:
        req = urllib.request.Request(
            f"{VIKING_HOST}/health", headers=_headers("sarah"), method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def _forget(uri: str, user: str) -> None:
    url = f"{VIKING_HOST}/api/v1/fs?uri={urllib.parse.quote(uri, safe='')}&recursive=False"
    req = urllib.request.Request(url, headers=_headers(user), method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception:
        pass


def _remember(uri: str, content: str, user: str) -> str:
    url = f"{VIKING_HOST}/api/v1/content/write"
    body = {"uri": uri, "content": content, "mode": "create"}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=_headers(user), method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get("status", "ok")
    except urllib.error.HTTPError as e:
        return f"error:{e.code}"
    except Exception as e:
        return f"error:{e}"


def _read_back(uri: str, user: str) -> bool:
    parent = uri.rsplit("/", 1)[0]
    url = f"{VIKING_HOST}/api/v1/fs/ls?uri={urllib.parse.quote(parent)}"
    req = urllib.request.Request(url, headers=_headers(user), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "ok":
                for entry in data.get("result", []):
                    if entry.get("uri") == uri:
                        return True
    except Exception as e:
        print(f"  Read-back failed for {uri}: {e}", file=sys.stderr)
    return False


def main() -> None:
    dry = "--dry-run" in sys.argv
    quiet = "--quiet" in sys.argv

    if not VIKING_KEY:
        print(
            "sync_memory_to_ov: set OPENVIKING_API_KEY or VIKING_KEY "
            "(e.g. ~/.hermes/.env or cron wrapper)",
            file=sys.stderr,
        )
        sys.exit(2)

    def _out(msg: str) -> None:
        if not quiet:
            print(msg)

    def _fail(msg: str) -> None:
        print(msg, file=sys.stdout if quiet else sys.stderr)

    if not dry and not _health_ok():
        msg = f"sync_memory_to_ov FAILED: OpenViking unreachable at {VIKING_HOST}"
        _fail(msg)
        _alert(msg)
        sys.exit(1)

    failures = []
    for profile, path in PROFILES.items():
        path_s = str(path)
        if not path.exists():
            _out(f"skip {profile}: no MEMORY.md at {path_s}")
            continue
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            _out(f"skip {profile}: empty MEMORY.md")
            continue
        uri = (
            f"viking://user/{profile}/peers/hermes/memories/patterns/"
            f"mem_LOCAL_MEMORY_{profile}.md"
        )
        if dry:
            print(f"[dry-run] would sync {profile} ({len(content)}b) -> {uri}")
            continue
        _forget(uri, profile)
        status = _remember(uri, content, profile)
        if isinstance(status, str) and status.startswith("error"):
            failures.append(f"{profile}: {status}")
            _fail(f"FAIL {profile} -> {uri} [{status}]")
        elif _read_back(uri, profile):
            _out(f"ok {profile} -> {uri} [{status}] verified")
        else:
            _out(f"ok {profile} -> {uri} [{status}] read-back not found")
            failures.append(f"{profile}: read-back not found")

    if failures:
        msg = "sync_memory_to_ov partial failure:\n" + "\n".join(failures)
        _fail(msg)
        _alert(msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
