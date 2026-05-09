"""RACE-only macro provider adapters."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .models import MacroObservation


REQUIRED_TIER1_SERIES: tuple[str, ...] = (
    "SPY",
    "QQQ",
    "VIX",
    "IEF",
    "HYG",
    "LQD",
    "DBC",
    "GLD",
    "T10Y2Y",
    "T10YIE",
    "BAMLH0A0HYM2",
)


class MacroSQLiteLoader:
    """Read-only macro loader for RACE-specific series."""

    def __init__(self, database_path: str | Path, table: str = "macro_observations") -> None:
        self.database_path = Path(database_path)
        self.table = table

    def latest(self, series_name: str) -> MacroObservation | None:
        uri = f"file:{self.database_path.as_posix()}?mode=ro"
        sql = (
            f"select series_name, date, value from {self.table} "
            "where series_name = ? order by date desc limit 1"
        )
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(sql, (series_name,)).fetchone()
        if row is None:
            return None
        return MacroObservation(
            series_name=row["series_name"],
            date=date.fromisoformat(row["date"]),
            value=float(row["value"]),
        )

