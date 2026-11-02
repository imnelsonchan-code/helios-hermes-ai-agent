"""Helpers for tests running against the scrubbed public repo snapshot."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def host_only_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def skip_unless_host_file(path: Path, reason: str):
    import unittest

    return unittest.skipUnless(path.is_file(), reason)
