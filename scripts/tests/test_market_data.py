#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST_DIR))

from market_data import (  # noqa: E402
    DailyBar,
    MarketCache,
    MarketDataError,
    MarketRequest,
    RawMarketResponse,
    SplitEvent,
    YahooMarketData,
    is_weekend,
    normalize_currency,
    previous_session,
    session_expected,
    wilder_atr,
)


class FixtureTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def daily_history(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        return self.response


class WindowTransport:
    """Fixture transport that drops bars/splits outside the requested window."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def daily_history(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        return RawMarketResponse(
            requested_symbol=self.response.requested_symbol,
            returned_symbol=self.response.returned_symbol,
            currency_code=self.response.currency_code,
            exchange=self.response.exchange,
            quote_timestamp=self.response.quote_timestamp,
            bars=tuple(
                bar for bar in self.response.bars if start <= bar.session < end
            ),
            splits=tuple(
                split
                for split in self.response.splits
                if start <= split.session < end
            ),
            raw_metadata=self.response.raw_metadata,
        )


class BoomTransport:
    def daily_history(self, symbol, start, end):
        raise RuntimeError("network should not be used")


def _bar(session, close="100", high="101", low="99", open_="100"):
    return DailyBar(
        session=session,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1000,
    )


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.session = date(2026, 9, 8)
        self.response = RawMarketResponse(
            requested_symbol="BETA",
            returned_symbol="BETA",
            currency_code="USD",
            exchange="NYQ",
            quote_timestamp="2026-09-08T20:00:00Z",
            bars=(_bar(self.session, close="400.84", high="405", low="395", open_="398"),),
        )

    def test_wilder_atr_constant_true_range(self):
        start = date(2026, 8, 1)
        bars = tuple(_bar(start + timedelta(days=i)) for i in range(15))
        self.assertEqual(wilder_atr(bars, through_session=bars[-1].session), Decimal("2"))

    def test_wilder_atr_requires_through_session(self):
        with self.assertRaises(MarketDataError):
            wilder_atr((_bar(self.session),), through_session=self.session)

    def test_gbpence_normalizes_to_gbp(self):
        self.assertEqual(normalize_currency("GBp"), ("GBP", Decimal("0.01")))

    def test_valid_evidence_and_cache(self):
        with tempfile.TemporaryDirectory() as td:
            market = YahooMarketData(
                FixtureTransport(self.response),
                clock=lambda: datetime(2026, 9, 8, 23, tzinfo=timezone.utc),
                cache=MarketCache(td),
            )
            evidence = market.get_validated_evidence(
                MarketRequest("BETA", self.session, "USD", tm_close=Decimal("400.84"))
            )
            self.assertTrue(evidence.valid_for_breach)
            self.assertEqual(evidence.bar.close, Decimal("400.84"))
            self.assertEqual(len(evidence.bars), 1)
            self.assertEqual(evidence.bars[0].close, Decimal("400.84"))
            self.assertTrue(Path(evidence.cache_path).is_file())

    def test_highest_close_and_chandelier_raw(self):
        from market_data import chandelier_raw, highest_close

        start = date(2026, 8, 1)
        bars = tuple(
            _bar(start + timedelta(days=i), close=str(100 + i), high=str(101 + i), low="99")
            for i in range(20)
        )
        through = bars[-1].session
        self.assertEqual(
            highest_close(bars, from_session=bars[5].session, through_session=through),
            Decimal("119"),
        )
        hc, atr, raw = chandelier_raw(
            bars,
            from_session=bars[5].session,
            through_session=through,
            trail_k=Decimal("4.0"),
        )
        self.assertEqual(hc, Decimal("119"))
        self.assertEqual(raw, hc - Decimal("4.0") * atr)

    def test_exchange_closed_has_empty_bars(self):
        evidence = YahooMarketData(BoomTransport()).get_validated_evidence(
            MarketRequest("BETA", date(2026, 9, 5), "USD")  # Saturday
        )
        self.assertEqual(evidence.bars, ())
        self.assertIn("EXCHANGE_CLOSED", evidence.issues)

    def test_tm_mismatch_suppresses_breach(self):
        market = YahooMarketData(FixtureTransport(self.response))
        evidence = market.get_validated_evidence(
            MarketRequest("BETA", self.session, "USD", tm_close=Decimal("390"))
        )
        self.assertFalse(evidence.valid_for_breach)
        self.assertIn("PRICE_MISMATCH", evidence.issues)

    def test_split_and_wrong_currency_fail_closed(self):
        response = RawMarketResponse(
            **{
                **self.response.__dict__,
                "currency_code": "GBp",
                "splits": (SplitEvent(self.session, Decimal("2")),),
            }
        )
        market = YahooMarketData(FixtureTransport(response))
        evidence = market.get_validated_evidence(
            MarketRequest(
                "BETA",
                self.session,
                "USD",
                plan_created_session=date(2026, 9, 1),
            )
        )
        self.assertFalse(evidence.valid_for_breach)
        self.assertIn("CURRENCY_MISMATCH", evidence.issues)
        self.assertIn("UNREBASED_SPLIT", evidence.issues)

    def test_missing_session_is_not_safe(self):
        response = RawMarketResponse(
            **{**self.response.__dict__, "bars": (_bar(date(2026, 9, 7)),)}
        )
        evidence = YahooMarketData(FixtureTransport(response)).get_validated_evidence(
            MarketRequest("BETA", self.session, "USD")
        )
        self.assertFalse(evidence.valid_for_breach)
        self.assertIsNone(evidence.bar)
        self.assertIn("EXPECTED_SESSION_MISSING", evidence.issues)
        self.assertIn("LAST_AVAILABLE_SESSION:2026-09-07", evidence.issues)
        self.assertNotIn("SKIPPED_INVALID_OHLC:1", evidence.issues)

    def test_missing_session_surfaces_skipped_invalid_ohlc(self):
        """Yahoo sometimes returns a zero/NaN stub bar for LSE names (e.g. TST1.L)."""
        expected = date(2026, 9, 9)
        response = RawMarketResponse(
            requested_symbol="TST1.L",
            returned_symbol="TST1.L",
            currency_code="GBp",
            exchange="LSE",
            quote_timestamp="2026-09-09T15:35:26+00:00",
            bars=(_bar(date(2026, 9, 8), close="63.06", high="63.16", low="62.83", open_="63.12"),),
            raw_metadata={
                "_skipped_invalid_ohlc": 1,
                "_skipped_invalid_ohlc_sessions": ["2026-09-09"],
            },
        )
        evidence = YahooMarketData(
            FixtureTransport(response),
            clock=lambda: datetime(2026, 9, 10, 5, tzinfo=timezone.utc),
        ).get_validated_evidence(
            MarketRequest("TST1.L", expected, "GBP", expected_exchange="LSE")
        )
        self.assertFalse(evidence.valid_for_breach)
        self.assertIsNone(evidence.bar)
        self.assertIn("EXPECTED_SESSION_MISSING", evidence.issues)
        self.assertIn("SKIPPED_INVALID_OHLC:1", evidence.issues)
        self.assertIn("INVALID_OHLC_FOR_EXPECTED_SESSION", evidence.issues)
        self.assertIn("LAST_AVAILABLE_SESSION:2026-09-08", evidence.issues)
        self.assertEqual(evidence.currency, "GBP")
        self.assertEqual(evidence.bars[0].close, Decimal("0.6306"))

    def test_stale_quote_timestamp_blocks_breach(self):
        response = RawMarketResponse(
            **{
                **self.response.__dict__,
                "quote_timestamp": "2026-09-07T20:00:00Z",
            }
        )
        evidence = YahooMarketData(
            FixtureTransport(response),
            clock=lambda: datetime(2026, 9, 8, 23, tzinfo=timezone.utc),
        ).get_validated_evidence(MarketRequest("BETA", self.session, "USD"))
        self.assertFalse(evidence.valid_for_breach)
        self.assertIn("QUOTE_TIMESTAMP_STALE", evidence.issues)

    def test_is_weekend_and_session_expected(self):
        self.assertTrue(is_weekend(date(2026, 9, 5)))
        self.assertTrue(is_weekend(date(2026, 9, 6)))
        self.assertFalse(is_weekend(date(2026, 9, 8)))
        self.assertFalse(session_expected(date(2026, 9, 5)))
        self.assertTrue(session_expected(date(2026, 9, 8)))
        holiday = date(2026, 9, 7)
        self.assertFalse(session_expected(holiday, {holiday}))
        self.assertTrue(session_expected(holiday, set()))

    def test_previous_session_skips_weekend_and_holiday(self):
        self.assertEqual(previous_session(date(2026, 9, 8)), date(2026, 9, 7))
        self.assertEqual(previous_session(date(2026, 9, 7)), date(2026, 9, 4))
        labor_day = date(2026, 9, 7)
        self.assertEqual(
            previous_session(date(2026, 9, 8), holidays={labor_day}),
            date(2026, 9, 4),
        )

    def test_weekend_is_exchange_closed_without_fetch(self):
        saturday = date(2026, 9, 5)
        evidence = YahooMarketData(BoomTransport()).get_validated_evidence(
            MarketRequest("BETA", saturday, "USD")
        )
        self.assertFalse(evidence.valid_for_breach)
        self.assertIsNone(evidence.bar)
        self.assertIn("EXCHANGE_CLOSED", evidence.issues)
        self.assertFalse(any(item.startswith("MARKET_FETCH_FAILED") for item in evidence.issues))

    def test_holiday_is_exchange_closed_without_fetch(self):
        holiday = date(2026, 9, 7)
        market = YahooMarketData(
            BoomTransport(), holidays=frozenset({holiday})
        )
        evidence = market.get_validated_evidence(MarketRequest("BETA", holiday, "USD"))
        self.assertFalse(evidence.valid_for_breach)
        self.assertIn("EXCHANGE_CLOSED", evidence.issues)
        self.assertFalse(any(item.startswith("MARKET_FETCH_FAILED") for item in evidence.issues))

    def test_gap_through_sl_is_observation_on_valid_bar(self):
        market = YahooMarketData(FixtureTransport(self.response))
        evidence = market.get_validated_evidence(
            MarketRequest(
                "BETA",
                self.session,
                "USD",
                active_sl=Decimal("400"),
            )
        )
        self.assertTrue(evidence.gap_through_sl)
        self.assertIn("GAP_THROUGH_SL", evidence.issues)
        self.assertTrue(evidence.valid_for_breach)
        self.assertEqual(evidence.bar.open, Decimal("398"))

    def test_gap_through_sl_false_when_open_above_sl(self):
        evidence = YahooMarketData(FixtureTransport(self.response)).get_validated_evidence(
            MarketRequest("BETA", self.session, "USD", active_sl=Decimal("350"))
        )
        self.assertFalse(evidence.gap_through_sl)
        self.assertNotIn("GAP_THROUGH_SL", evidence.issues)
        self.assertTrue(evidence.valid_for_breach)

    def test_unrebased_split_older_than_75_days(self):
        split_session = date(2026, 6, 1)
        plan_created = date(2026, 5, 15)
        response = RawMarketResponse(
            **{
                **self.response.__dict__,
                "splits": (SplitEvent(split_session, Decimal("2")),),
            }
        )
        transport = WindowTransport(response)
        evidence = YahooMarketData(transport).get_validated_evidence(
            MarketRequest(
                "BETA",
                self.session,
                "USD",
                plan_created_session=plan_created,
            )
        )
        self.assertEqual(transport.calls[0][1], plan_created - timedelta(days=400))
        self.assertFalse(evidence.valid_for_breach)
        self.assertIn("UNREBASED_SPLIT", evidence.issues)

    def test_history_lookback_covers_atr_window(self):
        transport = FixtureTransport(self.response)
        YahooMarketData(transport).get_validated_evidence(
            MarketRequest("BETA", self.session, "USD")
        )
        _, start, end = transport.calls[0]
        self.assertEqual(start, self.session - timedelta(days=400))
        self.assertEqual(end, self.session + timedelta(days=1))

    def test_exchange_mismatch_when_both_present(self):
        evidence = YahooMarketData(FixtureTransport(self.response)).get_validated_evidence(
            MarketRequest("BETA", self.session, "USD", expected_exchange="NMS")
        )
        self.assertIn("EXCHANGE_MISMATCH", evidence.issues)
        self.assertFalse(evidence.valid_for_breach)

    def test_empty_exchange_metadata_is_not_mismatch(self):
        response = RawMarketResponse(**{**self.response.__dict__, "exchange": None})
        evidence = YahooMarketData(FixtureTransport(response)).get_validated_evidence(
            MarketRequest("BETA", self.session, "USD", expected_exchange="NYQ")
        )
        self.assertNotIn("EXCHANGE_MISMATCH", evidence.issues)
        self.assertTrue(evidence.valid_for_breach)


if __name__ == "__main__":
    unittest.main()
