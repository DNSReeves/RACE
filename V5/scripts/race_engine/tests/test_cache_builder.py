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


def test_cache_builder_auto_detects_daily_prices_table(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    start = date(2026, 1, 1)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "create table daily_prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume integer)"
        )
        for ticker in required_price_tickers():
            connection.execute(
                "insert into daily_prices values (?, ?, ?, ?, ?, ?, ?, ?)",
                (ticker, start.isoformat(), 100, 101, 99, 100, 100, 1000),
            )

    result = build_race_market_cache(source, output)

    assert result.price_rows == len(required_price_tickers())
    with sqlite3.connect(output) as connection:
        assert connection.execute("select adjusted_close from prices where ticker = 'SPY'").fetchone()[0] == 100


def test_cache_builder_uses_registry_db_and_authoritative_schema_file(tmp_path) -> None:
    source = tmp_path / "generic_market.sqlite"
    registry = tmp_path / "registry.sqlite"
    schema = tmp_path / "etf_registry_schema.sql"
    output = tmp_path / "race_market_cache.sqlite"
    _create_price_macro_source_db(source)
    _create_registry_db(registry)
    schema.write_text(_registry_schema_sql(), encoding="utf-8")

    result = build_race_market_cache(
        source,
        output,
        source_registry_database=registry,
        registry_schema_file=schema,
    )

    assert "etf_registry" in result.registry_tables
    assert "etf_metrics" in result.registry_tables
    assert result.metric_rows > 0
    with sqlite3.connect(output) as connection:
        row = connection.execute(
            "select as_of, aum, expense_ratio, bid_ask_spread from etf_metrics where ticker = 'SPY'"
        ).fetchone()
    assert row == ("2026-01-03 12:00:00", 200_000_000.0, 0.09, None)


def test_cache_builder_loads_macro_csv_and_vix_csv(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    macro_csv = tmp_path / "macro.csv"
    vix_csv = tmp_path / "vix.csv"
    _create_source_without_macro_or_vix(source)
    macro_csv.write_text(
        "series_name,date,value\n"
        "T10Y2Y,2026-01-01,0.5\n"
        "T10YIE,2026-01-01,2.1\n"
        "BAMLH0A0HYM2,2026-01-01,300\n"
        "IGNORED,2026-01-01,1\n",
        encoding="utf-8",
    )
    vix_csv.write_text(
        "date,value\n2026-01-01,14.5\n2026-01-02,15.0\n",
        encoding="utf-8",
    )

    result = build_race_market_cache(source, output, macro_csv=macro_csv, vix_csv=vix_csv)

    assert result.vix_rows == 2
    assert result.macro_rows == 3
    with sqlite3.connect(output) as connection:
        assert connection.execute("select adjusted_close from prices where ticker = 'VIX' and date = '2026-01-01'").fetchone()[0] == 14.5
        assert connection.execute("select count(*) from macro_observations").fetchone()[0] == 3


def test_cache_builder_loads_macro_sqlite_source(tmp_path) -> None:
    source = tmp_path / "generic.sqlite"
    macro_source = tmp_path / "macro.sqlite"
    output = tmp_path / "race_market_cache.sqlite"
    _create_source_without_macro_or_vix(source)
    with sqlite3.connect(macro_source) as connection:
        connection.execute("create table macro_observations (series_name text, date text, value real)")
        connection.execute("insert into macro_observations values ('T10Y2Y', '2026-01-01', 0.5)")
        connection.execute("insert into macro_observations values ('T10YIE', '2026-01-01', 2.1)")
        connection.execute("insert into macro_observations values ('BAMLH0A0HYM2', '2026-01-01', 300)")

    result = build_race_market_cache(source, output, macro_source_database=macro_source)

    assert result.macro_rows == 3
    with sqlite3.connect(output) as connection:
        assert connection.execute("select value from macro_observations where series_name = 'BAMLH0A0HYM2'").fetchone()[0] == 300


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


def _create_price_macro_source_db(path):
    tickers = required_price_tickers()
    start = date(2026, 1, 1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
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
        for offset in range(3):
            current = start + timedelta(days=offset)
            connection.execute("insert into macro_observations values ('T10YIE', ?, ?)", (current.isoformat(), 2.0 + offset))
            connection.execute("insert into macro_observations values ('T10Y2Y', ?, ?)", (current.isoformat(), 0.5))
            connection.execute("insert into macro_observations values ('BAMLH0A0HYM2', ?, ?)", (current.isoformat(), 300.0))


def _create_registry_db(path):
    tickers = required_price_tickers()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table etf_registry (id integer primary key autoincrement, ticker text unique not null, name text, inception_date date, first_data_date date, last_update_date date, last_successful_load date, data_quality_score real default 0.0, load_status text default 'pending', error_count integer default 0, last_error text, notes text, created_at timestamp default current_timestamp, updated_at timestamp default current_timestamp, exchange text default 'US', asset_class text, sector text, total_rows integer default 0, is_leveraged boolean default 0, is_inverse boolean default 0, is_etn boolean default 0, expense_ratio real)"
        )
        connection.execute(
            "create table etf_metrics (ticker text primary key, name text, aum real, expense_ratio real, holdings_count integer, inception_date date, asset_class text, etf_company text, domicile text, nav real, nav_currency text, avg_volume integer, cusip text, isin text, symbol text, website text, description text, last_updated timestamp default current_timestamp, created_at timestamp default current_timestamp, metrics_source text)"
        )
        connection.execute(
            "create table etf_sectors (id integer primary key autoincrement, ticker text not null, industry text not null, exposure real not null, created_at timestamp default current_timestamp, unique(ticker, industry))"
        )
        connection.execute(
            "create table loading_history (id integer primary key autoincrement, ticker text not null, load_date date not null, data_start_date date, data_end_date date, rows_loaded integer, load_duration_seconds real, status text, error_message text, created_at timestamp default current_timestamp, load_type text default 'incremental', notes text)"
        )
        connection.execute(
            "create table loading_sessions (id integer primary key autoincrement, session_start timestamp default current_timestamp, session_end timestamp, total_etfs integer, successful_loads integer, failed_loads integer, total_rows_loaded integer, session_notes text, session_type text default 'daily')"
        )
        for ticker in tickers:
            connection.execute("insert into etf_registry (ticker) values (?)", (ticker,))
            connection.execute(
                "insert into etf_metrics (ticker, name, aum, expense_ratio, last_updated) values (?, ?, ?, ?, ?)",
                (ticker, ticker, 200_000_000.0, 0.09, "2026-01-03 12:00:00"),
            )


def _create_source_without_macro_or_vix(path):
    tickers = tuple(ticker for ticker in required_price_tickers() if ticker != "VIX")
    start = date(2026, 1, 1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
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


def _registry_schema_sql():
    return """
CREATE TABLE etf_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT,
    inception_date DATE,
    first_data_date DATE,
    last_update_date DATE,
    last_successful_load DATE,
    data_quality_score REAL DEFAULT 0.0,
    load_status TEXT DEFAULT 'pending',
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exchange TEXT DEFAULT 'US',
    asset_class TEXT,
    sector TEXT,
    total_rows INTEGER DEFAULT 0,
    is_leveraged BOOLEAN DEFAULT 0,
    is_inverse BOOLEAN DEFAULT 0,
    is_etn BOOLEAN DEFAULT 0,
    expense_ratio REAL
);
CREATE TABLE etf_metrics (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    aum REAL,
    expense_ratio REAL,
    holdings_count INTEGER,
    inception_date DATE,
    asset_class TEXT,
    etf_company TEXT,
    domicile TEXT,
    nav REAL,
    nav_currency TEXT,
    avg_volume INTEGER,
    cusip TEXT,
    isin TEXT,
    symbol TEXT,
    website TEXT,
    description TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metrics_source TEXT
);
CREATE TABLE etf_sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    industry TEXT NOT NULL,
    exposure REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, industry)
);
CREATE TABLE loading_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    load_date DATE NOT NULL,
    data_start_date DATE,
    data_end_date DATE,
    rows_loaded INTEGER,
    load_duration_seconds REAL,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    load_type TEXT DEFAULT 'incremental',
    notes TEXT
);
CREATE TABLE loading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    total_etfs INTEGER,
    successful_loads INTEGER,
    failed_loads INTEGER,
    total_rows_loaded INTEGER,
    session_notes TEXT,
    session_type TEXT DEFAULT 'daily'
);
"""
