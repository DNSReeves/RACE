import sqlite3
from datetime import date, timedelta

from race_engine.data.cache_builder import build_race_market_cache, required_price_tickers


def test_cache_builder_writes_race_schema(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    _create_source_db(source)

    result = build_race_market_cache(source, output)

    assert result.output_path == output
    assert result.price_rows > 0
    assert result.metric_rows > 0
    assert result.macro_rows > 0
    assert result.warnings == ()
    with sqlite3.connect(output) as connection:
        price_columns = [row[1] for row in connection.execute("pragma table_info(prices)")]
        assert price_columns == [
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
        ]
        assert connection.execute("select count(*) from prices where ticker = 'SPY'").fetchone()[0] == 3
        assert connection.execute("select value from macro_observations where series_name = 'T10YIE' order by date limit 1").fetchone()[0] == 2.0


def test_cache_builder_uses_read_only_source_and_does_not_create_source_tables(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    _create_source_db(source)

    build_race_market_cache(source, output)

    with sqlite3.connect(source) as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type = 'table'")}
    assert "race_metadata" not in tables
    assert "prices" in tables


def test_cache_builder_reports_missing_optional_tables(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute(
            "create table prices (ticker text, date text, adjusted_close real)"
        )
        connection.execute("insert into prices values ('SPY', '2026-01-01', 100)")

    result = build_race_market_cache(source, output)

    assert "metrics table not found: etf_metrics" in result.warnings
    assert "macro table not found: macro_observations" in result.warnings


def _create_source_db(path):
    tickers = required_price_tickers()
    start = date(2026, 1, 1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
        )
        connection.execute(
            "create table macro_observations (series_name text, date text, value real)"
        )
        for ticker in tickers:
            for offset in range(3):
                value = 100 + offset
                connection.execute(
                    "insert into prices values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, (start + timedelta(days=offset)).isoformat(), value, value, value, value, value, 1000),
                )
            connection.execute(
                "insert into etf_metrics values (?, ?, ?, ?, ?)",
                (ticker, start.isoformat(), 100_000_000, 0.1, 0.01),
            )
        for offset in range(3):
            current = start + timedelta(days=offset)
            connection.execute("insert into macro_observations values ('T10YIE', ?, ?)", (current.isoformat(), 2.0 + offset))
            connection.execute("insert into macro_observations values ('T10Y2Y', ?, ?)", (current.isoformat(), 0.5))
            connection.execute("insert into macro_observations values ('BAMLH0A0HYM2', ?, ?)", (current.isoformat(), 300.0))

