"""Read-only adapters over databases populated outside the RACE package."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .models import ETFMetrics, PriceBar


class ReadOnlySQLiteAdapter:
    """Small read-only SQLite wrapper.

    The adapter opens databases with SQLite URI ``mode=ro`` and never exposes
    write helpers. It deliberately has no dependency on ``dbloader.py``.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        uri = f"file:{self.database_path.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def fetch_price_bars(self, ticker: str, table: str = "prices") -> tuple[PriceBar, ...]:
        sql = (
            f"select ticker, date, open, high, low, close, adjusted_close, volume "
            f"from {table} where ticker = ? order by date"
        )
        rows = self._fetch_all(sql, (ticker,))
        return tuple(
            PriceBar(
                ticker=row["ticker"],
                date=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                adjusted_close=float(row["adjusted_close"]),
                volume=float(row["volume"]),
            )
            for row in rows
        )

    def fetch_latest_metrics(self, ticker: str, table: str = "etf_metrics") -> ETFMetrics | None:
        sql = (
            f"select ticker, as_of, aum, expense_ratio, bid_ask_spread from {table} "
            "where ticker = ? order by as_of desc limit 1"
        )
        rows = self._fetch_all(sql, (ticker,))
        if not rows:
            return None
        row = rows[0]
        return ETFMetrics(
            ticker=row["ticker"],
            as_of=date.fromisoformat(row["as_of"]),
            aum=None if row["aum"] is None else float(row["aum"]),
            expense_ratio=None if row["expense_ratio"] is None else float(row["expense_ratio"]),
            bid_ask_spread=None if row["bid_ask_spread"] is None else float(row["bid_ask_spread"]),
        )

    def _fetch_all(self, sql: str, params: Iterable[Any]) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(sql, tuple(params)))


class RaceMarketDataAdapter:
    """Strategy-layer adapter for ETF market data and metrics."""

    def __init__(self, database_path: str | Path) -> None:
        self.reader = ReadOnlySQLiteAdapter(database_path)

    def get_ohlcv(self, ticker: str) -> tuple[PriceBar, ...]:
        return self.reader.fetch_price_bars(ticker)

    def get_metrics(self, ticker: str) -> ETFMetrics | None:
        return self.reader.fetch_latest_metrics(ticker)

