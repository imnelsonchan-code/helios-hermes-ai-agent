#!/usr/bin/env python3
"""Validated Yahoo daily OHLC evidence for the audited position watch.

Only ``YFinanceTransport`` imports yfinance.  Validation and ATR calculation
are pure and fixture-friendly so unit tests never require network access.
"""
from __future__ import annotations

import json
import math
import os
import hashlib
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence


class MarketDataError(ValueError):
    """Invalid or unavailable market evidence."""


def _decimal(value, field_name: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MarketDataError(f"{field_name}: invalid decimal") from exc
    if not out.is_finite() or out <= 0:
        raise MarketDataError(f"{field_name}: must be finite and positive")
    return out


def _round_up_tick(value: Decimal, tick: Decimal) -> Decimal:
    if tick <= 0:
        raise MarketDataError("tick: must be positive")
    return (value / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def _round_down_tick(value: Decimal, tick: Decimal) -> Decimal:
    if tick <= 0:
        raise MarketDataError("tick: must be positive")
    return (value / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


@dataclass(frozen=True)
class DailyBar:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None


@dataclass(frozen=True)
class SplitEvent:
    session: date
    ratio: Decimal


@dataclass(frozen=True)
class RawMarketResponse:
    requested_symbol: str
    returned_symbol: str
    currency_code: str
    exchange: str | None
    quote_timestamp: str | None
    bars: tuple[DailyBar, ...]
    splits: tuple[SplitEvent, ...] = ()
    raw_metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ZoneParams:
    window_bars: int = 20
    alpha: Decimal = Decimal("0.10")
    rho: Decimal = Decimal("0.40")
    beta: Decimal = Decimal("2.0")
    kappa: Decimal = Decimal("0.5")


@dataclass(frozen=True)
class ZoneEvidence:
    status: str
    reason_code: str
    mode: str | None
    zone_lo: Decimal | None
    zone_hi: Decimal | None
    through_session: date
    window_start: date | None = None
    window_end: date | None = None
    bars_used: int = 0
    bin_size: Decimal | None = None
    mass: Decimal | None = None
    total_mass: Decimal | None = None
    width: Decimal | None = None


@dataclass(frozen=True)
class _ZoneCandidate:
    zone_lo: Decimal
    zone_hi: Decimal
    mass: Decimal
    width: Decimal


class MarketTransport(Protocol):
    def daily_history(self, symbol: str, start: date, end: date) -> RawMarketResponse:
        """Return unadjusted daily bars and corporate actions."""


@dataclass(frozen=True)
class MarketRequest:
    symbol: str
    expected_session: date
    expected_currency: str
    plan_created_session: date | None = None
    tm_close: Decimal | None = None
    active_sl: Decimal | None = None
    expected_exchange: str | None = None


@dataclass(frozen=True)
class MarketEvidence:
    symbol: str
    session: date
    currency: str | None
    bar: DailyBar | None
    retrieved_at: str
    valid_for_breach: bool
    issues: tuple[str, ...]
    cache_path: str | None = None
    gap_through_sl: bool = False
    # Full normalized series from the fetch (holding period + ATR runway).
    # Callers that only need the session bar may ignore this; default () keeps
    # existing fixtures/constructors compatible.
    bars: tuple[DailyBar, ...] = ()
    splits: tuple[SplitEvent, ...] = ()


# Observational flags recorded on an otherwise valid bar; they do not by
# themselves suppress SL/TP comparison.
_NON_BLOCKING_ISSUES = frozenset({"GAP_THROUGH_SL"})
_ATR_LOOKBACK_CALENDAR_DAYS = 400


def is_weekend(session: date) -> bool:
    return session.weekday() >= 5


def session_expected(
    session: date, holidays: set[date] | frozenset[date] | None = None
) -> bool:
    """True when ``session`` is a weekday that is not in ``holidays``."""
    if is_weekend(session):
        return False
    if holidays and session in holidays:
        return False
    return True


def previous_session(
    session: date, holidays: set[date] | frozenset[date] | None = None
) -> date:
    """Prior expected session, skipping weekends and injected holidays."""
    candidate = session - timedelta(days=1)
    for _ in range(30):
        if session_expected(candidate, holidays):
            return candidate
        candidate -= timedelta(days=1)
    raise MarketDataError("no previous session within 30 days")


def _history_start(request: MarketRequest) -> date:
    origin = request.expected_session
    if request.plan_created_session is not None and request.plan_created_session < origin:
        origin = request.plan_created_session
    return origin - timedelta(days=_ATR_LOOKBACK_CALENDAR_DAYS)


def _retrieved_at(retrieved: datetime) -> str:
    aware = (
        retrieved.astimezone(timezone.utc)
        if retrieved.tzinfo
        else retrieved.replace(tzinfo=timezone.utc)
    )
    return aware.isoformat().replace("+00:00", "Z")


def validate_bar(bar: DailyBar) -> tuple[str, ...]:
    issues: list[str] = []
    vals = (bar.open, bar.high, bar.low, bar.close)
    if any(not value.is_finite() or value <= 0 for value in vals):
        issues.append("PRICE_NONPOSITIVE")
    if bar.low > bar.high:
        issues.append("OHLC_LOW_ABOVE_HIGH")
    if not (bar.low <= bar.open <= bar.high):
        issues.append("OHLC_OPEN_OUTSIDE_RANGE")
    if not (bar.low <= bar.close <= bar.high):
        issues.append("OHLC_CLOSE_OUTSIDE_RANGE")
    return tuple(issues)


def _skipped_invalid_ohlc_count(raw_metadata: Mapping[str, object] | None) -> int:
    if not raw_metadata:
        return 0
    raw = raw_metadata.get("_skipped_invalid_ohlc", 0)
    try:
        count = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return count if count > 0 else 0


def _missing_session_diagnostics(
    bars: Sequence[DailyBar],
    *,
    expected_session: date,
    raw_metadata: Mapping[str, object] | None,
) -> tuple[str, ...]:
    """Extra audit clues when the expected session bar is absent (still fail-closed)."""
    extra: list[str] = []
    skipped = _skipped_invalid_ohlc_count(raw_metadata)
    if skipped:
        extra.append(f"SKIPPED_INVALID_OHLC:{skipped}")
    skipped_sessions = ()
    if raw_metadata:
        raw_sessions = raw_metadata.get("_skipped_invalid_ohlc_sessions")
        if isinstance(raw_sessions, (list, tuple)):
            skipped_sessions = tuple(str(item) for item in raw_sessions)
    if expected_session.isoformat() in skipped_sessions:
        extra.append("INVALID_OHLC_FOR_EXPECTED_SESSION")
    if bars:
        last = max(bar.session for bar in bars)
        extra.append(f"LAST_AVAILABLE_SESSION:{last.isoformat()}")
    else:
        extra.append("LAST_AVAILABLE_SESSION:none")
    return tuple(extra)


def _zone_rejected(
    through_session: date,
    reason_code: str,
    *,
    mode: str | None = None,
    window: Sequence[DailyBar] = (),
    bin_size: Decimal | None = None,
) -> ZoneEvidence:
    return ZoneEvidence(
        status="REJECTED",
        reason_code=reason_code,
        mode=mode,
        zone_lo=None,
        zone_hi=None,
        through_session=through_session,
        window_start=window[0].session if window else None,
        window_end=window[-1].session if window else None,
        bars_used=len(window),
        bin_size=bin_size,
    )


def _windowed_bars(
    bars: Sequence[DailyBar],
    *,
    through_session: date,
    window_bars: int,
) -> tuple[DailyBar, ...]:
    ordered = sorted((bar for bar in bars if bar.session <= through_session), key=lambda item: item.session)
    sessions = [bar.session for bar in ordered]
    if len(set(sessions)) != len(sessions):
        raise MarketDataError("duplicate market sessions")
    if window_bars <= 0:
        raise MarketDataError("zone window must be positive")
    return tuple(ordered[-window_bars:])


def _volume_usable(window: Sequence[DailyBar]) -> bool:
    if not window:
        return False
    total = 0
    for bar in window:
        volume = bar.volume
        if volume is None or volume <= 0:
            return False
        total += volume
    return total > 0


def _bin_bounds(window: Sequence[DailyBar], bin_size: Decimal) -> tuple[Decimal, int]:
    lowest = min(bar.low for bar in window)
    highest = max(bar.high for bar in window)
    base = _round_down_tick(lowest, bin_size)
    top = _round_up_tick(highest, bin_size)
    count = int(((top - base) / bin_size).to_integral_value(rounding=ROUND_CEILING))
    return base, max(count, 1)


def _bar_bin_range(bar: DailyBar, base: Decimal, bin_size: Decimal) -> tuple[int, int]:
    start = int(((bar.low - base) / bin_size).to_integral_value(rounding=ROUND_FLOOR))
    end = int(((bar.high - base) / bin_size).to_integral_value(rounding=ROUND_CEILING)) - 1
    if end < start:
        end = start
    return start, end


def _profile_weights(
    window: Sequence[DailyBar],
    *,
    base: Decimal,
    bin_size: Decimal,
    mode: str,
    bin_count: int,
) -> list[Decimal]:
    weights = [Decimal("0")] * bin_count
    for bar in window:
        start, end = _bar_bin_range(bar, base, bin_size)
        start = max(start, 0)
        end = min(end, bin_count - 1)
        if end < start:
            continue
        touched = end - start + 1
        increment = Decimal(bar.volume or 0) / Decimal(touched) if mode == "VPDC" else Decimal("1")
        for idx in range(start, end + 1):
            weights[idx] += increment
    return weights


def _select_zone_candidate(candidates: Sequence[_ZoneCandidate]) -> _ZoneCandidate:
    if not candidates:
        raise MarketDataError("no zone candidates")
    # mass DESC, width ASC, zone_lo ASC for stable ordering — but equal
    # mass+width is ambiguous even when zone_lo differs (do not silently pick).
    ranked = sorted(candidates, key=lambda item: (-item.mass, item.width, item.zone_lo))
    if len(ranked) > 1:
        first = ranked[0]
        second = ranked[1]
        if first.mass == second.mass and first.width == second.width:
            raise MarketDataError("ambiguous best cluster")
    return ranked[0]


def congestion_zone(
    bars: Sequence[DailyBar],
    *,
    through_session: date,
    atr14: Decimal,
    tick: Decimal,
    params: ZoneParams | None = None,
) -> ZoneEvidence:
    """Return a deterministic congestion zone ending at ``through_session``."""
    cfg = params or ZoneParams()
    atr = _decimal(atr14, "ATR14")
    tick_size = _decimal(tick, "tick")
    window = _windowed_bars(bars, through_session=through_session, window_bars=cfg.window_bars)
    if len(window) < cfg.window_bars:
        return _zone_rejected(through_session, "INSUFFICIENT_WINDOW", window=window)
    for bar in window:
        if validate_bar(bar):
            return _zone_rejected(through_session, "INVALID_BAR", window=window)

    bin_size = max(tick_size, _round_up_tick(atr * cfg.alpha, tick_size))
    mode = "VPDC" if _volume_usable(window) else "OTCC"
    base, bin_count = _bin_bounds(window, bin_size)
    weights = _profile_weights(window, base=base, bin_size=bin_size, mode=mode, bin_count=bin_count)
    total_mass = sum(weights, Decimal("0"))
    if total_mass <= 0:
        return _zone_rejected(through_session, "NO_CLUSTER", mode=mode, window=window, bin_size=bin_size)

    max_width = atr * cfg.beta
    min_mass = total_mass * cfg.rho
    max_bins = max(1, int((max_width / bin_size).to_integral_value(rounding=ROUND_FLOOR)))
    prefix = [Decimal("0")]
    for weight in weights:
        prefix.append(prefix[-1] + weight)

    candidates: list[_ZoneCandidate] = []
    for start in range(bin_count):
        for end in range(start, min(bin_count, start + max_bins)):
            width = Decimal(end - start + 1) * bin_size
            if width > max_width:
                break
            mass = prefix[end + 1] - prefix[start]
            if mass < min_mass:
                continue
            drop_left = prefix[end + 1] - prefix[start + 1] if start < end else Decimal("0")
            drop_right = prefix[end] - prefix[start] if start < end else Decimal("0")
            if start < end and (drop_left >= min_mass or drop_right >= min_mass):
                continue
            zone_lo = base + Decimal(start) * bin_size
            zone_hi = base + Decimal(end + 1) * bin_size
            candidates.append(
                _ZoneCandidate(zone_lo=zone_lo, zone_hi=zone_hi, mass=mass, width=width)
            )
    if not candidates:
        return _zone_rejected(through_session, "NO_CLUSTER", mode=mode, window=window, bin_size=bin_size)
    try:
        best = _select_zone_candidate(candidates)
    except MarketDataError:
        return _zone_rejected(
            through_session,
            "AMBIGUOUS_CLUSTER",
            mode=mode,
            window=window,
            bin_size=bin_size,
        )
    return ZoneEvidence(
        status="OK",
        reason_code="OK",
        mode=mode,
        zone_lo=best.zone_lo,
        zone_hi=best.zone_hi,
        through_session=through_session,
        window_start=window[0].session,
        window_end=window[-1].session,
        bars_used=len(window),
        bin_size=bin_size,
        mass=best.mass,
        total_mass=total_mass,
        width=best.width,
    )


def normalize_currency(currency_code: str) -> tuple[str, Decimal]:
    """Return canonical currency and multiplier into its major unit."""
    raw = str(currency_code or "").strip()
    if raw == "USD":
        return "USD", Decimal("1")
    if raw == "GBP":
        return "GBP", Decimal("1")
    if raw in {"GBp", "GBX", "GBPENCE", "GB PENCE"}:
        return "GBP", Decimal("0.01")
    raise MarketDataError(f"unsupported or ambiguous currency: {raw or 'missing'}")


def normalize_response(
    response: RawMarketResponse, expected_currency: str
) -> tuple[tuple[DailyBar, ...], str, tuple[str, ...]]:
    issues: list[str] = []
    try:
        currency, multiplier = normalize_currency(response.currency_code)
    except MarketDataError:
        return (), "", ("CURRENCY_AMBIGUOUS",)
    if currency != expected_currency:
        issues.append("CURRENCY_MISMATCH")
    bars = tuple(
        DailyBar(
            session=bar.session,
            open=bar.open * multiplier,
            high=bar.high * multiplier,
            low=bar.low * multiplier,
            close=bar.close * multiplier,
            volume=bar.volume,
        )
        for bar in response.bars
    )
    return bars, currency, tuple(issues)


def wilder_atr(
    bars: Sequence[DailyBar], *, through_session: date, period: int = 14
) -> Decimal:
    """Calculate exact Wilder ATR from ordered, unadjusted daily bars."""
    if period <= 0:
        raise MarketDataError("ATR period must be positive")
    ordered = sorted((bar for bar in bars if bar.session <= through_session), key=lambda b: b.session)
    sessions = [bar.session for bar in ordered]
    if len(set(sessions)) != len(sessions):
        raise MarketDataError("duplicate market sessions")
    if not ordered or ordered[-1].session != through_session:
        raise MarketDataError("ATR through-session missing")
    for bar in ordered:
        issues = validate_bar(bar)
        if issues:
            raise MarketDataError("invalid ATR bar: " + ",".join(issues))
    if len(ordered) < period + 1:
        raise MarketDataError(f"ATR requires at least {period + 1} bars")

    true_ranges: list[Decimal] = []
    for previous, current in zip(ordered, ordered[1:]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    atr = sum(true_ranges[:period], Decimal("0")) / Decimal(period)
    for tr in true_ranges[period:]:
        atr = (atr * Decimal(period - 1) + tr) / Decimal(period)
    return atr


def highest_close(
    bars: Sequence[DailyBar],
    *,
    from_session: date,
    through_session: date,
) -> Decimal:
    """Max daily close on ``[from_session, through_session]`` (inclusive)."""
    if through_session < from_session:
        raise MarketDataError("highest_close window inverted")
    window = [
        bar
        for bar in bars
        if from_session <= bar.session <= through_session
    ]
    if not window:
        raise MarketDataError("highest_close window empty")
    if not any(bar.session == through_session for bar in window):
        raise MarketDataError("highest_close through-session missing")
    for bar in window:
        issues = validate_bar(bar)
        if issues:
            raise MarketDataError("invalid highest_close bar: " + ",".join(issues))
    return max(bar.close for bar in window)


def chandelier_raw(
    bars: Sequence[DailyBar],
    *,
    from_session: date,
    through_session: date,
    trail_k: Decimal,
    atr_period: int = 14,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return ``(highest_close, atr, highest_close − k×ATR)`` as Decimals."""
    k = _decimal(trail_k, "trail_k")
    if k <= 0:
        raise MarketDataError("trail_k: must be positive")
    hc = highest_close(
        bars, from_session=from_session, through_session=through_session
    )
    atr = wilder_atr(bars, through_session=through_session, period=atr_period)
    return hc, atr, hc - k * atr


def unrebased_split_in_window(
    splits: Sequence[SplitEvent],
    *,
    plan_created_session: date | None,
    through_session: date,
) -> bool:
    """True when a non-1 split falls after plan creation through ``through_session``."""
    if plan_created_session is None:
        return False
    return any(
        split.session > plan_created_session
        and split.session <= through_session
        and split.ratio != Decimal("1")
        for split in splits
    )


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class MarketCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def write(
        self,
        request: MarketRequest,
        response: RawMarketResponse,
        evidence: MarketEvidence,
    ) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        safe_symbol = "".join(ch if ch.isalnum() or ch in ".-" else "_" for ch in request.symbol)
        destination = self.root / f"{request.expected_session.isoformat()}-{safe_symbol}.json"
        doc = {
            "schema_version": "1",
            "request": _json_safe(asdict(request)),
            "response": _json_safe(asdict(response)),
            "evidence": _json_safe(asdict(evidence)),
        }
        encoded = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()[:16]
        destination = self.root / (
            f"{request.expected_session.isoformat()}-{safe_symbol}-{digest}.json"
        )
        if destination.is_file():
            return str(destination)
        fd, tmp_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, sort_keys=True)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            try:
                os.link(tmp_name, destination)
            except FileExistsError:
                pass
            os.unlink(tmp_name)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return str(destination)


class YahooMarketData:
    def __init__(
        self,
        transport: MarketTransport,
        *,
        clock: Callable[[], datetime] | None = None,
        cache: MarketCache | None = None,
        tm_tolerance: Decimal = Decimal("0.01"),
        holidays: frozenset[date] | None = None,
    ):
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.cache = cache
        self.tm_tolerance = tm_tolerance
        self.holidays = holidays if holidays is not None else frozenset()

    def get_validated_evidence(self, request: MarketRequest) -> MarketEvidence:
        retrieved = self.clock()
        retrieved_at = _retrieved_at(retrieved)
        if not session_expected(request.expected_session, self.holidays):
            return MarketEvidence(
                symbol=request.symbol,
                session=request.expected_session,
                currency=None,
                bar=None,
                retrieved_at=retrieved_at,
                valid_for_breach=False,
                issues=("EXCHANGE_CLOSED",),
            )

        issues: list[str] = []
        response: RawMarketResponse | None = None
        bar: DailyBar | None = None
        series: tuple[DailyBar, ...] = ()
        splits: tuple[SplitEvent, ...] = ()
        currency: str | None = None
        gap_through_sl = False
        try:
            response = self.transport.daily_history(
                request.symbol,
                _history_start(request),
                request.expected_session + timedelta(days=1),
            )
            if response.requested_symbol.upper() != request.symbol.upper():
                issues.append("REQUESTED_SYMBOL_MISMATCH")
            if response.returned_symbol.upper() != request.symbol.upper():
                issues.append("RETURNED_SYMBOL_MISMATCH")
            expected_exchange = (request.expected_exchange or "").strip()
            actual_exchange = (response.exchange or "").strip()
            if (
                expected_exchange
                and actual_exchange
                and expected_exchange.casefold() != actual_exchange.casefold()
            ):
                issues.append("EXCHANGE_MISMATCH")
            if not response.quote_timestamp:
                issues.append("QUOTE_TIMESTAMP_MISSING")
            else:
                try:
                    quote_time = datetime.fromisoformat(
                        response.quote_timestamp.replace("Z", "+00:00")
                    )
                    if quote_time.tzinfo is None:
                        quote_time = quote_time.replace(tzinfo=timezone.utc)
                    retrieved_utc = (
                        retrieved.astimezone(timezone.utc)
                        if retrieved.tzinfo
                        else retrieved.replace(tzinfo=timezone.utc)
                    )
                    if quote_time > retrieved_utc + timedelta(minutes=5):
                        issues.append("QUOTE_TIMESTAMP_FUTURE")
                    if quote_time.date() < request.expected_session:
                        issues.append("QUOTE_TIMESTAMP_STALE")
                except ValueError:
                    issues.append("QUOTE_TIMESTAMP_INVALID")
            bars, currency_value, currency_issues = normalize_response(
                response, request.expected_currency
            )
            series = bars
            splits = tuple(response.splits)
            currency = currency_value or None
            issues.extend(currency_issues)
            matches = [item for item in bars if item.session == request.expected_session]
            if len(matches) != 1:
                issues.append("EXPECTED_SESSION_MISSING")
                issues.extend(
                    _missing_session_diagnostics(
                        bars,
                        expected_session=request.expected_session,
                        raw_metadata=response.raw_metadata,
                    )
                )
            else:
                bar = matches[0]
                issues.extend(validate_bar(bar))
            if request.plan_created_session is not None:
                if unrebased_split_in_window(
                    response.splits,
                    plan_created_session=request.plan_created_session,
                    through_session=request.expected_session,
                ):
                    issues.append("UNREBASED_SPLIT")
            if bar is not None and request.tm_close is not None and request.tm_close > 0:
                mismatch = abs(bar.close - request.tm_close) / request.tm_close
                if mismatch > self.tm_tolerance:
                    issues.append("PRICE_MISMATCH")
            if bar is not None and request.active_sl is not None:
                if bar.open <= request.active_sl:
                    issues.append("GAP_THROUGH_SL")
                    gap_through_sl = True
        except Exception as exc:
            issues.append("MARKET_FETCH_FAILED:" + type(exc).__name__)

        blocking = [item for item in issues if item not in _NON_BLOCKING_ISSUES]
        evidence = MarketEvidence(
            symbol=request.symbol,
            session=request.expected_session,
            currency=currency,
            bar=bar,
            retrieved_at=retrieved_at,
            valid_for_breach=bar is not None and not blocking,
            issues=tuple(sorted(set(issues))),
            gap_through_sl=gap_through_sl,
            bars=series,
            splits=splits,
        )
        if self.cache is not None and response is not None:
            try:
                cache_path = self.cache.write(request, response, evidence)
                evidence = replace(evidence, cache_path=cache_path)
            except OSError:
                evidence = replace(
                    evidence,
                    valid_for_breach=False,
                    issues=tuple(sorted(set(evidence.issues + ("CACHE_WRITE_FAILED",)))),
                )
        return evidence


class YFinanceTransport:
    """Thin optional-dependency boundary around yfinance."""

    def daily_history(self, symbol: str, start: date, end: date) -> RawMarketResponse:
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:
            raise MarketDataError("yfinance is not installed") from exc

        ticker = yf.Ticker(symbol)
        frame = ticker.history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=False,
        )
        if frame is None or frame.empty:
            raise MarketDataError("Yahoo returned no daily history")
        fast = {}
        try:
            fast = dict(ticker.fast_info)
        except Exception:
            fast = {}
        metadata = {}
        try:
            metadata = dict(ticker.history_metadata or {})
        except Exception:
            metadata = {}
        currency = str(fast.get("currency") or metadata.get("currency") or "")
        returned_symbol = str(
            fast.get("symbol") or metadata.get("symbol") or metadata.get("chartPreviousClose") and symbol or symbol
        )
        bars: list[DailyBar] = []
        splits: list[SplitEvent] = []
        skipped_invalid_ohlc = 0
        skipped_invalid_ohlc_sessions: list[str] = []
        for index, row in frame.iterrows():
            session = index.date()
            volume_raw = row.get("Volume")
            volume = None
            try:
                if volume_raw is not None and math.isfinite(float(volume_raw)):
                    volume = int(volume_raw)
            except (TypeError, ValueError, OverflowError):
                volume = None
            try:
                bars.append(
                    DailyBar(
                        session=session,
                        open=_decimal(row["Open"], "Open"),
                        high=_decimal(row["High"], "High"),
                        low=_decimal(row["Low"], "Low"),
                        close=_decimal(row["Close"], "Close"),
                        volume=volume,
                    )
                )
            except MarketDataError:
                skipped_invalid_ohlc += 1
                skipped_invalid_ohlc_sessions.append(session.isoformat())
                continue
            split_value = row.get("Stock Splits", 0)
            try:
                split = Decimal(str(split_value))
            except InvalidOperation:
                split = Decimal("0")
            if split.is_finite() and split not in (Decimal("0"), Decimal("1")):
                splits.append(SplitEvent(session, split))
        quote_ts = metadata.get("regularMarketTime")
        if isinstance(quote_ts, (int, float)):
            quote_ts = datetime.fromtimestamp(quote_ts, timezone.utc).isoformat()
        metadata["_skipped_invalid_ohlc"] = skipped_invalid_ohlc
        metadata["_skipped_invalid_ohlc_sessions"] = skipped_invalid_ohlc_sessions
        return RawMarketResponse(
            requested_symbol=symbol,
            returned_symbol=returned_symbol,
            currency_code=currency,
            exchange=str(fast.get("exchange") or metadata.get("exchangeName") or "") or None,
            quote_timestamp=str(quote_ts) if quote_ts else None,
            bars=tuple(bars),
            splits=tuple(splits),
            raw_metadata=metadata,
        )
