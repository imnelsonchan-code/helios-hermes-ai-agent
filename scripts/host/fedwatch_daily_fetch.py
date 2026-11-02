#!/usr/bin/env python3
"""fedwatch_daily_fetch.py — Daily CME FedWatch probability auto-fetch (W34 P1, t_3e2a22f1).

REPO MIRROR (path-regression only): live host owns cron job <fedwatch-daily-job-id>.
Do NOT invent an alternate BASE — keep alice/fedwatch as SSOT.
Canonical host path: ~/.hermes/scripts/fedwatch_daily_fetch.py

Runs fed_probability_fetch.py --json and saves the canonical daily snapshot so
daily report workers (Alice macro Step 1a) and Zoe have a deterministic path:
  ~/.hermes/shared/reports/alice/fedwatch/YYYY-MM-DD-fedwatch.json
  ~/.hermes/shared/reports/alice/fedwatch/latest.json  (overwrite)

Watchdog semantics (no_agent cron):
  - success: print ONE short summary line (saved to cron output; local delivery)
  - live-primary failure but fallback snapshot used: print WARNING line
  - hard failure (fetch subprocess error / bad JSON): print ERROR line, exit 1

Exit codes: 0 ok / 1 failure.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
BASE = os.path.join(_HERMES_HOME, "shared/reports/alice/fedwatch")
SCRIPT = os.path.join(_HERMES_HOME, "shared/reports/alice/scripts/fed_probability_fetch.py")
ZQ_SCRIPT = os.path.join(_HERMES_HOME, "shared/reports/alice/scripts/fed_backup_zq.py")
FETCH_TIMEOUT = 150
ZQ_TIMEOUT = 75


def run_zq_backup(reference_json: str) -> tuple[dict | None, str | None]:
    """Run fed_backup_zq.py against the canonical snapshot for defaults.

    Backup is optional: returns (data, None) on success,
    (None, reason) when it fails/skips — never raises.
    """
    try:
        proc = subprocess.run(
            [sys.executable, ZQ_SCRIPT, "--json", "--fedwatch-json", reference_json],
            capture_output=True, text=True, timeout=ZQ_TIMEOUT,
        )
    except Exception as e:
        return None, f"subprocess error: {e}"
    if proc.returncode not in (0, 1, 2):  # 3 = hard failure
        return None, f"exit {proc.returncode}: {proc.stderr.strip()[:300]}"
    try:
        out = json.loads(proc.stdout)
    except Exception:
        return None, "bad JSON output"
    return out, None


def _at_bound(p) -> bool:
    """True when a probability sits on the 0% or 100% rail."""
    try:
        if isinstance(p, bool):
            return False
        n = float(p)
    except (TypeError, ValueError):
        return False
    return n <= 0.5 or n >= 99.5


def _as_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _primary_and_sentiment(data: dict) -> tuple[dict, dict]:
    """Live cron JSON uses layers.a_primary / layers.c_sentiment.

    The repo mirror's older shape stores the same primary block at
    data["primary"] when ``layers`` is absent. b_backup_zq is never a source.
    """
    layers = data.get("layers")
    if isinstance(layers, dict):
        primary = layers.get("a_primary")
        sentiment = layers.get("c_sentiment")
        return (
            primary if isinstance(primary, dict) else {},
            sentiment if isinstance(sentiment, dict) else {},
        )
    primary = data.get("primary")
    sentiment = data.get("c_sentiment")
    return (
        primary if isinstance(primary, dict) else {},
        sentiment if isinstance(sentiment, dict) else {},
    )


def _a_pct(primary: dict):
    summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else {}
    if "oct_hike_pct" in summary:
        return _as_number(summary.get("oct_hike_pct"))
    meetings = primary.get("meetings")
    if isinstance(meetings, list) and meetings and isinstance(meetings[0], dict):
        return _as_number(meetings[0].get("prob_move_pct"))
    return None


def _range_ok(data: dict, primary: dict) -> bool:
    cal = None
    nested = primary.get("forward_backward_calibration")
    if isinstance(nested, dict) and "range_pct" in nested:
        cal = nested.get("range_pct")
    else:
        top = data.get("forward_backward_calibration")
        if isinstance(top, dict):
            cal = top.get("range_pct")
    if not isinstance(cal, (list, tuple)) or len(cal) != 2:
        return False
    lo = _as_number(cal[0])
    hi = _as_number(cal[1])
    if lo is None or hi is None:
        return False
    return 0 <= lo <= 100 and 0 <= hi <= 100


def _sentiment_fresh(data: dict, sentiment: dict) -> bool:
    stamp = sentiment.get("freshness_stamp")
    if isinstance(stamp, dict) and stamp.get("status") == "fresh":
        return True
    freshness = data.get("freshness")
    if not isinstance(freshness, dict):
        return False
    layers = freshness.get("layers")
    if not isinstance(layers, dict):
        return False
    marker = layers.get("c_sentiment")
    if marker == "fresh":
        return True
    if isinstance(marker, dict) and marker.get("status") == "fresh":
        return True
    return False


def _sentiment_ok(data: dict, sentiment: dict) -> bool:
    if not _sentiment_fresh(data, sentiment):
        return False
    summary = sentiment.get("summary") if isinstance(sentiment.get("summary"), dict) else {}
    oct_hike = _as_number(summary.get("oct_hike_pct"))
    if oct_hike is None or _at_bound(oct_hike):
        return False
    markets = sentiment.get("markets")
    if not isinstance(markets, list):
        return False
    for market in markets:
        if not isinstance(market, dict):
            continue
        url = market.get("url")
        question = market.get("question")
        if isinstance(url, str) and url.strip() and isinstance(question, str) and question.strip():
            return True
    return False


def stamp_cross_check(data: dict) -> dict:
    """Stamp citation before the daily/latest JSON write.

    A miss still returns the payload so latest.json is overwritten. ZQ backup
    (b_backup_zq) is not a second source and cannot clear a miss.
    """
    if not isinstance(data, dict):
        return data
    primary, sentiment = _primary_and_sentiment(data)
    a_pct = _a_pct(primary)
    # A usable primary (not 0/100, calibration inside 0–100) stays citable
    # when sentiment is stale. Only a bound or unusable ZQ print blanks the section.
    zq_unusable = a_pct is None or _at_bound(a_pct) or not _range_ok(data, primary)
    if zq_unusable:
        data["cross_check"] = {
            "citation": "miss",
            "reason": "degenerate_zq_sole_source",
        }
        freshness = data.get("freshness")
        if not isinstance(freshness, dict):
            freshness = {}
            data["freshness"] = freshness
        freshness["citation"] = "miss"
    elif not _sentiment_ok(data, sentiment):
        data["cross_check"] = {
            "citation": "primary_only",
            "reason": "sentiment_miss",
        }
    else:
        data["cross_check"] = {"citation": "ok"}
    return data


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--json"],
            capture_output=True, text=True, timeout=FETCH_TIMEOUT,
        )
    except Exception as e:
        print(f"[fedwatch-cron] ERROR: fetch subprocess failed: {e}")
        return 1
    if proc.returncode != 0:
        print(f"[fedwatch-cron] ERROR: fed_probability_fetch.py exited "
              f"{proc.returncode}\n{proc.stderr[:800]}")
        return 1
    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        print(f"[fedwatch-cron] ERROR: bad JSON from fetch: {e}\n{proc.stdout[:500]}")
        return 1

    daily_path = os.path.join(BASE, f"{today}-fedwatch.json")
    latest_path = os.path.join(BASE, "latest.json")
    # Reference file for the ZQ backup defaults (same primary schedule/effr)
    ref_path = os.path.join(BASE, ".ref_tmp.json")
    try:
        with open(ref_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        backup, berr = run_zq_backup(ref_path)
        if backup:
            data["backup_institutional"] = backup
            zb = backup.get("calc") or {}
            print(f"[fedwatch-cron] ZQ-BACKUP {backup.get('status')} "
                  f"asof={backup.get('market_asof')} "
                  f"meeting={backup.get('meeting')} "
                  f"prob={zb.get('probability')}% range={zb.get('range_pct')} "
                  f"[{backup.get('source', '')[:40]}…]")
        else:
            print(f"[fedwatch-cron] ZQ-BACKUP skip ({berr})")
    except Exception as e:
        print(f"[fedwatch-cron] ZQ-BACKUP skip (save/ref error: {e})")
    finally:
        if os.path.exists(ref_path):
            try:
                os.remove(ref_path)
            except OSError:
                pass
    data = stamp_cross_check(data)
    try:
        with open(daily_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[fedwatch-cron] ERROR: save failed: {e}")
        return 1

    p = data.get("primary") or {}
    s = p.get("summary") or {}
    as_of = p.get("as_of") or "?"
    fr = data.get("freshness") or {}
    fstatus = fr.get("status") or ("stale_fallback" if data.get("fallback_used") else "fresh")
    fage = fr.get("as_of_age_days")
    # Back-compat: older JSON may lack freshness — infer minimal staleness.
    stale = fstatus != "fresh" or bool(data.get("fallback_used"))
    if data.get("fallback_used"):
        print(f"[fedwatch-cron] WARNING: fallback snapshot used (no live "
              f"primary) as_of={as_of} — REFRESH REQUIRED before citing")
        if stale:
            print(f"[fedwatch-cron] FRESHNESS: {fstatus} as_of={as_of} "
                  f"age={fage if fage is not None else '?'}d — report row MUST "
                  f"carry 「institutional stale, sentiment-only」")
        return 0
    if stale:
        print(f"[fedwatch-cron] WARNING: primary institutional source stale "
              f"as_of={as_of} age={fage if fage is not None else '?'}d (>3d) — "
              f"report row MUST carry 「institutional stale, sentiment-only」; "
              f"do not silently cite {as_of} values")
        return 0
    print(f"[fedwatch-cron] OK {today} as_of={as_of} "
          f"sep_hike={s.get('sep_hike_pct')}% "
          f"oct_hike={s.get('oct_hike_pct')}% "
          f"year_end_hike={s.get('year_end_2026_hike_pct')}% "
          f"saved={daily_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
