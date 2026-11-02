#!/usr/bin/env python3
"""Deprecated: do not create extra Sunday 11:00 / 11:20 emily/christina clocks.

Weekly depth is **one** cron — Sunday 12:00 train `<desk-pack-weekly-job-id>`
(christina -> emily -> T&M). Split clocks were deleted 2026-09-20.

  python3 ~/.hermes/scripts/patch_desk_pack_weekly_train.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from desk_pack_weekly_prompts import (  # type: ignore
        DELETED_COMMODITIES_ID,
        DELETED_RATES_ID,
        TRAIN_ID,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from desk_pack_weekly_prompts import (  # type: ignore
        DELETED_COMMODITIES_ID,
        DELETED_RATES_ID,
        TRAIN_ID,
    )


def main() -> int:
    print(
        "DEPRECATED: weekly emily/christina are cars on "
        f"{TRAIN_ID} @ Sun 12:00 (single train). "
        f"Do not hermes cron create 11:00/11:20 jobs "
        f"({DELETED_COMMODITIES_ID} / {DELETED_RATES_ID} deleted). "
        "Run patch_desk_pack_weekly_train.py instead."
    )
    print(
        "RESULT_JSON="
        + json.dumps(
            {
                "deprecated": True,
                "train": TRAIN_ID,
                "deleted_commodities": DELETED_COMMODITIES_ID,
                "deleted_rates": DELETED_RATES_ID,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
