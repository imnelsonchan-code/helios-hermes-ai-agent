#!/usr/bin/env python3
"""Deterministic, auditable lot-level SL/TP risk plans.

The trade journal remains the execution ledger.  This module owns a separate
versioned sidecar whose entry-time inputs and calculated levels are immutable;
only append-only lifecycle/amendment events may be added.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from market_data import ZoneEvidence

SCHEMA_VERSION = "1"
POLICY_VERSION = "atr-r-v2"
ZONE_POLICY_VERSION = "atr-zone-v1"
CHANDELIER_POLICY_VERSION = "atr-chandelier-v1"
LEGACY_POLICY_VERSION = "legacy-journal-v1"
SUPPORTED_POLICY_VERSIONS = frozenset(
    {
        POLICY_VERSION,
        ZONE_POLICY_VERSION,
        CHANDELIER_POLICY_VERSION,
        LEGACY_POLICY_VERSION,
    }
)
SKIP_STATUS = {"VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED"}
PLAN_ROW_TOKEN = "PLAN_ROW_ID="
LOT_RISK_CAP = Decimal("0.005")
BOOK_RISK_CAP = Decimal("0.03")
SECTOR_RISK_CAP = Decimal("0.015")
STRESS_GAP_CAP = Decimal("0.05")


class RiskPlanError(ValueError):
    """Risk-plan input, integrity, or lifecycle failure."""


def _decimal(value, field_name: str) -> Decimal:
    try:
        out = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise RiskPlanError(f"{field_name}: invalid decimal") from exc
    if not out.is_finite():
        raise RiskPlanError(f"{field_name}: non-finite decimal")
    return out


def _positive(value, field_name: str) -> Decimal:
    out = _decimal(value, field_name)
    if out <= 0:
        raise RiskPlanError(f"{field_name}: must be positive")
    return out


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _round_tick(value: Decimal, tick: Decimal, rounding=ROUND_HALF_UP) -> Decimal:
    if tick <= 0:
        raise RiskPlanError("tick_size: must be positive")
    return (value / tick).quantize(Decimal("1"), rounding=rounding) * tick


def _round_long_stop(raw: Decimal, fill_price: Decimal, tick: Decimal) -> Decimal:
    """Round a long stop up (toward fill) so tick rounding cannot increase $ risk."""
    sl0 = _round_tick(raw, tick, ROUND_CEILING)
    if sl0 >= fill_price:
        raise RiskPlanError("calculated long levels have invalid geometry")
    return sl0


def _round_long_target(raw: Decimal, tick: Decimal) -> Decimal:
    """Round a long target away from fill (up in price)."""
    return _round_tick(raw, tick, ROUND_CEILING)


@dataclass(frozen=True)
class RiskPolicy:
    version: str = POLICY_VERSION
    atr_period: int = 14
    risk_atr_multiple: Decimal = Decimal("1.5")
    risk_max_atr_multiple: Decimal = Decimal("2.5")
    tp1_r_multiple: Decimal = Decimal("2")
    tp2_r_multiple: Decimal = Decimal("4")
    tp1_fraction: Decimal = Decimal("0.5")
    tick_size: Decimal = Decimal("0.01")
    zone_window_bars: int = 20
    zone_alpha: Decimal = Decimal("0.10")
    zone_rho: Decimal = Decimal("0.40")
    zone_beta_atr: Decimal = Decimal("2.0")
    zone_kappa_atr: Decimal = Decimal("0.5")
    zone_merge: str = "min"
    trail_k: Decimal = Decimal("4.0")
    trail_anchor: str = "close"


def chandelier_policy(**overrides) -> RiskPolicy:
    """Voted atr-chandelier-v1 defaults: TP1@2R, ~1/3 tranche, k=4.0 close trail."""
    base = dict(
        version=CHANDELIER_POLICY_VERSION,
        tp1_r_multiple=Decimal("2"),
        tp1_fraction=Decimal("1") / Decimal("3"),
        trail_k=Decimal("4.0"),
        trail_anchor="close",
    )
    base.update(overrides)
    return RiskPolicy(**base)


def has_fixed_tp2(policy_version: str) -> bool:
    return policy_version != CHANDELIER_POLICY_VERSION


def _long_geometry_ok(
    sl0: Decimal,
    fill: Decimal,
    tp1: Decimal,
    tp2: Decimal,
    policy_version: str,
) -> bool:
    if not (sl0 < fill < tp1):
        return False
    if has_fixed_tp2(policy_version):
        return tp1 < tp2
    return tp2 == tp1


@dataclass(frozen=True)
class JournalFill:
    row_id: str
    ticker: str
    yahoo_symbol: str
    filled_at: str
    shares: int
    currency: str
    price: Decimal
    source_field: str


@dataclass(frozen=True)
class RiskLevels:
    atr14: Decimal
    risk_per_share: Decimal
    sl0: Decimal
    active_sl: Decimal
    tp1: Decimal
    tp2: Decimal
    tp1_shares: int
    tp2_shares: int


@dataclass(frozen=True)
class PlanEvent:
    event_id: str
    kind: str
    occurred_at: str
    actor: str
    reason: str
    journal_row_id: str | None = None
    previous_event_id: str | None = None
    payload: Mapping[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskPlan:
    plan_id: str
    policy_version: str
    fill: JournalFill
    atr_session: str
    atr_source: str
    levels: RiskLevels
    input_hash: str
    calculation_hash: str
    events: tuple[PlanEvent, ...]
    policy: Mapping[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanView:
    state: str
    remaining_shares: int
    active_sl: Decimal
    issues: tuple[str, ...]
    tp1: Decimal = Decimal("0")
    tp2: Decimal = Decimal("0")
    rebased: bool = False


def parse_journal_fill(
    row: Mapping[str, str],
    *,
    yahoo_symbol: str | None = None,
    total_tolerance: Decimal = Decimal("0.01"),
) -> JournalFill:
    """Parse a BUY fill without ever treating a GBP amount as a USD fill."""
    action = str(row.get("Action") or "").strip().upper()
    status = str(row.get("Status") or "").strip().upper()
    if action != "BUY" or status in SKIP_STATUS:
        raise RiskPlanError("row is not an eligible BUY")

    row_id = str(row.get("RowID") or "").strip()
    ticker = str(row.get("Ticker") or "").strip().upper()
    if not row_id or not ticker:
        raise RiskPlanError("RowID and Ticker are required")
    shares_dec = _positive(row.get("Shares"), "Shares")
    if shares_dec != shares_dec.to_integral_value():
        raise RiskPlanError("Shares: whole shares required")
    shares = int(shares_dec)

    total_raw = str(row.get("Total USD") or "").strip()
    usd_raw = str(row.get("Price USD") or "").strip()
    total_usd = _decimal(total_raw, "Total USD") if total_raw else Decimal("0")
    if total_usd > 0 or usd_raw:
        currency = "USD"
        if usd_raw:
            price = _positive(usd_raw, "Price USD")
            source = "Price USD"
            if total_usd > 0:
                implied_total = price * shares
                relative = abs(implied_total - total_usd) / total_usd
                if relative > total_tolerance:
                    raise RiskPlanError("Price USD and Total USD disagree by more than 1%")
        elif total_usd > 0:
            price = total_usd / shares
            source = "Total USD/Shares"
        else:
            raise RiskPlanError("USD fill has no native-currency price")
    else:
        currency = "GBP"
        price = _positive(row.get("Price"), "Price")
        source = "Price"

    filled_at = str(row.get("FilledAt") or row.get("Date") or "").strip()
    if not filled_at:
        raise RiskPlanError("Date: required")
    return JournalFill(
        row_id=row_id,
        ticker=ticker,
        yahoo_symbol=(yahoo_symbol or ticker).strip().upper(),
        filled_at=filled_at,
        shares=shares,
        currency=currency,
        price=price,
        source_field=source,
    )


def calculate_levels(
    fill: JournalFill,
    atr14: Decimal,
    policy: RiskPolicy | None = None,
) -> RiskLevels:
    policy = policy or RiskPolicy()
    atr = _positive(atr14, "ATR14")
    risk = atr * policy.risk_atr_multiple
    sl0 = _round_long_stop(fill.price - risk, fill.price, policy.tick_size)
    tp1 = _round_long_target(fill.price + risk * policy.tp1_r_multiple, policy.tick_size)
    if policy.version == CHANDELIER_POLICY_VERSION:
        # Unused fixed TP2 placeholder: equal to TP1; runner qty lives in tp2_shares.
        tp2 = tp1
    else:
        tp2 = _round_long_target(fill.price + risk * policy.tp2_r_multiple, policy.tick_size)
    risk_rounded = fill.price - sl0
    if sl0 <= 0 or not _long_geometry_ok(sl0, fill.price, tp1, tp2, policy.version):
        raise RiskPlanError("calculated long levels have invalid geometry")
    tp1_shares = int(
        (Decimal(fill.shares) * policy.tp1_fraction).to_integral_value(rounding="ROUND_FLOOR")
    )
    if fill.shares == 1:
        tp1_shares = 0
    tp2_shares = fill.shares - tp1_shares
    return RiskLevels(
        atr14=atr,
        risk_per_share=risk_rounded,
        sl0=sl0,
        active_sl=sl0,
        tp1=tp1,
        tp2=tp2,
        tp1_shares=tp1_shares,
        tp2_shares=tp2_shares,
    )


def _tp_share_split(fill: JournalFill, policy: RiskPolicy) -> tuple[int, int]:
    tp1_shares = int(
        (Decimal(fill.shares) * policy.tp1_fraction).to_integral_value(rounding="ROUND_FLOOR")
    )
    if fill.shares == 1:
        tp1_shares = 0
    return tp1_shares, fill.shares - tp1_shares


def _zone_level_metadata(
    fill: JournalFill,
    atr14: Decimal,
    zone: ZoneEvidence | None,
    policy: RiskPolicy,
) -> dict[str, Decimal | str]:
    atr = _positive(atr14, "ATR14")
    atr_sl = fill.price - atr * policy.risk_atr_multiple
    zone_status = "NONE"
    zone_mode = ""
    zone_lo: Decimal | None = None
    zone_hi: Decimal | None = None
    zone_sl: Decimal | None = None
    sl_raw = atr_sl
    if zone is not None:
        if zone.status != "OK":
            raise RiskPlanError(f"zone must be OK, got {zone.status}:{zone.reason_code}")
        if zone.mode is None or zone.zone_lo is None or zone.zone_hi is None:
            raise RiskPlanError("zone evidence missing bounds")
        if zone.zone_lo >= fill.price:
            raise RiskPlanError("zone is above fill")
        zone_status = zone.status
        zone_mode = zone.mode
        zone_lo = zone.zone_lo
        zone_hi = zone.zone_hi
        zone_sl = zone.zone_lo - atr * policy.zone_kappa_atr
        sl_raw = min(atr_sl, zone_sl)
    if fill.price - sl_raw > atr * policy.risk_max_atr_multiple:
        raise RiskPlanError("zone widened stop exceeds R_max")
    return {
        "atr": atr,
        "atr_sl": atr_sl,
        "zone_sl": zone_sl if zone_sl is not None else Decimal("0"),
        "sl_raw": sl_raw,
        "zone_mode": zone_mode,
        "zone_lo": zone_lo if zone_lo is not None else Decimal("0"),
        "zone_hi": zone_hi if zone_hi is not None else Decimal("0"),
        "zone_status": zone_status,
    }


def calculate_levels_with_zone(
    fill: JournalFill,
    atr14: Decimal,
    zone: ZoneEvidence | None,
    policy: RiskPolicy | None = None,
) -> RiskLevels:
    policy = policy or RiskPolicy(version=ZONE_POLICY_VERSION)
    if zone is None:
        return calculate_levels(fill, atr14, policy)
    meta = _zone_level_metadata(fill, atr14, zone, policy)
    atr = meta["atr"]
    sl0 = _round_long_stop(meta["sl_raw"], fill.price, policy.tick_size)
    risk_eff = fill.price - sl0
    tp1 = _round_long_target(fill.price + risk_eff * policy.tp1_r_multiple, policy.tick_size)
    tp2 = _round_long_target(fill.price + risk_eff * policy.tp2_r_multiple, policy.tick_size)
    if sl0 <= 0 or not (sl0 < fill.price < tp1 < tp2):
        raise RiskPlanError("calculated long levels have invalid geometry")
    tp1_shares, tp2_shares = _tp_share_split(fill, policy)
    return RiskLevels(
        atr14=atr,
        risk_per_share=risk_eff,
        sl0=sl0,
        active_sl=sl0,
        tp1=tp1,
        tp2=tp2,
        tp1_shares=tp1_shares,
        tp2_shares=tp2_shares,
    )


def _fill_session(fill: JournalFill) -> date:
    raw = str(fill.filled_at or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw[:19].replace("Z", ""), fmt.replace("Z", "")).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise RiskPlanError("fill date unparseable") from exc


def propose_chandelier_trail_sl(
    plan: RiskPlan,
    bars: Sequence,
    *,
    through_session: date,
    splits: Sequence | None = None,
    plan_rebased: bool = False,
    shadow_for_legacy: bool = False,
) -> tuple[dict[str, str] | None, str | None]:
    """Propose a monotone TRAIL_SL raise from closes. Does not append events.

    Returns ``(payload, reason)``. ``payload`` is suitable for
    ``append_plan_event(..., kind="TRAIL_SL")`` after owner confirmation
    when the plan is already ``atr-chandelier-v1``.
    ``reason`` is set when no proposal is emitted (e.g. ``UNREBASED_SPLIT``,
    ``MISSING_SESSION``, ``NO_RAISE``). Never mutates the immutable plan core.

    When ``plan_rebased`` is True, post-fill splits are assumed already restated
    via ``REBASE_SPLIT`` and the unrebased-split refuse is skipped.

    ``shadow_for_legacy``: compute the voted chandelier trail against an
    atr-r-v2 / atr-zone-v1 plan for file-only comparison. Payload is display
    only — do not adopt onto a non-chandelier plan without a policy migrate.
    """
    from market_data import (  # local import: avoid cycle at module load
        MarketDataError,
        chandelier_raw,
        unrebased_split_in_window,
    )

    legacy_ok = plan.policy_version in {POLICY_VERSION, ZONE_POLICY_VERSION}
    if plan.policy_version == CHANDELIER_POLICY_VERSION:
        anchor = str((plan.policy or {}).get("trail_anchor") or "close")
        if anchor != "close":
            raise RiskPlanError(f"unsupported trail_anchor: {anchor}")
        trail_k = _positive((plan.policy or {}).get("trail_k") or "4.0", "trail_k")
        atr_period = int((plan.policy or {}).get("atr_period") or 14)
    elif shadow_for_legacy and legacy_ok:
        anchor = "close"
        trail_k = Decimal("4.0")
        atr_period = 14
    else:
        return None, "WRONG_POLICY"
    tick = _plan_tick(plan)
    from_session = _fill_session(plan.fill)
    if (not plan_rebased) and unrebased_split_in_window(
        splits or (),
        plan_created_session=from_session,
        through_session=through_session,
    ):
        return None, "UNREBASED_SPLIT"
    try:
        _hc, atr, raw = chandelier_raw(
            bars,
            from_session=from_session,
            through_session=through_session,
            trail_k=trail_k,
            atr_period=atr_period,
        )
    except MarketDataError:
        return None, "MISSING_SESSION"
    current = _event_active_sl(plan)
    if plan_rebased:
        # Levels already restated via REBASE_SPLIT; do not floor on pre-split SL0
        # and do not refuse post-fill splits (Yahoo history is restated).
        candidate = _round_tick(max(current, raw), tick, ROUND_CEILING)
    else:
        # Floor at immutable SL0 so the trail never undercuts the entry stop.
        # May rise above fill after a favourable run (explicit trail, not auto-BE).
        candidate = _round_tick(max(plan.levels.sl0, raw), tick, ROUND_CEILING)
    if candidate <= current:
        # Real chandelier: no adoptable proposal. Legacy shadow: emit a
        # display-only compare payload so owners see the path ran (not silence).
        if shadow_for_legacy and legacy_ok:
            return (
                {
                    "old_sl": str(current),
                    "new_sl": str(candidate),
                    "session": through_session.isoformat(),
                    "atr14": str(atr),
                    "highest_close": str(_hc),
                    "trail_k": str(trail_k),
                    "trail_anchor": anchor,
                    "entry_session": from_session.isoformat(),
                    "shadow": "atr-chandelier-v1",
                    "compare_only": "NO_RAISE",
                },
                "NO_RAISE",
            )
        return None, "NO_RAISE"
    payload = {
        "old_sl": str(current),
        "new_sl": str(candidate),
        "session": through_session.isoformat(),
        "atr14": str(atr),
        "highest_close": str(_hc),
        "trail_k": str(trail_k),
        "trail_anchor": anchor,
        "entry_session": from_session.isoformat(),
    }
    if shadow_for_legacy and plan.policy_version != CHANDELIER_POLICY_VERSION:
        payload["shadow"] = "atr-chandelier-v1"
    return payload, None


def trail_exit_triggered(close, trail) -> bool:
    """Close-based chandelier exit: ``close <= trail``."""
    return _decimal(close, "close") <= _decimal(trail, "trail")


def create_plan(
    fill: JournalFill,
    *,
    atr_session: date,
    atr14: Decimal,
    atr_source: str,
    created_at: datetime | None = None,
    actor: str = "migration-approved",
    reason: str = "ADOPT_NEW_POLICY",
    policy: RiskPolicy | None = None,
    broker_attestation: Mapping[str, str] | None = None,
) -> RiskPlan:
    """Create a pure, reproducible plan; performs no I/O."""
    policy = policy or RiskPolicy()
    if policy.version == CHANDELIER_POLICY_VERSION and policy.trail_anchor != "close":
        raise RiskPlanError(f"unsupported trail_anchor: {policy.trail_anchor}")
    levels = calculate_levels(fill, atr14, policy)
    extras = {}
    if policy.version == CHANDELIER_POLICY_VERSION:
        extras["tp2_mode"] = "unused"
    input_doc = {
        "fill": _fill_to_dict(fill),
        "atr_session": atr_session.isoformat(),
        "atr14": str(atr14),
        "atr_source": atr_source,
        "policy": _policy_to_dict(policy, extras=extras or None),
    }
    calc_doc = _levels_to_dict(levels)
    occurred = created_at or datetime.now(timezone.utc)
    created_payload: dict[str, str | int] = {}
    if broker_attestation:
        created_payload.update({str(k): v for k, v in broker_attestation.items()})
    event_base = {
        "kind": "CREATED",
        "occurred_at": _iso_utc(occurred),
        "actor": actor,
        "reason": reason,
        "journal_row_id": None,
        "previous_event_id": None,
        "payload": created_payload,
    }
    event = PlanEvent(event_id=_canonical_hash(event_base), **event_base)
    return RiskPlan(
        plan_id=fill.row_id,
        policy_version=policy.version,
        fill=fill,
        atr_session=atr_session.isoformat(),
        atr_source=atr_source,
        levels=levels,
        input_hash=_canonical_hash(input_doc),
        calculation_hash=_canonical_hash(calc_doc),
        events=(event,),
        policy=_policy_to_dict(policy, extras=extras or None),
    )


def create_plan_with_zone(
    fill: JournalFill,
    *,
    atr_session: date,
    atr14: Decimal,
    atr_source: str,
    zone: ZoneEvidence,
    created_at: datetime | None = None,
    actor: str = "migration-approved",
    reason: str = "ADOPT_NEW_POLICY",
    policy: RiskPolicy | None = None,
    broker_attestation: Mapping[str, str] | None = None,
) -> RiskPlan:
    """Create a zone-aware plan with immutable congestion evidence in policy."""
    base_policy = policy or RiskPolicy()
    if zone.status != "OK":
        raise RiskPlanError(f"zone must be OK, got {zone.status}:{zone.reason_code}")
    zone_policy = replace(base_policy, version=ZONE_POLICY_VERSION)
    levels = calculate_levels_with_zone(fill, atr14, zone, zone_policy)
    zone_meta = _zone_level_metadata(fill, atr14, zone, zone_policy)
    policy_doc = _policy_to_dict(
        zone_policy,
        extras={
            "zone_mode": str(zone_meta["zone_mode"]),
            "zone_lo": str(zone_meta["zone_lo"]),
            "zone_hi": str(zone_meta["zone_hi"]),
            "atr_sl": str(zone_meta["atr_sl"]),
            "zone_sl": str(zone_meta["zone_sl"]),
            "zone_status": str(zone_meta["zone_status"]),
            "merge": zone_policy.zone_merge,
        },
    )
    input_doc = {
        "fill": _fill_to_dict(fill),
        "atr_session": atr_session.isoformat(),
        "atr14": str(atr14),
        "atr_source": atr_source,
        "policy": policy_doc,
    }
    calc_doc = _levels_to_dict(levels)
    occurred = created_at or datetime.now(timezone.utc)
    created_payload: dict[str, str | int] = {}
    if broker_attestation:
        created_payload.update({str(k): v for k, v in broker_attestation.items()})
    event_base = {
        "kind": "CREATED",
        "occurred_at": _iso_utc(occurred),
        "actor": actor,
        "reason": reason,
        "journal_row_id": None,
        "previous_event_id": None,
        "payload": created_payload,
    }
    event = PlanEvent(event_id=_canonical_hash(event_base), **event_base)
    return RiskPlan(
        plan_id=fill.row_id,
        policy_version=zone_policy.version,
        fill=fill,
        atr_session=atr_session.isoformat(),
        atr_source=atr_source,
        levels=levels,
        input_hash=_canonical_hash(input_doc),
        calculation_hash=_canonical_hash(calc_doc),
        events=(event,),
        policy=policy_doc,
    )


def create_grandfathered_plan(
    fill: JournalFill,
    *,
    sl: Decimal,
    tp1: Decimal,
    tp2: Decimal,
    created_at: datetime | None = None,
    actor: str = "migration-approved",
    broker_attestation: Mapping[str, str] | None = None,
) -> RiskPlan:
    """Record existing journal geometry without pretending it came from ATR."""
    sl_value = _positive(sl, "SL")
    tp1_value = _positive(tp1, "TP1")
    tp2_value = _positive(tp2, "TP2")
    if not (sl_value < fill.price < tp1_value < tp2_value):
        raise RiskPlanError("legacy long levels have invalid geometry")
    risk = fill.price - sl_value
    tp1_shares = fill.shares // 2
    levels = RiskLevels(
        atr14=Decimal("0"),
        risk_per_share=risk,
        sl0=sl_value,
        active_sl=sl_value,
        tp1=tp1_value,
        tp2=tp2_value,
        tp1_shares=tp1_shares,
        tp2_shares=fill.shares - tp1_shares,
    )
    input_doc = {
        "fill": _fill_to_dict(fill),
        "journal_levels": _levels_to_dict(levels),
        "policy": LEGACY_POLICY_VERSION,
    }
    created_payload: dict[str, str | int] = {}
    if broker_attestation:
        created_payload.update({str(k): v for k, v in broker_attestation.items()})
    event_base = {
        "kind": "CREATED",
        "occurred_at": _iso_utc(created_at or datetime.now(timezone.utc)),
        "actor": actor,
        "reason": "GRANDFATHER_CURRENT",
        "journal_row_id": None,
        "previous_event_id": None,
        "payload": created_payload,
    }
    event = PlanEvent(event_id=_canonical_hash(event_base), **event_base)
    return RiskPlan(
        plan_id=fill.row_id,
        policy_version=LEGACY_POLICY_VERSION,
        fill=fill,
        atr_session="N/A",
        atr_source="journal-legacy:no-atr",
        levels=levels,
        input_hash=_canonical_hash(input_doc),
        calculation_hash=_canonical_hash(_levels_to_dict(levels)),
        events=(event,),
        policy={"version": LEGACY_POLICY_VERSION},
    )


def with_created_broker_attestation(
    plan: RiskPlan,
    broker_attestation: Mapping[str, str],
) -> RiskPlan:
    """Freeze broker SL attestation onto CREATED without recomputing levels.

    Only valid for CREATED-only plans (adopt path). Rehashing CREATED would
    break ``previous_event_id`` chains if later events already exist.
    """
    if not plan.events or plan.events[0].kind != "CREATED":
        raise RiskPlanError("plan missing CREATED event")
    if len(plan.events) != 1:
        raise RiskPlanError(
            "with_created_broker_attestation only allowed on CREATED-only plans"
        )
    created = plan.events[0]
    if created.payload.get("broker_sl") or created.payload.get("broker_sl_ack"):
        raise RiskPlanError("CREATED already has broker attestation")
    new_payload = {
        **{str(k): v for k, v in created.payload.items()},
        **{str(k): v for k, v in broker_attestation.items()},
    }
    event_base = {
        "kind": created.kind,
        "occurred_at": created.occurred_at,
        "actor": created.actor,
        "reason": created.reason,
        "journal_row_id": created.journal_row_id,
        "previous_event_id": created.previous_event_id,
        "payload": new_payload,
    }
    new_created = PlanEvent(event_id=_canonical_hash(event_base), **event_base)
    return replace(plan, events=(new_created,))


def append_plan_event(
    plan: RiskPlan,
    *,
    kind: str,
    actor: str,
    reason: str,
    payload: Mapping[str, str | int],
    occurred_at: datetime | None = None,
    journal_row_id: str | None = None,
) -> RiskPlan:
    """Append a hashed event without changing the immutable plan core."""
    if kind not in {"SELL_CONFIRMED", "TRAIL_SL", "REBASE_SPLIT", "CLOSED"}:
        raise RiskPlanError(f"unsupported event kind: {kind}")
    if not actor.strip() or not reason.strip():
        raise RiskPlanError("event actor and reason are required")
    if kind in {"SELL_CONFIRMED", "CLOSED"} and not journal_row_id:
        raise RiskPlanError(f"{kind} requires journal_row_id")
    if kind == "SELL_CONFIRMED":
        _positive(payload.get("shares"), "SELL_CONFIRMED shares")
    if kind == "REBASE_SPLIT":
        _positive(payload.get("ratio"), "REBASE_SPLIT ratio")
        _positive(payload.get("new_shares"), "REBASE_SPLIT new_shares")
        _positive(payload.get("new_sl"), "REBASE_SPLIT new_sl")
        _positive(payload.get("new_tp1"), "REBASE_SPLIT new_tp1")
        _positive(payload.get("new_tp2"), "REBASE_SPLIT new_tp2")
        if not str(payload.get("effective_date") or "").strip():
            raise RiskPlanError("REBASE_SPLIT effective_date is required")
    if kind == "TRAIL_SL":
        old_sl = _positive(payload.get("old_sl"), "TRAIL_SL old_sl")
        new_sl = _positive(payload.get("new_sl"), "TRAIL_SL new_sl")
        current_sl = _event_active_sl(plan)
        if old_sl != current_sl:
            raise RiskPlanError("TRAIL_SL old_sl does not match current active SL")
        if new_sl < old_sl:
            raise RiskPlanError("TRAIL_SL may not lower the stop")
        broker_raw = str(payload.get("broker_sl") or "").strip()
        if not broker_raw:
            raise RiskPlanError(
                "TRAIL_SL requires broker_sl attestation "
                "(price matching new_sl, or BROKER_SL_NONE)"
            )
        if broker_raw.upper() != "BROKER_SL_NONE":
            broker_sl = _positive(broker_raw, "TRAIL_SL broker_sl")
            if broker_sl != new_sl:
                raise RiskPlanError(
                    "TRAIL_SL broker_sl must equal new_sl "
                    f"(got {broker_sl}, new_sl {new_sl})"
                )
    event_base = {
        "kind": kind,
        "occurred_at": _iso_utc(occurred_at or datetime.now(timezone.utc)),
        "actor": actor,
        "reason": reason,
        "journal_row_id": journal_row_id,
        "previous_event_id": plan.events[-1].event_id if plan.events else None,
        "payload": dict(payload),
    }
    event = PlanEvent(event_id=_canonical_hash(event_base), **event_base)
    if any(existing.event_id == event.event_id for existing in plan.events):
        raise RiskPlanError("duplicate event")
    return replace(plan, events=plan.events + (event,))


def _plan_tick(plan: RiskPlan) -> Decimal:
    raw = (plan.policy or {}).get("tick_size") if plan.policy else None
    return _positive(raw or "0.01", "tick_size")


def _event_active_sl(plan: RiskPlan) -> Decimal:
    current_sl = plan.levels.active_sl
    for existing in plan.events:
        if existing.kind == "TRAIL_SL":
            current_sl = _positive(existing.payload.get("new_sl"), "TRAIL_SL new_sl")
        elif existing.kind == "REBASE_SPLIT":
            current_sl = _positive(existing.payload.get("new_sl"), "REBASE_SPLIT new_sl")
    return current_sl


def _derived_levels(plan: RiskPlan) -> tuple[Decimal, Decimal, Decimal, int, bool]:
    """Active SL/TP and lot size from immutable core plus trail/rebase events."""
    active_sl = plan.levels.active_sl
    tp1 = plan.levels.tp1
    tp2 = plan.levels.tp2
    lot_shares = plan.fill.shares
    rebased = False
    for event in plan.events:
        if event.kind == "TRAIL_SL":
            try:
                new_sl = _positive(event.payload.get("new_sl"), "TRAIL_SL new_sl")
            except RiskPlanError:
                continue
            if new_sl < active_sl:
                continue
            active_sl = new_sl
        elif event.kind == "REBASE_SPLIT":
            try:
                active_sl = _positive(event.payload.get("new_sl"), "REBASE_SPLIT new_sl")
                tp1 = _positive(event.payload.get("new_tp1"), "REBASE_SPLIT new_tp1")
                tp2 = _positive(event.payload.get("new_tp2"), "REBASE_SPLIT new_tp2")
                shares = _positive(event.payload.get("new_shares"), "REBASE_SPLIT new_shares")
            except RiskPlanError:
                continue
            if shares != shares.to_integral_value():
                continue
            lot_shares = int(shares)
            rebased = True
    return active_sl, tp1, tp2, lot_shares, rebased


def apply_split_rebase(
    plan: RiskPlan,
    *,
    ratio,
    effective_date: str,
    actor: str,
    reason: str = "CORPORATE_ACTION_SPLIT",
    occurred_at: datetime | None = None,
) -> RiskPlan:
    """Append REBASE_SPLIT with scaled lot size and levels; does not mutate the core."""
    ratio_d = _positive(ratio, "REBASE_SPLIT ratio")
    date_s = str(effective_date or "").strip()
    if not date_s:
        raise RiskPlanError("REBASE_SPLIT effective_date is required")
    active_sl, tp1, tp2, lot_shares, _rebased = _derived_levels(plan)
    new_shares_dec = Decimal(lot_shares) * ratio_d
    if new_shares_dec != new_shares_dec.to_integral_value():
        raise RiskPlanError("REBASE_SPLIT new_shares must be whole shares")
    new_shares = int(new_shares_dec)
    if new_shares <= 0:
        raise RiskPlanError("REBASE_SPLIT new_shares: must be positive")
    tick = _plan_tick(plan)
    new_sl = _round_tick(active_sl / ratio_d, tick, ROUND_CEILING)
    new_tp1 = _round_long_target(tp1 / ratio_d, tick)
    new_tp2 = _round_long_target(tp2 / ratio_d, tick)
    if plan.policy_version == CHANDELIER_POLICY_VERSION:
        # TP1/TP2 are unused fixed-target placeholders; the active trail may
        # already sit above TP1 after a favourable run — do not require
        # new_sl < new_tp1.
        new_tp2 = new_tp1
        if new_sl <= 0 or new_tp1 <= 0 or new_tp2 != new_tp1:
            raise RiskPlanError("REBASE_SPLIT levels have invalid geometry")
    elif not (new_sl < new_tp1 < new_tp2):
        raise RiskPlanError("REBASE_SPLIT levels have invalid geometry")
    return append_plan_event(
        plan,
        kind="REBASE_SPLIT",
        actor=actor,
        reason=reason,
        payload={
            "ratio": str(ratio_d),
            "effective_date": date_s,
            "new_shares": new_shares,
            "new_sl": str(new_sl),
            "new_tp1": str(new_tp1),
            "new_tp2": str(new_tp2),
        },
        occurred_at=occurred_at,
    )


def planned_stop_risk(shares, risk_per_share) -> Decimal:
    """Dollar risk of a planned stop: shares × risk per share."""
    qty = _positive(shares, "shares")
    rps = _positive(risk_per_share, "risk_per_share")
    return qty * rps


def check_nav_gates(
    lots: Sequence[Mapping[str, object]],
    nav: Decimal,
) -> tuple[str, ...]:
    """Return NAV risk-gate issue codes; pure, no I/O."""
    nav_d = _positive(nav, "nav")
    book = Decimal("0")
    stress_total = Decimal("0")
    sector_risk: dict[str, Decimal] = {}
    lot_excess = False
    for lot in lots:
        risk = _decimal(lot.get("risk", 0), "lot.risk")
        if risk < 0:
            raise RiskPlanError("lot.risk: must be non-negative")
        stress = _decimal(lot.get("stress_gap", 0), "lot.stress_gap")
        if stress < 0:
            raise RiskPlanError("lot.stress_gap: must be non-negative")
        book += risk
        stress_total += stress
        if risk / nav_d > LOT_RISK_CAP:
            lot_excess = True
        sector = str(lot.get("sector") or "").strip()
        if sector:
            sector_risk[sector] = sector_risk.get(sector, Decimal("0")) + risk
    issues: list[str] = []
    if lot_excess:
        issues.append("LOT_RISK_EXCESS")
    if book / nav_d > BOOK_RISK_CAP:
        issues.append("BOOK_RISK_EXCESS")
    if any(value / nav_d > SECTOR_RISK_CAP for value in sector_risk.values()):
        issues.append("SECTOR_RISK_EXCESS")
    if stress_total / nav_d > STRESS_GAP_CAP:
        issues.append("STRESS_GAP_EXCESS")
    return tuple(issues)


def _attributed_sells(
    plan: RiskPlan,
    rows: Sequence[Mapping[str, str]],
    *,
    allow_legacy_fallback: bool,
) -> tuple[list[Mapping[str, str]], list[str]]:
    candidates: list[Mapping[str, str]] = []
    issues: list[str] = []
    ticker_sells = []
    explicit = []
    for row in rows:
        if str(row.get("Action") or "").strip().upper() != "SELL":
            continue
        if str(row.get("Status") or "").strip().upper() != "CLOSED":
            continue
        if str(row.get("Ticker") or "").strip().upper() != plan.fill.ticker:
            continue
        ticker_sells.append(row)
        notes = str(row.get("Notes") or "")
        linked = str(row.get("PlanRowID") or "").strip()
        if linked == plan.plan_id or f"{PLAN_ROW_TOKEN}{plan.plan_id}" in notes:
            explicit.append(row)
    if explicit:
        candidates = explicit
    elif ticker_sells and allow_legacy_fallback:
        candidates = ticker_sells
        issues.append("LEGACY_SELL_ATTRIBUTION")
    elif ticker_sells:
        issues.append("UNATTRIBUTED_SELL")
    return candidates, issues


def reconcile_plan(
    plan: RiskPlan,
    journal_rows: Sequence[Mapping[str, str]],
    *,
    allow_legacy_fallback: bool = False,
) -> PlanView:
    """Derive current state from confirmed, explicitly attributed journal SELLs."""
    issues = list(validate_plan(plan))
    sells, sell_issues = _attributed_sells(
        plan, journal_rows, allow_legacy_fallback=allow_legacy_fallback
    )
    issues.extend(sell_issues)
    sold = 0
    seen: set[str] = set()
    for row in sells:
        row_id = str(row.get("RowID") or "").strip()
        if not row_id or row_id in seen:
            issues.append("SELL_ROW_ID_INVALID")
            continue
        seen.add(row_id)
        try:
            qty = _positive(row.get("Shares"), "SELL Shares")
        except RiskPlanError:
            issues.append("SELL_SHARES_INVALID")
            continue
        if qty != qty.to_integral_value():
            issues.append("SELL_SHARES_FRACTIONAL")
            continue
        sold += int(qty)

    active_sl, tp1, tp2, lot_shares, rebased = _derived_levels(plan)
    cursor_sl = plan.levels.active_sl
    for event in plan.events:
        if event.kind == "TRAIL_SL":
            try:
                new_sl = _positive(event.payload.get("new_sl"), "TRAIL_SL new_sl")
            except RiskPlanError:
                issues.append("TRAIL_SL_INVALID")
                continue
            if new_sl < cursor_sl:
                issues.append("TRAIL_SL_LOWERED")
                continue
            cursor_sl = new_sl
        elif event.kind == "REBASE_SPLIT":
            try:
                cursor_sl = _positive(event.payload.get("new_sl"), "REBASE_SPLIT new_sl")
            except RiskPlanError:
                issues.append("REBASE_EVENT_INVALID")
    remaining = lot_shares - sold
    if remaining < 0:
        issues.append("OVERSELL")
        remaining = 0
    if plan.fill.shares > 0:
        tp1_shares = plan.levels.tp1_shares * lot_shares // plan.fill.shares
    else:
        tp1_shares = 0
    if sold == 0:
        state = "ACTIVE"
    elif remaining == 0:
        state = "CLOSED"
    elif sold == tp1_shares and tp1_shares > 0:
        state = "TP1_EXECUTED"
    elif plan.policy_version == LEGACY_POLICY_VERSION:
        state = "PARTIAL_LEGACY"
    else:
        state = "BLOCKED"
        issues.append("UNEXPECTED_PARTIAL_QUANTITY")
    blocking = [issue for issue in issues if issue != "LEGACY_SELL_ATTRIBUTION"]
    if blocking and state != "CLOSED":
        state = "BLOCKED"
    return PlanView(
        state=state,
        remaining_shares=remaining,
        active_sl=active_sl,
        issues=tuple(sorted(set(issues))),
        tp1=tp1,
        tp2=tp2,
        rebased=rebased,
    )


def validate_plan(plan: RiskPlan) -> tuple[str, ...]:
    issues: list[str] = []
    lv = plan.levels
    if plan.policy_version not in SUPPORTED_POLICY_VERSIONS:
        issues.append("POLICY_VERSION_UNSUPPORTED")
    if plan.plan_id != plan.fill.row_id:
        issues.append("PLAN_ID_ROW_ID_MISMATCH")
    if not _long_geometry_ok(lv.sl0, plan.fill.price, lv.tp1, lv.tp2, plan.policy_version):
        issues.append("LEVEL_GEOMETRY_INVALID")
    if lv.tp1_shares + lv.tp2_shares != plan.fill.shares:
        issues.append("SHARE_ALLOCATION_INVALID")
    event_ids: set[str] = set()
    previous: str | None = None
    event_active_sl = plan.levels.active_sl
    for event in plan.events:
        if event.event_id in event_ids:
            issues.append("DUPLICATE_EVENT")
        event_ids.add(event.event_id)
        event_doc = asdict(event)
        claimed = event_doc.pop("event_id")
        if _canonical_hash(event_doc) != claimed:
            issues.append("EVENT_HASH_INVALID")
        if event.previous_event_id != previous:
            issues.append("EVENT_CHAIN_INVALID")
        if not event.actor.strip() or not event.reason.strip():
            issues.append("EVENT_AUDIT_FIELDS_MISSING")
        if event.kind == "TRAIL_SL":
            try:
                old_sl = _positive(event.payload.get("old_sl"), "TRAIL_SL old_sl")
                new_sl = _positive(event.payload.get("new_sl"), "TRAIL_SL new_sl")
                if old_sl != event_active_sl or new_sl < old_sl:
                    issues.append("TRAIL_SL_CHAIN_INVALID")
                else:
                    event_active_sl = new_sl
            except RiskPlanError:
                issues.append("TRAIL_SL_INVALID")
        elif event.kind == "SELL_CONFIRMED":
            try:
                _positive(event.payload.get("shares"), "SELL_CONFIRMED shares")
            except RiskPlanError:
                issues.append("SELL_EVENT_INVALID")
            if not event.journal_row_id:
                issues.append("SELL_EVENT_JOURNAL_REF_MISSING")
        elif event.kind == "REBASE_SPLIT":
            try:
                _positive(event.payload.get("ratio"), "REBASE_SPLIT ratio")
                _positive(event.payload.get("new_shares"), "REBASE_SPLIT new_shares")
                _positive(event.payload.get("new_tp1"), "REBASE_SPLIT new_tp1")
                _positive(event.payload.get("new_tp2"), "REBASE_SPLIT new_tp2")
                event_active_sl = _positive(event.payload.get("new_sl"), "REBASE_SPLIT new_sl")
            except RiskPlanError:
                issues.append("REBASE_EVENT_INVALID")
            if not str(event.payload.get("effective_date") or "").strip():
                issues.append("REBASE_EVENT_INVALID")
        elif event.kind == "CLOSED" and not event.journal_row_id:
            issues.append("CLOSED_EVENT_JOURNAL_REF_MISSING")
        previous = event.event_id
    if not plan.events or plan.events[0].kind != "CREATED":
        issues.append("CREATED_EVENT_MISSING")
    if plan.policy_version == LEGACY_POLICY_VERSION:
        input_doc = {
            "fill": _fill_to_dict(plan.fill),
            "journal_levels": _levels_to_dict(plan.levels),
            "policy": LEGACY_POLICY_VERSION,
        }
    else:
        policy_doc = dict(plan.policy) if plan.policy else _policy_to_dict(RiskPolicy())
        input_doc = {
            "fill": _fill_to_dict(plan.fill),
            "atr_session": plan.atr_session,
            "atr14": str(plan.levels.atr14),
            "atr_source": plan.atr_source,
            "policy": policy_doc,
        }
    if _canonical_hash(input_doc) != plan.input_hash:
        issues.append("INPUT_HASH_INVALID")
    if _canonical_hash(_levels_to_dict(plan.levels)) != plan.calculation_hash:
        issues.append("CALCULATION_HASH_INVALID")
    if plan.policy_version == ZONE_POLICY_VERSION:
        for key in ("zone_mode", "zone_lo", "zone_hi", "atr_sl", "zone_sl", "zone_status", "merge"):
            if key not in plan.policy:
                issues.append("ZONE_POLICY_FIELDS_MISSING")
                break
        try:
            zone_lo = _positive(plan.policy.get("zone_lo"), "zone_lo")
            zone_hi = _positive(plan.policy.get("zone_hi"), "zone_hi")
            _positive(plan.policy.get("atr_sl"), "atr_sl")
            _positive(plan.policy.get("zone_sl"), "zone_sl")
            if zone_lo >= zone_hi or zone_lo >= plan.fill.price:
                issues.append("ZONE_POLICY_GEOMETRY_INVALID")
            if plan.policy.get("zone_status") != "OK":
                issues.append("ZONE_POLICY_STATUS_INVALID")
            if str(plan.policy.get("merge") or "") != "min":
                issues.append("ZONE_POLICY_MERGE_INVALID")
        except RiskPlanError:
            issues.append("ZONE_POLICY_FIELDS_INVALID")
    if plan.policy_version == CHANDELIER_POLICY_VERSION:
        try:
            _positive(plan.policy.get("trail_k"), "trail_k")
            if str(plan.policy.get("trail_anchor") or "") != "close":
                issues.append("TRAIL_ANCHOR_UNSUPPORTED")
            if str(plan.policy.get("tp2_mode") or "") != "unused":
                issues.append("CHANDELIER_TP2_MODE_INVALID")
            if lv.tp1 != lv.tp2:
                issues.append("CHANDELIER_TP2_PLACEHOLDER_INVALID")
        except RiskPlanError:
            issues.append("CHANDELIER_POLICY_FIELDS_INVALID")
    return tuple(sorted(set(issues)))


def _policy_to_dict(
    policy: RiskPolicy,
    *,
    extras: Mapping[str, str | int] | None = None,
) -> dict[str, str | int]:
    out: dict[str, str | int] = {
        "version": policy.version,
        "atr_period": policy.atr_period,
        "risk_atr_multiple": str(policy.risk_atr_multiple),
        "risk_max_atr_multiple": str(policy.risk_max_atr_multiple),
        "tp1_r_multiple": str(policy.tp1_r_multiple),
        "tp2_r_multiple": str(policy.tp2_r_multiple),
        "tp1_fraction": str(policy.tp1_fraction),
        "tick_size": str(policy.tick_size),
        "zone_window_bars": policy.zone_window_bars,
        "zone_alpha": str(policy.zone_alpha),
        "zone_rho": str(policy.zone_rho),
        "zone_beta_atr": str(policy.zone_beta_atr),
        "zone_kappa_atr": str(policy.zone_kappa_atr),
        "zone_merge": policy.zone_merge,
        "trail_k": str(policy.trail_k),
        "trail_anchor": policy.trail_anchor,
    }
    if extras:
        out.update(extras)
    return out


def _fill_to_dict(fill: JournalFill) -> dict:
    out = asdict(fill)
    out["price"] = str(fill.price)
    return out


def _levels_to_dict(levels: RiskLevels) -> dict:
    out = asdict(levels)
    for key in ("atr14", "risk_per_share", "sl0", "active_sl", "tp1", "tp2"):
        out[key] = str(out[key])
    return out


def plan_to_dict(plan: RiskPlan) -> dict:
    return {
        "plan_id": plan.plan_id,
        "policy_version": plan.policy_version,
        "fill": _fill_to_dict(plan.fill),
        "atr_session": plan.atr_session,
        "atr_source": plan.atr_source,
        "levels": _levels_to_dict(plan.levels),
        "input_hash": plan.input_hash,
        "calculation_hash": plan.calculation_hash,
        "events": [asdict(event) for event in plan.events],
        "policy": dict(plan.policy),
    }


def plan_from_dict(doc: Mapping[str, object]) -> RiskPlan:
    try:
        fill_doc = dict(doc["fill"])  # type: ignore[arg-type]
        fill_doc["price"] = _decimal(fill_doc["price"], "fill.price")
        level_doc = dict(doc["levels"])  # type: ignore[arg-type]
        for key in ("atr14", "risk_per_share", "sl0", "active_sl", "tp1", "tp2"):
            raw = level_doc[key]
            level_doc[key] = Decimal(str(raw))
            if not level_doc[key].is_finite():
                raise RiskPlanError(f"levels.{key}: non-finite")
        events = tuple(
            PlanEvent(**dict(event)) for event in doc.get("events", [])  # type: ignore[arg-type]
        )
        policy_raw = doc.get("policy") or {}
        if not isinstance(policy_raw, dict):
            policy_raw = {}
        return RiskPlan(
            plan_id=str(doc["plan_id"]),
            policy_version=str(doc["policy_version"]),
            fill=JournalFill(**fill_doc),
            atr_session=str(doc["atr_session"]),
            atr_source=str(doc["atr_source"]),
            levels=RiskLevels(**level_doc),
            input_hash=str(doc["input_hash"]),
            calculation_hash=str(doc["calculation_hash"]),
            events=events,
            policy=policy_raw,
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        if isinstance(exc, RiskPlanError):
            raise
        raise RiskPlanError(f"malformed risk plan: {exc}") from exc


def load_plan_store(path: str | Path) -> dict[str, RiskPlan]:
    source = Path(path)
    if not source.is_file():
        return {}
    try:
        doc = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RiskPlanError(f"risk-plan store unreadable: {exc}") from exc
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise RiskPlanError("risk-plan schema version unsupported")
    try:
        raw_plans = doc.get("plans") or {}
        if not isinstance(raw_plans, dict):
            raise RiskPlanError("risk-plan plans must be an object")
        plans = {key: plan_from_dict(value) for key, value in raw_plans.items()}
    except (AttributeError, TypeError, KeyError) as exc:
        raise RiskPlanError(f"malformed risk-plan store: {exc}") from exc
    for key, plan in plans.items():
        if key != plan.plan_id or validate_plan(plan):
            raise RiskPlanError(f"invalid risk plan: {key}")
    return plans


def _immutable_core(plan: RiskPlan) -> dict:
    doc = plan_to_dict(plan)
    doc.pop("events", None)
    return doc


def write_plan_store(
    path: str | Path,
    plans: Mapping[str, RiskPlan],
    *,
    existing: Mapping[str, RiskPlan] | None = None,
    allow_core_replace: frozenset[str] | set[str] | None = None,
) -> None:
    """Atomically write valid plans while enforcing append-only history.

    ``allow_core_replace`` is an explicit owner escape hatch for audited policy
    upgrades (e.g. atr-r-v2 -> atr-chandelier-v1). Keys listed there may replace
    immutable cores; all other keys keep the strict append-only rules.
    """
    destination = Path(path)
    prior = dict(existing) if existing is not None else load_plan_store(destination)
    replaceable = frozenset(allow_core_replace or ())
    for key, plan in plans.items():
        issues = validate_plan(plan)
        if key != plan.plan_id or issues:
            raise RiskPlanError(f"refusing invalid risk plan {key}: {','.join(issues)}")
        old = prior.get(key)
        if old and key not in replaceable:
            if _immutable_core(old) != _immutable_core(plan):
                raise RiskPlanError(f"immutable plan core changed: {key}")
            old_events = [asdict(event) for event in old.events]
            new_events = [asdict(event) for event in plan.events]
            if new_events[: len(old_events)] != old_events:
                raise RiskPlanError(f"event history rewrite: {key}")
    missing = set(prior) - set(plans)
    if missing:
        raise RiskPlanError("plan deletion is not allowed: " + ",".join(sorted(missing)))

    doc = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "plans": {key: plan_to_dict(plans[key]) for key in sorted(plans)},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, destination)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def proposed_plan_record(plan: RiskPlan, current_levels: Mapping[str, str]) -> dict:
    """Read-only migration artifact comparing journal and standardized levels."""
    return {
        "plan_id": plan.plan_id,
        "ticker": plan.fill.ticker,
        "currency": plan.fill.currency,
        "fill": str(plan.fill.price),
        "current_journal": dict(current_levels),
        "proposed": _levels_to_dict(plan.levels),
        "decision_required": ["GRANDFATHER_CURRENT", "ADOPT_NEW_POLICY"],
        "input_hash": plan.input_hash,
        "calculation_hash": plan.calculation_hash,
    }
