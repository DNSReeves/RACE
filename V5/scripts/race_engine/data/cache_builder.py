"""Build the RACE-specific market data cache from generic local databases."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from race_engine.allocation.sleeves import BASELINE_UNIVERSE
from race_engine.data.macro_loader import REQUIRED_TIER1_SERIES


PRICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adjusted_close REAL NOT NULL,
    volume REAL,
    PRIMARY KEY (ticker, date)
)
"""

ETF_METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS etf_metrics (
    ticker TEXT NOT NULL,
    as_of TEXT NOT NULL,
    aum REAL,
    expense_ratio REAL,
    bid_ask_spread REAL,
    PRIMARY KEY (ticker, as_of)
)
"""

MACRO_SCHEMA = """
CREATE TABLE IF NOT EXISTS macro_observations (
    series_name TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (series_name, date)
)
"""


@dataclass(frozen=True)
class SourceMapping:
    price_table: str = "prices"
    price_ticker: str = "ticker"
    price_date: str = "date"
    price_open: str = "open"
    price_high: str = "high"
    price_low: str = "low"
    price_close: str = "close"
    price_adjusted_close: str = "adjusted_close"
    price_volume: str = "volume"
    metrics_table: str = "etf_metrics"
    metrics_ticker: str = "ticker"
    metrics_as_of: str = "as_of"
    metrics_aum: str = "aum"
    metrics_expense_ratio: str = "expense_ratio"
    metrics_bid_ask_spread: str = "bid_ask_spread"
    macro_table: str = "macro_observations"
    macro_series: str = "series_name"
    macro_date: str = "date"
    macro_value: str = "value"


@dataclass(frozen=True)
class CacheBuildResult:
    output_path: Path
    price_rows: int
    metric_rows: int
    macro_rows: int
    warnings: tuple[str, ...]


def build_race_market_cache(
    source_database: str | Path,
    output_database: str | Path = "race_engine_out/race_market_cache.sqlite",
    mapping: SourceMapping | None = None,
) -> CacheBuildResult:
    """Translate a generic local ETF database into the RACE cache schema.

    The source database is opened in SQLite read-only mode. This function does
    not import or call ``dbloader.py``.
    """

    source_path = Path(source_database)
    output_path = Path(output_database)
    config = mapping or SourceMapping()
    warnings: list[str] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect_read_only(source_path) as source, sqlite3.connect(output_path) as target:
        _create_target_schema(target)
        tickers = required_price_tickers()
        price_rows = _copy_prices(source, target, config, tickers)
        metric_rows = _copy_metrics(source, target, config, tickers, warnings)
        macro_rows = _copy_macro(source, target, config, warnings)
        target.commit()

    return CacheBuildResult(output_path, price_rows, metric_rows, macro_rows, tuple(warnings))


def required_price_tickers() -> tuple[str, ...]:
    macro_price_tickers = (
        ticker
        for ticker in REQUIRED_TIER1_SERIES
        if ticker not in {"T10Y2Y", "T10YIE", "BAMLH0A0HYM2"}
    )
    universe = (entry.ticker for entry in BASELINE_UNIVERSE)
    return tuple(dict.fromkeys((*macro_price_tickers, *universe)))


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"source database not found: {path}")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _create_target_schema(connection: sqlite3.Connection) -> None:
    connection.execute(PRICE_SCHEMA)
    connection.execute(ETF_METRICS_SCHEMA)
    connection.execute(MACRO_SCHEMA)
    connection.execute("delete from prices")
    connection.execute("delete from etf_metrics")
    connection.execute("delete from macro_observations")


def _copy_prices(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    mapping: SourceMapping,
    tickers: Iterable[str],
) -> int:
    _require_table(source, mapping.price_table)
    _require_columns(
        source,
        mapping.price_table,
        (
            mapping.price_ticker,
            mapping.price_date,
            mapping.price_adjusted_close,
        ),
    )
    optional = _table_columns(source, mapping.price_table)
    rows_written = 0
    sql = f"""
        select
            {mapping.price_ticker} as ticker,
            {mapping.price_date} as date,
            {_column_or_null(optional, mapping.price_open)} as open,
            {_column_or_null(optional, mapping.price_high)} as high,
            {_column_or_null(optional, mapping.price_low)} as low,
            {_column_or_null(optional, mapping.price_close)} as close,
            {mapping.price_adjusted_close} as adjusted_close,
            {_column_or_null(optional, mapping.price_volume)} as volume
        from {mapping.price_table}
        where {mapping.price_ticker} = ?
        order by {mapping.price_date}
    """
    for ticker in tickers:
        for row in source.execute(sql, (ticker,)):
            if row["adjusted_close"] is None:
                continue
            target.execute(
                """
                insert or replace into prices
                (ticker, date, open, high, low, close, adjusted_close, volume)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ticker"],
                    row["date"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["adjusted_close"],
                    row["volume"],
                ),
            )
            rows_written += 1
    return rows_written


def _copy_metrics(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    mapping: SourceMapping,
    tickers: Iterable[str],
    warnings: list[str],
) -> int:
    if not _has_table(source, mapping.metrics_table):
        warnings.append(f"metrics table not found: {mapping.metrics_table}")
        return 0
    _require_columns(source, mapping.metrics_table, (mapping.metrics_ticker, mapping.metrics_as_of))
    optional = _table_columns(source, mapping.metrics_table)
    rows_written = 0
    sql = f"""
        select
            {mapping.metrics_ticker} as ticker,
            {mapping.metrics_as_of} as as_of,
            {_column_or_null(optional, mapping.metrics_aum)} as aum,
            {_column_or_null(optional, mapping.metrics_expense_ratio)} as expense_ratio,
            {_column_or_null(optional, mapping.metrics_bid_ask_spread)} as bid_ask_spread
        from {mapping.metrics_table}
        where {mapping.metrics_ticker} = ?
        order by {mapping.metrics_as_of}
    """
    for ticker in tickers:
        for row in source.execute(sql, (ticker,)):
            target.execute(
                """
                insert or replace into etf_metrics
                (ticker, as_of, aum, expense_ratio, bid_ask_spread)
                values (?, ?, ?, ?, ?)
                """,
                (row["ticker"], row["as_of"], row["aum"], row["expense_ratio"], row["bid_ask_spread"]),
            )
            rows_written += 1
    return rows_written


def _copy_macro(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    mapping: SourceMapping,
    warnings: list[str],
) -> int:
    if not _has_table(source, mapping.macro_table):
        warnings.append(f"macro table not found: {mapping.macro_table}")
        return 0
    _require_columns(source, mapping.macro_table, (mapping.macro_series, mapping.macro_date, mapping.macro_value))
    rows_written = 0
    sql = f"""
        select
            {mapping.macro_series} as series_name,
            {mapping.macro_date} as date,
            {mapping.macro_value} as value
        from {mapping.macro_table}
        where {mapping.macro_series} in ({",".join("?" for _ in REQUIRED_TIER1_SERIES)})
        order by {mapping.macro_series}, {mapping.macro_date}
    """
    for row in source.execute(sql, REQUIRED_TIER1_SERIES):
        target.execute(
            """
            insert or replace into macro_observations
            (series_name, date, value)
            values (?, ?, ?)
            """,
            (row["series_name"], row["date"], row["value"]),
        )
        rows_written += 1
    return rows_written


def _has_table(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type = 'table' and name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    if not _has_table(connection, table):
        raise ValueError(f"required source table not found: {table}")


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"pragma table_info({table})")}


def _require_columns(connection: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> None:
    available = _table_columns(connection, table)
    missing = [column for column in columns if column not in available]
    if missing:
        raise ValueError(f"{table} missing required columns: {', '.join(missing)}")


def _column_or_null(available: set[str], column: str) -> str:
    return column if column in available else "null"

