#!/usr/bin/env python3
"""Mercury Decide ENFORCE sidecar — OpenRouter Decisions API.

Calls ``inception/mercury-decide:free`` via POST /api/alpha/decisions.
Writes ledger JSON + Telegram (Yes/No + scores). No Hermes chat pin.
No external chat-pin path. Never writes *-revised.md.

Modes:
  enforce (default) — Sat: spawn ⊆ APPROVE; Zoe: escalate-only stricter;
                      MOA publish: score ≥90 ACCEPT else REWORK.
  off               — kill switch; no API; Sat FAIL-OPEN all High; Zoe keep verdict;
                      MOA FAIL-OPEN ACCEPT.

Infra faults (timeout / HTTP / parse) -> FAIL-OPEN + Telegram.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODEL = "inception/mercury-decide:free"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODE = "enforce"
VERDICT_RANK = {"PASS": 0, "CONDITIONAL": 1, "REJECT": 2}
MOA_PUBLISH_THRESHOLD = 90
MOA_WEIGHT_COMPLETENESS = 0.45
MOA_WEIGHT_COHERENCE = 0.35
MOA_WEIGHT_SOURCES = 0.20


def hermes_home() -> Path:
    """Hermes root (``~/.hermes``).

    Profile workers may export ``HERMES_HOME=~/.hermes/profiles/<name>``; ledgers,
    spawn stamps and ``.env`` lookup must still use the shared root, so a
    ``.../profiles/<name>`` override is normalised to its grandparent.
    """
    override = os.environ.get("HERMES_HOME")
    if override:
        p = Path(override).expanduser()
        if p.parent.name == "profiles":
            return p.parent.parent
        return p
    return Path(os.path.expanduser("~/.hermes"))


def resolve_path(raw: str) -> Path:
    """Expand ``~``; bare relative paths (``shared/reports/...``) anchor at hermes_home()."""
    p = Path(raw).expanduser()
    if not p.is_absolute():
        anchored = hermes_home() / p
        if anchored.exists() or not p.exists():
            return anchored
    return p


def ledger_root() -> Path:
    return hermes_home() / "shared" / "reports" / "mercury"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_mode(cli_mode: str | None = None) -> str:
    """Env kill switch wins: MERCURY_DECIDE_MODE=off overrides CLI --mode enforce."""
    env_raw = (os.environ.get("MERCURY_DECIDE_MODE") or "").strip().lower()
    if env_raw == "off":
        return "off"
    if env_raw and env_raw not in ("enforce", "off"):
        print(f"WARN MERCURY_DECIDE_MODE={env_raw!r} invalid; using enforce", file=sys.stderr)
    raw = (cli_mode or env_raw or DEFAULT_MODE).strip().lower()
    if raw in ("off", "enforce"):
        return raw
    print(f"WARN mode={raw!r} invalid; using enforce", file=sys.stderr)
    return DEFAULT_MODE


def _env_file_key(env_path: Path, name: str = "OPENROUTER_API_KEY") -> str:
    """Read one key from a dotenv file (never logged). Handles ``export`` + quotes."""
    if not env_path.is_file():
        return ""
    try:
        text = env_path.read_text(encoding="utf-8")
    except Exception:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        k, _, v = line.partition("=")
        if k.strip() != name:
            continue
        v = v.strip()
        if v[:1] in ("'", '"'):
            q = v[0]
            end = v.find(q, 1)
            v = v[1:end] if end > 0 else v[1:]
        else:
            v = v.split(" #", 1)[0].strip()
        if v:
            return v
    return ""


def openrouter_api_key() -> str:
    """Env first, then Hermes ``.env`` (cron/terminal subprocesses often lack it)."""
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    home = hermes_home()
    candidates = [
        home / ".env",
        Path(os.path.expanduser("~/.hermes/.env")),
    ]
    seen: set[str] = set()
    for env_path in candidates:
        marker = str(env_path)
        if marker in seen:
            continue
        seen.add(marker)
        val = _env_file_key(env_path)
        if val:
            return val
    return ""


def call_decisions(
    *,
    state: Any,
    questions: dict[str, Any],
    timeout: float = 45.0,
    retries: int = 1,
) -> tuple[dict[str, Any] | None, str]:
    """POST Decisions API. Returns (payload_or_None, detail)."""
    key = openrouter_api_key()
    if not key:
        return None, "OPENROUTER_API_KEY unset"
    body = json.dumps(
        {"model": MODEL, "state": state, "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")
    last = "unknown"
    attempts = max(1, retries + 1)
    for _ in range(attempts):
        req = urllib.request.Request(
            DECISIONS_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    last = "response not object"
                    continue
                if data.get("error") and not isinstance(data.get("answers"), dict):
                    last = "response error"
                    continue
                return data, "ok"
        except urllib.error.HTTPError as e:
            last = f"http {e.code}"
            if e.code in (400, 401, 402, 403, 404):
                break  # config/auth faults — retry cannot help
        except Exception as e:
            last = f"{type(e).__name__}: {e}"[:160]
    return None, last


def usable_answers(payload: dict[str, Any] | None, keys: list[str]) -> dict[str, Any] | None:
    """Return answers dict only when it contains at least one expected question key.

    HTTP 200 with empty/foreign ``answers`` is an infra fault (schema drift), not a
    verdict — callers must treat it as DECIDE_UNAVAILABLE so Telegram says FAIL-OPEN.
    """
    if not isinstance(payload, dict):
        return None
    answers = payload.get("answers")
    if not isinstance(answers, dict) or not answers:
        return None
    if not any(k in answers for k in keys):
        return None
    return answers


def _noul_pair(answers: dict[str, Any], key: str) -> dict[str, float | None]:
    node = answers.get(key) if isinstance(answers, dict) else None
    if not isinstance(node, dict):
        return {"yes": None, "no": None}
    noul = node.get("noul")
    try:
        yes = float(noul) if noul is not None else None
    except (TypeError, ValueError):
        yes = None
    no = None if yes is None else max(0.0, min(1.0, 1.0 - yes))
    return {"yes": yes, "no": no}


def _score_val(answers: dict[str, Any], key: str) -> float | None:
    node = answers.get(key) if isinstance(answers, dict) else None
    if not isinstance(node, dict):
        return None
    raw = node.get("score")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _choice_val(answers: dict[str, Any], key: str) -> str | None:
    node = answers.get(key) if isinstance(answers, dict) else None
    if not isinstance(node, dict):
        return None
    choice = node.get("choice")
    return str(choice) if choice is not None else None


def stricter_verdict(a: str, b: str) -> str:
    ra = VERDICT_RANK.get((a or "").upper(), 0)
    rb = VERDICT_RANK.get((b or "").upper(), 0)
    return a if ra >= rb else b


def _as_bool(v: Any) -> bool:
    """JSON from LLM cards may carry "false"/"no" strings; bool("false") is True."""
    if isinstance(v, str):
        return v.strip().lower() not in ("false", "no", "n", "0", "")
    return bool(v)


def load_candidates(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("candidates"), list):
        items = raw["candidates"]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("candidates must be a list or {candidates: [...]}")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        tid = str(item.get("topic_id") or item.get("id") or f"topic-{i + 1}").strip()
        out.append(
            {
                "topic_id": tid,
                "title": str(item.get("title") or tid).strip(),
                "assignee": str(item.get("assignee") or "alice").strip().lower(),
                "priority": str(item.get("priority") or "High").strip(),
                "actionable": _as_bool(item.get("actionable", True)),
                "details": str(item.get("details") or item.get("rationale") or "").strip(),
            }
        )
    return out


def decide_sat_topics(
    candidates: list[dict[str, Any]],
    *,
    mode: str,
    week: str,
) -> dict[str, Any]:
    high: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for c in candidates:
        if not (str(c.get("priority", "")).lower().startswith("high") and c.get("actionable", True)):
            continue
        if c["topic_id"] in seen_ids:  # duplicate slug — one question set, one spawn
            continue
        seen_ids.add(c["topic_id"])
        high.append(c)
    base: dict[str, Any] = {
        "mode": mode,
        "scope": "sat_topics",
        "as_of": _now_iso(),
        "week": week,
        "model": MODEL,
        "status": "OK",
        "items": [],
        "approve_topic_ids": [],
    }
    if mode == "off":
        base["status"] = "OFF"
        base["detail"] = "mode=off kill switch (legacy High spawn)"
        for c in high:
            base["items"].append(
                {
                    "topic_id": c["topic_id"],
                    "type": "new_topic",
                    "decision": "APPROVE",
                    "decision_hint": "APPROVE",
                    "yes_no": [{"id": "spawn", "yes": None, "no": None}],
                    "scores": [],
                    "choice": {"id": "would_verdict", "value": "APPROVE"},
                    "confidence": None,
                    "rationale": "mode=off kill switch — legacy High spawn",
                    "assignee": c["assignee"],
                    "title": c["title"],
                }
            )
            base["approve_topic_ids"].append(c["topic_id"])
        return base

    if not high:
        base["status"] = "OK"
        base["note"] = "no High+actionable candidates"
        return base

    state = {
        "week": week,
        "candidates": [
            {
                "topic_id": c["topic_id"],
                "title": c["title"],
                "assignee": c["assignee"],
                "details": str(c.get("details") or "")[:800],
            }
            for c in high
        ],
    }
    # One batched choice per topic via parallel noul + overall choice keys.
    questions: dict[str, Any] = {}
    qkeys = question_keys(high)
    for c in high:
        tid = qkeys[c["topic_id"]]
        questions[f"spawn_{tid}"] = {
            "type": "noul",
            "instructions": (
                f"Should the desk spawn a kanban card THIS week for topic "
                f"{c['title']!r} (assignee {c['assignee']})? True = high ROI "
                f"and actionable; False = defer or reject."
            ),
            "true": "Spawn now — clear owner, feasible this week",
            "false": "Do not spawn — defer or reject",
        }
        questions[f"roi_{tid}"] = {
            "type": "score",
            "instructions": f"Expected desk ROI for spawning {c['title']!r} this week.",
            "criteria": ["Waste", "Low", "Medium", "High", "Critical"],
        }

    payload, detail = call_decisions(state=state, questions=questions, retries=1)
    answers = usable_answers(payload, list(questions)) if payload is not None else None
    if payload is not None and answers is None:
        payload, detail = None, "response had no usable answers"
    if payload is None or answers is None:
        base["status"] = "DECIDE_UNAVAILABLE"
        base["detail"] = detail
        for c in high:
            base["items"].append(
                {
                    "topic_id": c["topic_id"],
                    "type": "new_topic",
                    "decision": "APPROVE",
                    "decision_hint": "APPROVE",
                    "yes_no": [{"id": "spawn", "yes": None, "no": None}],
                    "scores": [],
                    "choice": {"id": "would_verdict", "value": "APPROVE"},
                    "confidence": None,
                    "rationale": f"FAIL-OPEN ({detail})",
                    "assignee": c["assignee"],
                    "title": c["title"],
                }
            )
            base["approve_topic_ids"].append(c["topic_id"])
        return base

    fail_open_ids: list[str] = []
    for c in high:
        tid = qkeys[c["topic_id"]]
        yn = _noul_pair(answers, f"spawn_{tid}")
        score = _score_val(answers, f"roi_{tid}")
        yes = yn.get("yes")
        if yes is None:
            decision = "APPROVE"
            rationale = "FAIL-OPEN missing noul"
            fail_open_ids.append(c["topic_id"])
        elif yes >= 0.55:
            decision = "APPROVE"
            rationale = "spawn noul >= 0.55"
        elif yes >= 0.35:
            decision = "DEFER"
            rationale = "spawn noul mid — defer"
        else:
            decision = "REJECT"
            rationale = "spawn noul low — reject"
        item = {
            "topic_id": c["topic_id"],
            "type": "new_topic",
            "decision": decision,
            "decision_hint": decision,
            "yes_no": [{"id": "spawn", "yes": yes, "no": yn.get("no")}],
            "scores": [{"id": "roi", "value": score}],
            "choice": {"id": "would_verdict", "value": decision},
            "confidence": None,
            "rationale": rationale,
            "assignee": c["assignee"],
            "title": c["title"],
        }
        base["items"].append(item)
        if decision == "APPROVE":
            base["approve_topic_ids"].append(c["topic_id"])
    if fail_open_ids:
        # Per-topic fail-open must be visible (not a silent APPROVE under status=OK).
        base["status"] = "PARTIAL_FAIL_OPEN"
        base["detail"] = f"missing noul for {len(fail_open_ids)} topic(s): " + ",".join(fail_open_ids)[:200]
        base["fail_open_topic_ids"] = fail_open_ids
    return base


def question_keys(high: list[dict[str, Any]]) -> dict[str, str]:
    """topic_id -> unique API question suffix (sanitised slug, collision-safe)."""
    out: dict[str, str] = {}
    used: set[str] = set()
    for c in high:
        base = re.sub(r"[^a-zA-Z0-9_]+", "_", c["topic_id"])[:40] or "topic"
        key, n = base, 2
        while key in used:
            key = f"{base[:36]}_{n}"
            n += 1
        used.add(key)
        out[c["topic_id"]] = key
    return out


def parse_zoe_verdict(text: str) -> tuple[str, bool]:
    """Return (verdict, parsed). Unparsed defaults to PASS but is flagged for ledger/Telegram."""
    m = re.search(r'"verdict"\s*:\s*"(PASS|CONDITIONAL|REJECT)"', text or "", re.I)
    if m:
        return m.group(1).upper(), True
    m2 = re.search(r"\bverdict\b\s*[:=]\s*\**\s*(PASS|CONDITIONAL|REJECT)\b", text or "", re.I)
    if m2:
        return m2.group(1).upper(), True
    return "PASS", False


def extract_zoe_verdict(text: str) -> str:
    return parse_zoe_verdict(text)[0]


def decide_zoe_challenge(
    artifact_text: str,
    *,
    mode: str,
    profile: str,
    artifact_path: str,
) -> dict[str, Any]:
    zoe_verdict, verdict_parsed = parse_zoe_verdict(artifact_text)
    base: dict[str, Any] = {
        "mode": mode,
        "scope": "zoe_challenge",
        "as_of": _now_iso(),
        "profile": profile,
        "artifact": artifact_path,
        "model": MODEL,
        "status": "OK",
        "zoe_verdict_parsed": verdict_parsed,
        "zoe_verdict": zoe_verdict,
        "decide_verdict": zoe_verdict,
        "final_verdict": zoe_verdict,
        "action": "keep",
        "items": [],
    }
    if mode == "off":
        base["status"] = "OFF"
        base["action"] = "keep"
        base["rationale"] = "mode=off kill switch"
        return base

    state = {
        "profile": profile,
        "zoe_verdict": zoe_verdict,
        "artifact_excerpt": (artifact_text or "")[:12000],
    }
    questions = {
        "publishable": {
            "type": "noul",
            "instructions": (
                "Is this draft safe to treat as publishable after Zoe's gate "
                "(PASS-level), assuming numbers must match packs?"
            ),
            "true": "Publishable / PASS-level",
            "false": "Not publishable",
        },
        "invented_numbers": {
            "type": "noul",
            "instructions": (
                "Does the artifact invent or mislabel pack numbers "
                "(tm_score, valuation_score, ATR%, ADX, Risk%)?"
            ),
            "true": "Invented or mislabeled figures present",
            "false": "No invented figures detected",
        },
        "has_session_summary": {
            "type": "noul",
            "instructions": "Does the draft include a ## Session summary section when required?",
            "true": "Session summary present or not required",
            "false": "Required Session summary missing",
        },
        "invention_risk": {
            "type": "score",
            "instructions": "Risk that quantitative claims are invented.",
            "criteria": ["None", "Low", "Medium", "High", "Severe"],
        },
        "agree_with_zoe": {
            "type": "score",
            "instructions": f"How much do you agree with Zoe verdict {zoe_verdict}?",
            "criteria": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        },
        "would_verdict": {
            "type": "choice",
            "instructions": "Independent IC verdict for this artifact.",
            "criteria": {
                "PASS": "No blocker/major; publishable",
                "CONDITIONAL": "Majors revisable without inventing numbers",
                "REJECT": "Blocker or unsafe majors",
            },
        },
    }
    payload, detail = call_decisions(state=state, questions=questions, retries=1)
    answers = usable_answers(payload, list(questions)) if payload is not None else None
    if payload is not None and answers is None:
        payload, detail = None, "response had no usable answers"
    if payload is None or answers is None:
        base["status"] = "DECIDE_UNAVAILABLE"
        base["detail"] = detail
        base["action"] = "FAIL-OPEN"
        base["rationale"] = f"keep Zoe ({detail})"
        return base

    yn_pub = _noul_pair(answers, "publishable")
    yn_inv = _noul_pair(answers, "invented_numbers")
    yn_sum = _noul_pair(answers, "has_session_summary")
    decide_v = (_choice_val(answers, "would_verdict") or zoe_verdict).upper()
    if decide_v not in VERDICT_RANK:
        decide_v = zoe_verdict
    # Escalate from noul signals.
    if (yn_inv.get("yes") or 0) >= 0.6:
        decide_v = stricter_verdict(decide_v, "REJECT")
    if (yn_sum.get("no") or 0) >= 0.6:
        decide_v = stricter_verdict(decide_v, "REJECT")
    if (yn_pub.get("no") or 0) >= 0.6:
        decide_v = stricter_verdict(decide_v, "CONDITIONAL")

    final = stricter_verdict(zoe_verdict, decide_v)
    base["decide_verdict"] = decide_v
    base["final_verdict"] = final
    base["action"] = "keep" if final == zoe_verdict else f"escalate->{final}"
    base["items"] = [
        {
            "topic_id_or_gate": "zoe_challenge",
            "yes_no": [
                {"id": "publishable", "yes": yn_pub.get("yes"), "no": yn_pub.get("no")},
                {"id": "invented_numbers", "yes": yn_inv.get("yes"), "no": yn_inv.get("no")},
                {"id": "has_session_summary", "yes": yn_sum.get("yes"), "no": yn_sum.get("no")},
            ],
            "scores": [
                {"id": "invention_risk", "value": _score_val(answers, "invention_risk")},
                {"id": "agree_with_zoe", "value": _score_val(answers, "agree_with_zoe")},
            ],
            "choice": {"id": "would_verdict", "value": decide_v},
            "decision_hint": final,
            "confidence": None,
        }
    ]
    return base


def _score_to_100(raw: float | None) -> float | None:
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v <= 1.0:
        return max(0.0, min(100.0, v * 100.0))
    return max(0.0, min(100.0, v))


def compute_moa_publish_score(answers: dict[str, Any]) -> dict[str, Any]:
    """Weighted 0–100; invented_numbers hard gate. Returns publish_score, defects, dims."""
    c = _score_to_100(_score_val(answers, "completeness"))
    h = _score_to_100(_score_val(answers, "coherence"))
    src = _noul_pair(answers, "sources_cited")
    inv = _noul_pair(answers, "invented_numbers")
    src_yes = src.get("yes")
    inv_yes = inv.get("yes")
    defects: list[dict[str, Any]] = []
    dims = {
        "completeness": c,
        "coherence": h,
        "sources_cited": (None if src_yes is None else round(float(src_yes) * 100.0, 2)),
        "invented_numbers_yes": inv_yes,
    }
    if c is None or h is None or src_yes is None or inv_yes is None:
        defects.append({"id": "missing_dimension", "severity": "blocker"})
        return {
            "publish_score": 0,
            "threshold": MOA_PUBLISH_THRESHOLD,
            "decision": "REWORK",
            "defects": defects,
            "dims": dims,
            "rationale": "missing dimension -> REWORK",
        }
    sources_100 = float(src_yes) * 100.0
    base = (
        MOA_WEIGHT_COMPLETENESS * float(c)
        + MOA_WEIGHT_COHERENCE * float(h)
        + MOA_WEIGHT_SOURCES * sources_100
    )
    publish = int(max(0, min(100, round(base))))
    if float(c) < 70:
        defects.append({"id": "completeness_low", "severity": "major", "value": c})
    if float(h) < 70:
        defects.append({"id": "coherence_low", "severity": "major", "value": h})
    if float(src_yes) < 0.5:
        defects.append({"id": "sources_weak", "severity": "major", "value": src_yes})
    if float(inv_yes) >= 0.5:
        defects.append({"id": "invented_numbers", "severity": "blocker", "value": inv_yes})
        publish = min(publish, 59)
    elif float(inv_yes) >= 0.3:
        defects.append({"id": "invented_numbers_soft", "severity": "major", "value": inv_yes})
        publish = int(max(0, min(100, round(base - 40.0 * (float(inv_yes) - 0.3) / 0.2))))
    floor_fail = any(
        d.get("id") in ("completeness_low", "coherence_low", "sources_weak", "invented_numbers")
        for d in defects
    )
    if floor_fail:
        decision = "REWORK"
    elif publish >= MOA_PUBLISH_THRESHOLD:
        decision = "ACCEPT"
    else:
        defects.append({"id": "below_threshold", "severity": "major", "value": publish})
        decision = "REWORK"
    return {
        "publish_score": publish,
        "threshold": MOA_PUBLISH_THRESHOLD,
        "decision": decision,
        "defects": defects,
        "dims": dims,
        "rationale": f"score={publish} threshold={MOA_PUBLISH_THRESHOLD}",
    }


def decide_moa_publish(
    report_text: str,
    *,
    mode: str,
    artifact_path: str,
    attempt: int = 0,
) -> dict[str, Any]:
    """Score an MOA report; ACCEPT if publish_score ≥90 else REWORK."""
    base: dict[str, Any] = {
        "mode": mode,
        "scope": "moa_publish",
        "as_of": _now_iso(),
        "artifact": artifact_path,
        "model": MODEL,
        "status": "OK",
        "attempt": int(attempt),
        "threshold": MOA_PUBLISH_THRESHOLD,
        "publish_score": None,
        "decision": "ACCEPT",
        "defects": [],
        "items": [],
        "action": "ACCEPT",
    }
    if not (report_text or "").strip():
        base["status"] = "EMPTY_REPORT"
        base["decision"] = "REWORK"
        base["action"] = "REWORK"
        base["publish_score"] = 0
        base["defects"] = [{"id": "empty_report", "severity": "blocker"}]
        base["rationale"] = "empty report"
        return base
    if mode == "off":
        base["status"] = "OFF"
        base["decision"] = "ACCEPT"
        base["action"] = "FAIL-OPEN"
        base["publish_score"] = None
        base["rationale"] = "mode=off kill switch — ACCEPT without score"
        return base

    state = {
        "kind": "moa_report",
        "artifact_excerpt": (report_text or "")[:14000],
    }
    questions = {
        "invented_numbers": {
            "type": "noul",
            "instructions": (
                "Does this MOA report invent or mislabel quantitative claims "
                "(prices, scores, hit-rates, ATR%, ADX, Risk%, valuation/tm numbers)?"
            ),
            "true": "Invented or mislabeled figures present",
            "false": "No invented figures detected",
        },
        "completeness": {
            "type": "score",
            "instructions": "How complete is this MOA report for desk publish?",
            "criteria": [
                "Severe gaps",
                "Barely adequate",
                "Mostly complete",
                "Publish-ready depth",
                "Exemplary coverage",
            ],
        },
        "coherence": {
            "type": "score",
            "instructions": "How coherent and readable is the report (no blend of tm/value scores)?",
            "criteria": [
                "Confused",
                "Fragmented",
                "Acceptable",
                "Clear",
                "Publish-standard",
            ],
        },
        "sources_cited": {
            "type": "noul",
            "instructions": "Are key claims backed by explicit sources or pack cites?",
            "true": "Sources adequate",
            "false": "Sources weak or missing",
        },
        "blends_e5": {
            "type": "noul",
            "instructions": (
                "Does the report improperly blend tm_score with valuation_score "
                "or other sleeve scores into one number?"
            ),
            "true": "E5 blend present",
            "false": "No improper blend",
        },
    }
    payload, detail = call_decisions(state=state, questions=questions, retries=1)
    answers = usable_answers(payload, list(questions)) if payload is not None else None
    if payload is not None and answers is None:
        payload, detail = None, "response had no usable answers"
    if payload is None or answers is None:
        base["status"] = "DECIDE_UNAVAILABLE"
        base["detail"] = detail
        base["decision"] = "ACCEPT"
        base["action"] = "FAIL-OPEN"
        base["rationale"] = f"infra fail-open ({detail})"
        return base

    scored = compute_moa_publish_score(answers)
    blend = _noul_pair(answers, "blends_e5")
    if (blend.get("yes") or 0) >= 0.55:
        scored["defects"].append({"id": "e5_blend", "severity": "blocker", "value": blend.get("yes")})
        scored["decision"] = "REWORK"
        scored["publish_score"] = min(int(scored["publish_score"] or 0), 59)

    base["publish_score"] = scored["publish_score"]
    base["decision"] = scored["decision"]
    base["action"] = scored["decision"]
    base["defects"] = scored["defects"]
    base["dims"] = scored["dims"]
    base["rationale"] = scored["rationale"]
    base["items"] = [
        {
            "topic_id_or_gate": "moa_publish",
            "yes_no": [
                {
                    "id": "invented_numbers",
                    "yes": _noul_pair(answers, "invented_numbers").get("yes"),
                    "no": _noul_pair(answers, "invented_numbers").get("no"),
                },
                {
                    "id": "sources_cited",
                    "yes": _noul_pair(answers, "sources_cited").get("yes"),
                    "no": _noul_pair(answers, "sources_cited").get("no"),
                },
                {"id": "blends_e5", "yes": blend.get("yes"), "no": blend.get("no")},
            ],
            "scores": [
                {"id": "completeness", "value": _score_val(answers, "completeness")},
                {"id": "coherence", "value": _score_val(answers, "coherence")},
            ],
            "decision_hint": scored["decision"],
            "confidence": None,
        }
    ]
    return base


def format_telegram(ledger: dict[str, Any]) -> str:
    mode = str(ledger.get("mode") or "enforce").upper()
    status = str(ledger.get("status") or "OK")
    scope = str(ledger.get("scope") or "")
    # Contract: message must be prefixed with ENFORCE|OFF (not mid-string only).
    lines = [f"{mode} · Mercury Decide · {scope} · status={status}"]
    if scope == "sat_topics":
        lines.append(f"week={ledger.get('week')} approve={len(ledger.get('approve_topic_ids') or [])}")
        for item in ledger.get("items") or []:
            yn = (item.get("yes_no") or [{}])[0]
            scores = item.get("scores") or []
            roi = scores[0].get("value") if scores else None
            yes = yn.get("yes")
            no = yn.get("no")
            ypart = f"Yes {yes:.2f}" if isinstance(yes, (int, float)) else "Yes ?"
            npart = f"No {no:.2f}" if isinstance(no, (int, float)) else "No ?"
            spart = f"roi={roi:.2f}" if isinstance(roi, (int, float)) else "roi=?"
            lines.append(
                f"- {item.get('topic_id')}: {ypart}/{npart} {spart} -> {item.get('decision')}"
            )
        if status == "CANDIDATES_INVALID":
            lines.append(f"action=NO-SPAWN (candidates unusable) detail={ledger.get('detail')}")
        elif status in ("DECIDE_UNAVAILABLE", "OFF", "PARTIAL_FAIL_OPEN"):
            lines.append(f"action=FAIL-OPEN detail={ledger.get('detail') or ledger.get('rationale')}")
    elif scope == "moa_publish":
        lines.append(f"artifact={ledger.get('artifact')} attempt={ledger.get('attempt')}")
        score = ledger.get("publish_score")
        thr = ledger.get("threshold", MOA_PUBLISH_THRESHOLD)
        spart = f"{score}" if score is not None else "?"
        lines.append(
            f"publish_score={spart} threshold={thr} -> {ledger.get('decision')} "
            f"action={ledger.get('action')}"
        )
        dims = ledger.get("dims") or {}
        if dims:
            lines.append(
                "dims "
                f"C={dims.get('completeness')} H={dims.get('coherence')} "
                f"sources={dims.get('sources_cited')} inv={dims.get('invented_numbers_yes')}"
            )
        for d in ledger.get("defects") or []:
            lines.append(f"- defect {d.get('id')} ({d.get('severity')})")
        if status in ("DECIDE_UNAVAILABLE", "OFF"):
            lines.append(f"FAIL-OPEN detail={ledger.get('detail') or ledger.get('rationale')}")
    else:
        lines.append(f"profile={ledger.get('profile')} artifact={ledger.get('artifact')}")
        zoe_label = str(ledger.get("zoe_verdict"))
        if ledger.get("zoe_verdict_parsed") is False:
            zoe_label += " (UNPARSED->default)"
        lines.append(
            f"Zoe={zoe_label} Decide={ledger.get('decide_verdict')} "
            f"final={ledger.get('final_verdict')} action={ledger.get('action')}"
        )
        for item in ledger.get("items") or []:
            for yn in item.get("yes_no") or []:
                yes, no = yn.get("yes"), yn.get("no")
                ypart = f"Yes {yes:.2f}" if isinstance(yes, (int, float)) else "Yes ?"
                npart = f"No {no:.2f}" if isinstance(no, (int, float)) else "No ?"
                lines.append(f"- {yn.get('id')}: {ypart} / {npart}")
            for sc in item.get("scores") or []:
                val = sc.get("value")
                spart = f"{val:.2f}" if isinstance(val, (int, float)) else "?"
                lines.append(f"- metric {sc.get('id')}={spart}")
        if status in ("DECIDE_UNAVAILABLE", "OFF"):
            lines.append(
                f"FAIL-OPEN: keep Zoe verdict; detail={ledger.get('detail') or ledger.get('rationale')}"
            )
    path = ledger.get("ledger_path")
    if path:
        lines.append(f"ledger: {path}")
    return "\n".join(lines)


def send_telegram(msg: str) -> bool:
    """Best-effort Telegram. Returns True on rc==0; never raises, never echoes msg/secrets."""
    cli = os.path.expanduser("~/.local/bin/hermes")
    if not os.path.isfile(cli):
        cli = shutil.which("hermes") or cli
    try:
        proc = subprocess.run(
            [cli, "send", "--to", "telegram", msg],
            timeout=30,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        print(f"WARN telegram: {type(e).__name__}", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(f"WARN telegram: hermes send rc={proc.returncode}", file=sys.stderr)
        return False
    return True


def write_ledger(path: Path, ledger: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger = dict(ledger)
    ledger["ledger_path"] = str(path)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def already_spawned(week: str, topic_id: str) -> bool:
    stamp = ledger_root() / "spawned" / f"{week}.json"
    if not stamp.is_file():
        return False
    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
    except Exception:
        return False
    ids = data.get("topic_ids") if isinstance(data, dict) else None
    return isinstance(ids, list) and topic_id in ids


def mark_spawned(week: str, topic_ids: list[str]) -> None:
    stamp = ledger_root() / "spawned" / f"{week}.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if stamp.is_file():
        try:
            raw = json.loads(stamp.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("topic_ids"), list):
                existing = [str(x) for x in raw["topic_ids"]]
        except Exception:
            existing = []
    merged = sorted(set(existing) | set(topic_ids))
    stamp.write_text(
        json.dumps({"week": week, "topic_ids": merged, "as_of": _now_iso()}, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mercury Decide ENFORCE sidecar")
    ap.add_argument("--scope", choices=("sat", "zoe", "moa_publish"), required=True)
    ap.add_argument("--mode", choices=("off", "enforce"), default=None)
    ap.add_argument("--week", default="", help="ISO week YYYY-Www for sat scope")
    ap.add_argument("--candidates", default="", help="JSON candidates path (sat)")
    ap.add_argument(
        "--artifact",
        default="",
        help="Zoe challenge path (zoe) or MOA report path (moa_publish)",
    )
    ap.add_argument("--profile", default="zoe")
    ap.add_argument("--attempt", type=int, default=0, help="MOA rework attempt index (0=original)")
    ap.add_argument("--out", default="", help="Ledger output path")
    ap.add_argument("--telegram", action="store_true", default=True)
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--mark-spawned", action="store_true", help="Record approve ids for idempotency")
    ap.add_argument(
        "--stamp-only",
        action="store_true",
        help="Sat: read existing ledger --out/--week; stamp approve ids; no API",
    )
    ap.add_argument(
        "--ledger",
        default="",
        help="Existing sat ledger path for --stamp-only",
    )
    ap.add_argument(
        "--only-ids",
        default="",
        help="Comma topic_ids: with --stamp-only stamp only these (partial spawn)",
    )
    args = ap.parse_args(argv)

    mode = resolve_mode(args.mode)
    do_tg = bool(args.telegram) and not args.no_telegram

    if args.scope == "sat":
        week = args.week.strip() or datetime.now(timezone.utc).strftime("%G-W%V")
        out = resolve_path(args.out) if args.out else ledger_root() / f"{week}-improvement-decisions.json"

        if args.stamp_only:
            lpath = resolve_path(args.ledger) if args.ledger else out
            if not lpath.is_file():
                print(f"refuse: ledger missing for --stamp-only: {lpath}", file=sys.stderr)
                return 2
            try:
                ledger = json.loads(lpath.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"refuse: ledger unreadable ({type(e).__name__}): {lpath}", file=sys.stderr)
                return 2
            if not isinstance(ledger, dict):
                print("refuse: ledger not object", file=sys.stderr)
                return 2
            ledger_week = str(ledger.get("week") or "").strip()
            if args.week.strip() and ledger_week and ledger_week != week:
                print(f"refuse: --week {week} != ledger week {ledger_week}", file=sys.stderr)
                return 2
            if not args.week.strip() and ledger_week:
                week = ledger_week  # never stamp under "today" when ledger names its week
            raw_approve = [str(t) for t in (ledger.get("approve_topic_ids") or [])]
            if args.only_ids.strip():
                only = {t.strip() for t in args.only_ids.split(",") if t.strip()}
                raw_approve = [t for t in raw_approve if t in only]
            skipped = [tid for tid in raw_approve if already_spawned(week, tid)]
            approve = [tid for tid in raw_approve if tid not in skipped]
            if approve:
                mark_spawned(week, approve)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "stamp_only": True,
                        "week": week,
                        "approve_topic_ids": approve,
                        "skipped_already_spawned": skipped,
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        if not args.candidates:
            print("refuse: --candidates required for sat", file=sys.stderr)
            return 2
        cpath = resolve_path(args.candidates)
        try:
            candidates = load_candidates(cpath)
        except Exception as e:
            # Still leave a ledger so the spawn step never reads a missing file.
            ledger = {
                "mode": mode,
                "scope": "sat_topics",
                "as_of": _now_iso(),
                "week": week,
                "model": MODEL,
                "status": "CANDIDATES_INVALID",
                "detail": f"candidates unreadable ({type(e).__name__}): {cpath.name}",
                "items": [],
                "approve_topic_ids": [],
                "skipped_already_spawned": [],
            }
            write_ledger(out, ledger)
            msg = format_telegram({**ledger, "ledger_path": str(out)})
            print(msg)
            print(f"refuse: {ledger['detail']}", file=sys.stderr)
            if do_tg:
                send_telegram(msg)
            return 2
        ledger = decide_sat_topics(candidates, mode=mode, week=week)
        raw_approve = list(ledger.get("approve_topic_ids") or [])
        skipped = [tid for tid in raw_approve if already_spawned(week, tid)]
        approve = [tid for tid in raw_approve if tid not in skipped]
        ledger["approve_topic_ids"] = approve
        ledger["skipped_already_spawned"] = skipped
        write_ledger(out, ledger)
        if args.mark_spawned and approve:
            mark_spawned(week, approve)
        msg = format_telegram(ledger)
        print(msg)
        if do_tg:
            send_telegram(msg)
        print(json.dumps({"ok": True, "out": str(out), "approve_topic_ids": approve}, ensure_ascii=False))
        return 0

    if args.scope == "moa_publish":
        if not args.artifact:
            print("refuse: --artifact required for moa_publish", file=sys.stderr)
            return 2
        apath = resolve_path(args.artifact)
        if not apath.is_file():
            print(f"refuse: artifact missing: {apath}", file=sys.stderr)
            return 2
        text = apath.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            print(f"refuse: artifact empty: {apath}", file=sys.stderr)
            return 2
        ledger = decide_moa_publish(
            text,
            mode=mode,
            artifact_path=str(apath),
            attempt=args.attempt,
        )
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", apath.stem) or "moa"
        out = (
            resolve_path(args.out)
            if args.out
            else ledger_root() / "moa" / f"{day}-{stem}.decide.json"
        )
        write_ledger(out, ledger)
        msg = format_telegram(ledger)
        print(msg)
        if do_tg:
            send_telegram(msg)
        decision = str(ledger.get("decision") or "ACCEPT")
        print(
            json.dumps(
                {
                    "ok": True,
                    "out": str(out),
                    "publish_score": ledger.get("publish_score"),
                    "threshold": ledger.get("threshold"),
                    "decision": decision,
                    "action": ledger.get("action"),
                    "status": ledger.get("status"),
                    "defects": ledger.get("defects") or [],
                },
                ensure_ascii=False,
            )
        )
        if ledger.get("status") in ("DECIDE_UNAVAILABLE", "OFF"):
            return 0  # fail-open ACCEPT
        return 0 if decision == "ACCEPT" else 1

    # zoe scope
    if not args.artifact:
        print("refuse: --artifact required for zoe", file=sys.stderr)
        return 2
    apath = resolve_path(args.artifact)
    text = apath.read_text(encoding="utf-8", errors="replace") if apath.is_file() else ""
    if not text:
        print(f"refuse: artifact missing/empty: {apath}", file=sys.stderr)
        return 2
    ledger = decide_zoe_challenge(
        text,
        mode=mode,
        profile=args.profile,
        artifact_path=str(apath),
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Zoe artifacts share basenames across legs (e.g. <date>-challenge.md in different
    # category dirs) — include the parent dir so ledgers do not overwrite each other.
    parent = re.sub(r"[^A-Za-z0-9_.-]+", "_", apath.parent.name) or "x"
    stem = f"{parent}-{apath.stem}"
    out = (
        resolve_path(args.out)
        if args.out
        else ledger_root() / "zoe" / f"{day}-{stem}.decide.json"
    )
    write_ledger(out, ledger)
    msg = format_telegram(ledger)
    print(msg)
    if do_tg:
        send_telegram(msg)
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "final_verdict": ledger.get("final_verdict"),
                "action": ledger.get("action"),
                "status": ledger.get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
