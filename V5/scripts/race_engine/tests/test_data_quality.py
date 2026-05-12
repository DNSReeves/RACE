import sqlite3
from datetime import date, timedelta

from race_engine.data.adapter import RaceMarketDataAdapter
from race_engine.data.macro_loader import REQUIRED_TIER1_SERIES
from race_engine.data.models import ETFMetrics, MacroObservation, PriceBar
from race_engine.data.quality import evaluate_etf_quality, forward_fill_single_gaps
from race_engine.data.readiness import evaluate_tier1_readiness


def _bars(count: int) -> tuple[PriceBar, ...]:
    start = date(2025, 1, 1)
    return tuple(
        PriceBar("SPY", start + timedelta(days=i), 1, 1, 1, 1, 1, 100)
        for i in range(count)
    )


def test_single_gap_forward_fills_but_two_gaps_require_review() -> None:
    filled, review = forward_fill_single_gaps((1.0, None, 3.0, None, None, 6.0))
    assert filled == (1.0, 1.0, 3.0, 3.0, None, 6.0)
    assert review is True


def test_missing_tier1_blocks_execution_without_fallback() -> None:
    as_of = date(2026, 5, 9)
    observations = {
        name: MacroObservation(name, as_of, 1.0)
        for name in REQUIRED_TIER1_SERIES
        if name != "VIX"
    }

    result = evaluate_tier1_readiness(observations, as_of)

    assert result.can_execute is False
    assert result.missing_tier1 == ("VIX",)
    assert result.events[0].event_type == "TIER1_MISSING"


def test_stale_tier1_with_fallback_is_degraded_but_executable() -> None:
    as_of = date(2026, 5, 9)
    observations = {
        name: MacroObservation(name, as_of, 1.0) for name in REQUIRED_TIER1_SERIES
    }
    observations["T10Y2Y"] = MacroObservation("T10Y2Y", date(2026, 5, 1), 0.5)

    result = evaluate_tier1_readiness(observations, as_of, {"T10Y2Y": "last_valid"})

    assert result.can_execute is True
    assert result.degraded is True
    assert result.events[0].fallback_applied == "last_valid"


def test_missing_ohlcv_makes_only_that_etf_ineligible() -> None:
    result = evaluate_etf_quality("ABC", (), None, date(2026, 5, 9))

    assert result.eligible is False
    assert result.events[0].event_type == "OHLCV_MISSING"


def test_tier2_stale_values_emit_degraded_events() -> None:
    result = evaluate_etf_quality(
        "SPY",
        _bars(252),
        ETFMetrics("SPY", date(2026, 3, 1), aum=1.0, expense_ratio=0.09, bid_ask_spread=None),
        date(2026, 5, 9),
        sleeve_median_spread=0.02,
    )

    assert result.eligible is True
    assert result.status == "WARN"
    assert {event.event_type for event in result.events} == {
        "AUM_STALE",
        "SPREAD_STALE",
    }
    assert result.values["bid_ask_spread"] == 0.02


def test_market_adapter_reads_sqlite_in_read_only_mode(tmp_path) -> None:
    db_path = tmp_path / "market.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "insert into prices values ('SPY', '2026-05-08', 1, 2, 0.5, 1.5, 1.4, 1000)"
        )
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
        )
        connection.execute(
            "insert into etf_metrics values ('SPY', '2026-05-08', 100000000, 0.09, 0.01)"
        )

    adapter = RaceMarketDataAdapter(db_path)

    bars = adapter.get_ohlcv("SPY")
    metrics = adapter.get_metrics("SPY")
    assert bars[0].adjusted_close == 1.4
    assert metrics is not None
    assert metrics.aum == 100000000


def test_market_adapter_defaults_nullable_price_fields(tmp_path) -> None:
    db_path = tmp_path / "market.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "insert into prices values ('VIX', '2026-05-08', null, null, null, null, 15.5, null)"
        )

    bars = RaceMarketDataAdapter(db_path).get_ohlcv("VIX")

    assert bars[0].open == 15.5
    assert bars[0].high == 15.5
    assert bars[0].low == 15.5
    assert bars[0].close == 15.5
    assert bars[0].volume == 0.0


def test_market_adapter_accepts_timestamp_metric_as_of(tmp_path) -> None:
    db_path = tmp_path / "market.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
        )
        connection.execute(
            "insert into etf_metrics values ('SPY', '2025-09-18T09:16:20.507644', 100000000, 0.09, null)"
        )

    metrics = RaceMarketDataAdapter(db_path).get_metrics("SPY")

    assert metrics is not None
    assert metrics.as_of.isoformat() == "2025-09-18"
    assert metrics.bid_ask_spread is None
