#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from market_data import (  # noqa: E402
    DailyBar,
    MarketDataError,
    ZoneEvidence,
    _ZoneCandidate,
    _select_zone_candidate,
    congestion_zone,
)
from risk_plan import RiskPlanError, calculate_levels_with_zone, parse_journal_fill  # noqa: E402


def _bar(session: date, low: str, high: str, *, volume: int | None = 100) -> DailyBar:
    low_d = Decimal(low)
    high_d = Decimal(high)
    close = (low_d + high_d) / Decimal("2")
    return DailyBar(
        session=session,
        open=close,
        high=high_d,
        low=low_d,
        close=close,
        volume=volume,
    )


def _buy_fill(price_usd: str = "100"):
    return parse_journal_fill(
        {
            "Date": "2026-09-08",
            "Ticker": "TEST",
            "Action": "BUY",
            "Shares": "50",
            "Price": "75.00",
            "Price USD": price_usd,
            "Total USD": str(Decimal(price_usd) * Decimal("50")),
            "SL": "",
            "TP1": "",
            "TP2": "",
            "Status": "OPEN",
            "Notes": "",
            "RowID": "zone-entry",
        }
    )


class CongestionZoneTests(unittest.TestCase):
    def test_vpdc_prefers_volume_cluster(self):
        start = date(2026, 8, 1)
        bars = tuple(
            [_bar(start + timedelta(days=i), "100.0", "100.1", volume=100) for i in range(12)]
            + [_bar(start + timedelta(days=12 + i), "101.0", "101.1", volume=10) for i in range(8)]
        )
        zone = congestion_zone(
            bars,
            through_session=bars[-1].session,
            atr14=Decimal("1"),
            tick=Decimal("0.1"),
        )
        self.assertEqual(zone.status, "OK")
        self.assertEqual(zone.mode, "VPDC")
        self.assertEqual(zone.zone_lo, Decimal("100.0"))
        self.assertEqual(zone.zone_hi, Decimal("100.1"))
        self.assertEqual(zone.bin_size, Decimal("0.1"))

    def test_otcc_fallback_when_volume_unusable(self):
        start = date(2026, 8, 1)
        bars = tuple(
            [_bar(start + timedelta(days=i), "100.0", "100.1", volume=None) for i in range(11)]
            + [_bar(start + timedelta(days=11 + i), "101.0", "101.1", volume=None) for i in range(9)]
        )
        zone = congestion_zone(
            bars,
            through_session=bars[-1].session,
            atr14=Decimal("1"),
            tick=Decimal("0.1"),
        )
        self.assertEqual(zone.status, "OK")
        self.assertEqual(zone.mode, "OTCC")
        self.assertEqual(zone.zone_lo, Decimal("100.0"))
        self.assertEqual(zone.zone_hi, Decimal("100.1"))

    def test_ambiguous_tie_fails_closed(self):
        with self.assertRaises(MarketDataError):
            _select_zone_candidate(
                [
                    _ZoneCandidate(
                        zone_lo=Decimal("100.0"),
                        zone_hi=Decimal("100.1"),
                        mass=Decimal("10"),
                        width=Decimal("0.1"),
                    ),
                    _ZoneCandidate(
                        zone_lo=Decimal("110.0"),
                        zone_hi=Decimal("110.1"),
                        mass=Decimal("10"),
                        width=Decimal("0.1"),
                    ),
                ]
            )

    def test_min_merge_keeps_atr_stop_when_zone_is_tighter(self):
        fill = _buy_fill("100")
        zone = ZoneEvidence(
            status="OK",
            reason_code="OK",
            mode="VPDC",
            zone_lo=Decimal("91"),
            zone_hi=Decimal("92"),
            through_session=date(2026, 9, 7),
            window_start=date(2026, 8, 11),
            window_end=date(2026, 9, 7),
            bars_used=20,
            bin_size=Decimal("0.1"),
            mass=Decimal("1000"),
            total_mass=Decimal("2000"),
            width=Decimal("1.0"),
        )
        levels = calculate_levels_with_zone(fill, Decimal("10"), zone)
        self.assertEqual(levels.sl0, Decimal("85.00"))
        self.assertEqual(levels.risk_per_share, Decimal("15.00"))
        self.assertEqual(levels.tp1, Decimal("130.00"))
        self.assertEqual(levels.tp2, Decimal("160.00"))

    def test_r_max_rejects_overwide_zone(self):
        fill = _buy_fill("100")
        zone = ZoneEvidence(
            status="OK",
            reason_code="OK",
            mode="VPDC",
            zone_lo=Decimal("70"),
            zone_hi=Decimal("72"),
            through_session=date(2026, 9, 7),
            window_start=date(2026, 8, 11),
            window_end=date(2026, 9, 7),
            bars_used=20,
            bin_size=Decimal("0.1"),
            mass=Decimal("1000"),
            total_mass=Decimal("2000"),
            width=Decimal("2.0"),
        )
        with self.assertRaises(RiskPlanError):
            calculate_levels_with_zone(fill, Decimal("10"), zone)

    def test_googl_like_bin_rounding(self):
        from market_data import ZoneParams, _round_up_tick

        atr = Decimal("8.65")
        tick = Decimal("0.01")
        params = ZoneParams()
        self.assertEqual(
            max(tick, _round_up_tick(atr * params.alpha, tick)),
            Decimal("0.87"),
        )
        start = date(2026, 8, 1)
        bars = tuple(
            _bar(start + timedelta(days=i), "330.00", "330.50", volume=1000) for i in range(20)
        )
        zone = congestion_zone(
            bars,
            through_session=bars[-1].session,
            atr14=atr,
            tick=tick,
        )
        self.assertEqual(zone.status, "OK")
        self.assertEqual(zone.bin_size, Decimal("0.87"))
        self.assertLessEqual(zone.zone_lo, Decimal("330.00"))
        self.assertGreater(zone.zone_hi, Decimal("330.00"))


if __name__ == "__main__":
    unittest.main()
