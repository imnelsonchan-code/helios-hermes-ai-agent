#!/usr/bin/env python3
"""Audit/propose legacy OPEN risk plans; writes only with explicit decisions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from market_data import (
    YFinanceTransport,
    congestion_zone,
    normalize_response,
    wilder_atr,
)
from risk_plan import (
    CHANDELIER_POLICY_VERSION,
    POLICY_VERSION,
    ZONE_POLICY_VERSION,
    RiskPlan,
    RiskPolicy,
    RiskPlanError,
    append_plan_event,
    chandelier_policy,
    create_grandfathered_plan,
    create_plan,
    create_plan_with_zone,
    load_plan_store,
    parse_journal_fill,
    plan_to_dict,
    propose_chandelier_trail_sl,
    proposed_plan_record,
    with_created_broker_attestation,
    write_plan_store,
)

DEFAULT_JOURNAL = str(Path.home() / ".hermes" / "trade_journal.csv")
DEFAULT_STORE = str(Path.home() / ".hermes" / "risk_plans.json")
DEFAULT_EVIDENCE_DIR = str(Path.home() / ".hermes" / "shared" / "audit" / "market-data" / "atr-inputs")
DEFAULT_UPGRADE_ARCHIVE = str(
    Path.home() / ".hermes" / "shared" / "audit" / "risk-plan-upgrades"
)
SKIP_STATUS = {"VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED"}
ATR_LOOKBACK_CALENDAR_DAYS = 400
SUPPORTED_MIGRATE_POLICIES = (
    POLICY_VERSION,
    ZONE_POLICY_VERSION,
    CHANDELIER_POLICY_VERSION,
)
UPGRADEABLE_TO_CHANDELIER = frozenset({POLICY_VERSION, ZONE_POLICY_VERSION})


def _immutable_core_dict(plan: RiskPlan) -> dict:
    doc = plan_to_dict(plan)
    doc.pop("events", None)
    return doc


def _immutable_core_differs(prior: RiskPlan, new: RiskPlan) -> bool:
    return _immutable_core_dict(prior) != _immutable_core_dict(new)


def _upgrade_allowed(prior_policy: str, target_policy: str) -> bool:
    return (
        target_policy == CHANDELIER_POLICY_VERSION
        and prior_policy in UPGRADEABLE_TO_CHANDELIER
    )


def _prior_upgradeable_lifecycle(prior: RiskPlan) -> bool:
    """Only CREATED-only plans may be core-replaced (no dropped trail/sell history)."""
    if not prior.events:
        return False
    if prior.events[0].kind != "CREATED":
        return False
    return all(event.kind == "CREATED" for event in prior.events)


def _archive_prior_plan(prior: RiskPlan, archive_dir: str = DEFAULT_UPGRADE_ARCHIVE) -> Path:
    """Persist superseded plan JSON before an audited core replace."""
    root = Path(archive_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = root / f"{prior.plan_id}-{prior.policy_version}-{ts}.json"
    path.write_text(
        json.dumps(plan_to_dict(prior), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _rows(path: str) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _open_buy_rows(rows: list[dict]) -> list[dict]:
    sold: dict[str, float] = {}
    bought: dict[str, float] = {}
    for row in rows:
        status = str(row.get("Status") or "").strip().upper()
        ticker = str(row.get("Ticker") or "").strip().upper()
        action = str(row.get("Action") or "").strip().upper()
        if not ticker or status in SKIP_STATUS:
            continue
        try:
            shares = float(row.get("Shares") or 0)
        except ValueError:
            shares = 0
        target = (
            bought
            if action == "BUY"
            else sold
            if action == "SELL" and status == "CLOSED"
            else None
        )
        if target is not None:
            target[ticker] = target.get(ticker, 0) + shares
    open_tickers = {
        ticker for ticker, total in bought.items() if total - sold.get(ticker, 0) > 0
    }
    return [
        row
        for row in rows
        if str(row.get("Ticker") or "").strip().upper() in open_tickers
        and str(row.get("Action") or "").strip().upper() == "BUY"
        and str(row.get("Status") or "").strip().upper() == "OPEN"
    ]


def _fill_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def _write_atr_evidence(root: str, document: dict) -> tuple[str, str]:
    rendered = json.dumps(document, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    destination = Path(root) / f"sha256-{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        fd, tmp_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(document, fh, indent=2, sort_keys=True)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            try:
                os.link(tmp_name, destination)
            except FileExistsError:
                pass
        finally:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    return "sha256:" + digest, str(destination)


def _zone_record(zone) -> dict[str, str | int | None]:
    return {
        "zone_status": zone.status,
        "zone_reason_code": zone.reason_code,
        "zone_mode": zone.mode,
        "zone_lo": str(zone.zone_lo) if zone.zone_lo is not None else None,
        "zone_hi": str(zone.zone_hi) if zone.zone_hi is not None else None,
        "zone_window_start": zone.window_start.isoformat() if zone.window_start else None,
        "zone_window_end": zone.window_end.isoformat() if zone.window_end else None,
        "zone_bars_used": zone.bars_used,
        "zone_bin_size": str(zone.bin_size) if zone.bin_size is not None else None,
        "zone_mass": str(zone.mass) if zone.mass is not None else None,
        "zone_total_mass": str(zone.total_mass) if zone.total_mass is not None else None,
        "zone_width": str(zone.width) if zone.width is not None else None,
    }


def _print_s0_ticket(plan) -> None:
    lv = plan.levels
    print(
        f"[risk-migrate] S0 ticket {plan.fill.ticker} {plan.plan_id}: "
        f"SL0={lv.sl0} TP1={lv.tp1} tp1_shares={lv.tp1_shares} "
        f"tp2_shares={lv.tp2_shares} policy={plan.policy_version}",
        file=sys.stderr,
    )


def _propose_atr_plan(
    row: dict,
    transport: YFinanceTransport,
    evidence_dir: str,
    *,
    policy_version: str = POLICY_VERSION,
    broker_attestation: dict[str, str] | None = None,
):
    fill = parse_journal_fill(row)
    filled = _fill_date(fill.filled_at)
    response = transport.daily_history(
        fill.yahoo_symbol, filled - timedelta(days=ATR_LOOKBACK_CALENDAR_DAYS), filled
    )
    if response.requested_symbol.upper() != fill.yahoo_symbol.upper():
        raise RiskPlanError("Yahoo requested-symbol mismatch")
    if response.returned_symbol.upper() != fill.yahoo_symbol.upper():
        raise RiskPlanError("Yahoo returned-symbol mismatch")
    bars, currency, issues = normalize_response(response, fill.currency)
    if issues or currency != fill.currency:
        raise RiskPlanError("market currency validation failed: " + ",".join(issues))
    prior = [bar for bar in bars if bar.session < filled]
    if not prior:
        raise RiskPlanError("no fully completed session before fill")
    atr_session = prior[-1].session
    if any(
        split.ratio != Decimal("1")
        and prior[0].session <= split.session <= atr_session
        for split in response.splits
    ):
        raise RiskPlanError("split inside ATR evidence window")
    atr14 = wilder_atr(prior, through_session=atr_session)
    use_chandelier = policy_version == CHANDELIER_POLICY_VERSION
    use_zone = policy_version == ZONE_POLICY_VERSION
    if use_chandelier:
        policy = chandelier_policy()
    elif use_zone:
        policy = RiskPolicy(version=ZONE_POLICY_VERSION)
    else:
        policy = RiskPolicy()
    zone = None
    zone_doc = {
        "zone_status": "SKIPPED",
        "zone_reason_code": (
            "CHANDELIER_NO_ZONE"
            if use_chandelier
            else "POLICY_ATR_R_V2"
            if not use_zone
            else "NONE"
        ),
        "zone_mode": None,
        "zone_lo": None,
        "zone_hi": None,
        "zone_window_start": None,
        "zone_window_end": None,
        "zone_bars_used": 0,
        "zone_bin_size": None,
        "zone_mass": None,
        "zone_total_mass": None,
        "zone_width": None,
    }
    # Zone geometry only when explicitly requested — never sneak widen on atr-r-v2.
    if use_zone:
        zone = congestion_zone(
            prior,
            through_session=atr_session,
            atr14=atr14,
            tick=policy.tick_size,
        )
        zone_doc = _zone_record(zone)
        if zone.status == "OK" and zone.zone_lo is not None and zone.zone_lo >= fill.price:
            zone_doc["zone_status"] = "REJECTED"
            zone_doc["zone_reason_code"] = "ZONE_ABOVE_FILL"
    elif not use_chandelier:
        # Still compute zone for proposal metadata only (shadow compare).
        zone_shadow = congestion_zone(
            prior,
            through_session=atr_session,
            atr14=atr14,
            tick=policy.tick_size,
        )
        zone_doc = _zone_record(zone_shadow)
        zone_doc["zone_status"] = "SHADOW_ONLY"
        # Never surface an underlying OK as if zone geometry were live.
        zone_doc["zone_reason_code"] = "SHADOW_ONLY"
        zone_doc["zone_shadow_reason_code"] = zone_shadow.reason_code or "NONE"
        zone = None
    evidence_doc = {
        "schema_version": "1",
        "symbol": fill.yahoo_symbol,
        "currency": currency,
        "atr_session": atr_session.isoformat(),
        "period": 14,
        "bars": [
            {
                "session": bar.session.isoformat(),
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
                "volume": bar.volume,
            }
            for bar in prior
        ],
        "splits": [
            {"session": split.session.isoformat(), "ratio": str(split.ratio)}
            for split in response.splits
        ],
        "metadata": {
            "exchange": response.exchange,
            "quote_timestamp": response.quote_timestamp,
            "raw": {str(key): str(value) for key, value in response.raw_metadata.items()},
        },
        "atr14": str(atr14),
        "zone": zone_doc,
        "policy_version": policy_version,
    }
    evidence_hash, evidence_path = _write_atr_evidence(evidence_dir, evidence_doc)
    plan = None
    if use_zone and zone_doc["zone_status"] == "OK" and zone is not None:
        try:
            plan = create_plan_with_zone(
                fill,
                atr_session=atr_session,
                atr14=atr14,
                atr_source=evidence_hash,
                created_at=datetime.now(timezone.utc),
                zone=zone,
                policy=policy,
                broker_attestation=broker_attestation,
            )
        except RiskPlanError as exc:
            if "R_max" not in str(exc):
                raise
            zone_doc["zone_status"] = "REJECTED"
            zone_doc["zone_reason_code"] = "R_MAX_EXCEEDED"
            zone_doc["zone_error"] = str(exc)
    if plan is None:
        # atr-zone-v1 with rejected zone falls back to pure atr-r-v2 geometry.
        fallback_policy = policy if use_chandelier else RiskPolicy()
        plan = create_plan(
            fill,
            atr_session=atr_session,
            atr14=atr14,
            atr_source=evidence_hash,
            created_at=datetime.now(timezone.utc),
            policy=fallback_policy,
            broker_attestation=broker_attestation,
        )
    current = {key: str(row.get(key) or "") for key in ("SL", "TP1", "TP2")}
    record = proposed_plan_record(plan, current)
    record.update(zone_doc)
    record["atr_evidence"] = evidence_path
    record["policy_version"] = plan.policy_version
    _print_s0_ticket(plan)
    return plan, record


def _attest_broker_sl(
    *,
    expected_sl: Decimal,
    broker_sl: str,
    broker_sl_none: bool,
) -> dict[str, str]:
    """Return payload fragment for broker static-SL attestation."""
    if broker_sl_none and broker_sl:
        raise RiskPlanError("pass only one of --broker-sl / --broker-sl-none")
    if broker_sl_none:
        return {"broker_sl": "BROKER_SL_NONE", "broker_sl_ack": "NONE"}
    if not broker_sl.strip():
        raise RiskPlanError(
            "adopt/trail requires --broker-sl PRICE (must match sidecar SL) "
            "or --broker-sl-none"
        )
    attested = Decimal(str(broker_sl).replace(",", "").strip())
    if attested != expected_sl:
        raise RiskPlanError(
            f"broker_sl {attested} does not match sidecar SL {expected_sl}"
        )
    return {"broker_sl": str(attested), "broker_sl_ack": "MATCH"}


def adopt_trail_sl(
    *,
    row_id: str,
    session: date,
    store_path: str,
    transport: YFinanceTransport | None = None,
    plans: dict | None = None,
    actor: str = "owner",
    reason: str = "OWNER_CONFIRMED_BROKER_STATIC_SL",
    broker_sl: str = "",
    broker_sl_none: bool = False,
) -> tuple[object, dict]:
    """Append TRAIL_SL from nightly chandelier propose. Writes nothing itself."""
    existing = plans if plans is not None else load_plan_store(store_path)
    plan = existing.get(row_id)
    if plan is None:
        raise RiskPlanError(f"plan not found: {row_id}")
    if plan.policy_version != CHANDELIER_POLICY_VERSION:
        raise RiskPlanError(
            f"TRAIL_SL adopt requires {CHANDELIER_POLICY_VERSION}, "
            f"got {plan.policy_version}"
        )
    filled = _fill_date(plan.fill.filled_at)
    transport = transport or YFinanceTransport()
    response = transport.daily_history(
        plan.fill.yahoo_symbol,
        filled - timedelta(days=ATR_LOOKBACK_CALENDAR_DAYS),
        session + timedelta(days=1),
    )
    bars, currency, issues = normalize_response(response, plan.fill.currency)
    if issues or currency != plan.fill.currency:
        raise RiskPlanError("market currency validation failed: " + ",".join(issues))
    plan_rebased = any(event.kind == "REBASE_SPLIT" for event in plan.events)
    payload, skip_reason = propose_chandelier_trail_sl(
        plan,
        bars,
        through_session=session,
        splits=response.splits,
        plan_rebased=plan_rebased,
        shadow_for_legacy=False,
    )
    if skip_reason:
        raise RiskPlanError(f"trail not adoptable: {skip_reason}")
    if payload is None:
        raise RiskPlanError("trail not adoptable: NO_PAYLOAD")
    attest = _attest_broker_sl(
        expected_sl=Decimal(payload["new_sl"]),
        broker_sl=broker_sl,
        broker_sl_none=broker_sl_none,
    )
    merged = dict(payload)
    merged.update(attest)
    updated = append_plan_event(
        plan,
        kind="TRAIL_SL",
        actor=actor,
        reason=reason,
        payload=merged,
    )
    return updated, merged


def _run_trail_adopt(args: argparse.Namespace) -> int:
    if not args.session:
        print("[risk-migrate] --trail requires --session YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        session = date.fromisoformat(args.session)
    except ValueError:
        print("[risk-migrate] invalid --session", file=sys.stderr)
        return 2
    try:
        existing = load_plan_store(args.store)
        updated, payload = adopt_trail_sl(
            row_id=args.trail,
            session=session,
            store_path=args.store,
            plans=existing,
            broker_sl=args.broker_sl,
            broker_sl_none=args.broker_sl_none,
        )
        proposed = dict(existing)
        proposed[args.trail] = updated
        write_plan_store(args.store, proposed, existing=existing)
    except RiskPlanError as exc:
        print(f"[risk-migrate] trail adopt failed: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"[risk-migrate] trail adopt I/O failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"[risk-migrate] TRAIL_SL {args.trail}: "
        f"{payload.get('old_sl')} -> {payload.get('new_sl')} "
        f"broker={payload.get('broker_sl')} session={payload.get('session')}",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit/propose OPEN risk plans")
    parser.add_argument("--journal", default=DEFAULT_JOURNAL)
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output", default="", help="Optional migration audit JSON")
    parser.add_argument(
        "--policy",
        choices=list(SUPPORTED_MIGRATE_POLICIES),
        default=CHANDELIER_POLICY_VERSION,
        help=(
            "Policy for proposals/adopts: atr-chandelier-v1 (default), "
            "atr-r-v2, atr-zone-v1 (explicit). Existing atr-r-v2/atr-zone-v1 "
            "plans may be upgraded to atr-chandelier-v1 via --adopt "
            "(audited core replace + archive)."
        ),
    )
    parser.add_argument(
        "--trail",
        default="",
        metavar="ROWID",
        help="Adopt tonight's chandelier PROPOSED_TRAIL as TRAIL_SL for this RowID",
    )
    parser.add_argument(
        "--session",
        default="",
        help="Session date YYYY-MM-DD (required with --trail)",
    )
    parser.add_argument(
        "--broker-sl",
        default="",
        help="Attested broker static SL (must match sidecar SL0 / trail new_sl)",
    )
    parser.add_argument(
        "--broker-sl-none",
        action="store_true",
        help="Explicit ack that no broker protective stop is rested",
    )
    parser.add_argument(
        "--adopt",
        action="append",
        default=[],
        metavar="ROWID",
        help="Explicitly adopt proposed ATR policy for this RowID",
    )
    parser.add_argument(
        "--grandfather",
        action="append",
        default=[],
        metavar="ROWID",
        help="Explicitly preserve valid current journal levels for this RowID",
    )
    parser.add_argument(
        "--grandfather-trailed",
        default="",
        metavar="ROWID",
        help="Preserve one legacy plan and append an audited trail event",
    )
    parser.add_argument("--original-sl", default="", help="Original protective SL for --grandfather-trailed")
    parser.add_argument("--trail-sl", default="", help="Current raised SL for --grandfather-trailed")
    parser.add_argument("--trail-reason", default="", help="Required reason for --grandfather-trailed")
    args = parser.parse_args(argv)

    if args.trail:
        return _run_trail_adopt(args)

    try:
        rows = _rows(args.journal)
    except OSError as exc:
        print(f"[risk-migrate] journal unavailable: {exc}", file=sys.stderr)
        return 2

    existing = load_plan_store(args.store)
    proposed = dict(existing)
    decisions = set(args.adopt) | set(args.grandfather)
    if args.grandfather_trailed:
        decisions.add(args.grandfather_trailed)
    report: list[dict] = []
    core_replacements: set[str] = set()
    transport = YFinanceTransport()
    for row in _open_buy_rows(rows):
        row_id = str(row.get("RowID") or "").strip()
        if not row_id:
            report.append({"ticker": row.get("Ticker"), "status": "BLOCKED", "issue": "ROWID_MISSING"})
            continue
        try:
            if row_id in args.grandfather or row_id == args.grandfather_trailed:
                fill = parse_journal_fill(row)
                sl_value = Decimal(
                    args.original_sl
                    if row_id == args.grandfather_trailed
                    else str(row.get("SL") or "")
                )
                if row_id == args.grandfather_trailed:
                    if not args.trail_sl or not args.trail_reason:
                        raise RiskPlanError(
                            "--grandfather-trailed requires --original-sl, "
                            "--trail-sl, and --trail-reason"
                        )
                    trail_new = Decimal(str(args.trail_sl))
                    attest = _attest_broker_sl(
                        expected_sl=trail_new,
                        broker_sl=args.broker_sl,
                        broker_sl_none=args.broker_sl_none,
                    )
                    plan = create_grandfathered_plan(
                        fill,
                        sl=sl_value,
                        tp1=Decimal(str(row.get("TP1") or "")),
                        tp2=Decimal(str(row.get("TP2") or "")),
                    )
                    payload = {
                        "old_sl": args.original_sl,
                        "new_sl": args.trail_sl,
                        **attest,
                    }
                    plan = append_plan_event(
                        plan,
                        kind="TRAIL_SL",
                        actor="migration-approved",
                        reason=args.trail_reason,
                        payload=payload,
                    )
                else:
                    attest = _attest_broker_sl(
                        expected_sl=sl_value,
                        broker_sl=args.broker_sl,
                        broker_sl_none=args.broker_sl_none,
                    )
                    plan = create_grandfathered_plan(
                        fill,
                        sl=sl_value,
                        tp1=Decimal(str(row.get("TP1") or "")),
                        tp2=Decimal(str(row.get("TP2") or "")),
                        broker_attestation=attest,
                    )
                record = {
                    "plan_id": row_id,
                    "ticker": fill.ticker,
                    "status": "PROPOSED",
                    "selected": (
                        "GRANDFATHER_TRAILED"
                        if row_id == args.grandfather_trailed
                        else "GRANDFATHER_CURRENT"
                    ),
                    "plan": plan_to_dict(plan),
                    "broker_attestation": attest,
                }
                proposed[row_id] = plan
                _print_s0_ticket(plan)
                report.append(record)
            else:
                # Single Yahoo propose. On adopt, freeze attestation onto CREATED
                # without a second market fetch (levels already fixed).
                plan, record = _propose_atr_plan(
                    row,
                    transport,
                    args.evidence_dir,
                    policy_version=args.policy,
                )
                if row_id in args.adopt:
                    prior = existing.get(row_id)
                    if prior is not None and _immutable_core_differs(prior, plan):
                        if not _upgrade_allowed(prior.policy_version, args.policy):
                            raise RiskPlanError(
                                f"immutable plan exists for {row_id} "
                                f"({prior.policy_version}); cannot adopt "
                                f"{args.policy} without an allowed upgrade path"
                            )
                        if not _prior_upgradeable_lifecycle(prior):
                            kinds = ",".join(sorted({e.kind for e in prior.events}))
                            raise RiskPlanError(
                                f"refuse core replace for {row_id}: prior plan "
                                f"has post-CREATED lifecycle events ({kinds}); "
                                f"archive-only upgrade would drop TRAIL/SELL/"
                                f"REBASE history from the live store"
                            )
                        archive_path = _archive_prior_plan(prior)
                        attest = _attest_broker_sl(
                            expected_sl=plan.levels.sl0,
                            broker_sl=args.broker_sl,
                            broker_sl_none=args.broker_sl_none,
                        )
                        attest = {
                            **attest,
                            "upgraded_from": prior.policy_version,
                            "prior_calculation_hash": prior.calculation_hash,
                            "prior_archive": str(archive_path),
                        }
                        plan = with_created_broker_attestation(plan, attest)
                        core_replacements.add(row_id)
                        record["status"] = "PROPOSED"
                        record["selected"] = "UPGRADE_TO_CHANDELIER"
                        record["broker_attestation"] = attest
                        record["prior_archive"] = str(archive_path)
                        record["plan"] = plan_to_dict(plan)
                        proposed[row_id] = plan
                    else:
                        attest = _attest_broker_sl(
                            expected_sl=plan.levels.sl0,
                            broker_sl=args.broker_sl,
                            broker_sl_none=args.broker_sl_none,
                        )
                        plan = with_created_broker_attestation(plan, attest)
                        record["status"] = "PROPOSED"
                        record["selected"] = "ADOPT_NEW_POLICY"
                        record["broker_attestation"] = attest
                        record["plan"] = plan_to_dict(plan)
                        proposed[row_id] = plan
                else:
                    record["status"] = "PROPOSED"
                report.append(record)
        except Exception as exc:
            report.append(
                {
                    "plan_id": row_id,
                    "ticker": row.get("Ticker"),
                    "status": "BLOCKED",
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )

    document = {
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "journal": args.journal,
        "store": args.store,
        "policy": args.policy,
        "read_only": not bool(decisions),
        "proposals": report,
    }
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if decisions:
        known = {str(item.get("plan_id") or "") for item in report}
        unknown = decisions - known
        if unknown:
            print("[risk-migrate] unknown decisions: " + ",".join(sorted(unknown)), file=sys.stderr)
            return 2
        selected_failures = [
            item["plan_id"]
            for item in report
            if item.get("plan_id") in decisions and item.get("status") == "BLOCKED"
        ]
        if selected_failures:
            print("[risk-migrate] selected plans blocked: " + ",".join(selected_failures), file=sys.stderr)
            return 2
        write_plan_store(
            args.store,
            proposed,
            existing=existing,
            allow_core_replace=core_replacements,
        )
        print(f"[risk-migrate] wrote {len(proposed)} plan(s)", file=sys.stderr)
        if core_replacements:
            print(
                "[risk-migrate] core replacements: "
                + ",".join(sorted(core_replacements)),
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
