"""Baseline ETF universe and eligibility filters."""

from __future__ import annotations

from datetime import date
from typing import Mapping

from race_engine.allocation.sleeves import BASELINE_UNIVERSE, UniverseEntry
from race_engine.config.constants import DEFAULT_CONFIG


def baseline_universe() -> tuple[UniverseEntry, ...]:
    validate_one_sleeve_per_etf(BASELINE_UNIVERSE)
    return BASELINE_UNIVERSE


def validate_one_sleeve_per_etf(entries: tuple[UniverseEntry, ...]) -> None:
    seen: dict[str, str] = {}
    for entry in entries:
        if entry.ticker in seen and seen[entry.ticker] != entry.sleeve:
            raise ValueError(f"{entry.ticker} maps to both {seen[entry.ticker]} and {entry.sleeve}")
        seen[entry.ticker] = entry.sleeve
    if sleeve_for_ticker("TIP", entries) != "fixed_income":
        raise ValueError("TIP must be classified as fixed_income")
    if sleeve_for_ticker("VTIP", entries) != "fixed_income":
        raise ValueError("VTIP must be classified as fixed_income")


def sleeve_for_ticker(ticker: str, entries: tuple[UniverseEntry, ...] = BASELINE_UNIVERSE) -> str | None:
    for entry in entries:
        if entry.ticker == ticker:
            return entry.sleeve
    return None


def eligible_entries(
    evaluation_date: date,
    price_history_days: Mapping[str, int],
    entries: tuple[UniverseEntry, ...] = BASELINE_UNIVERSE,
    minimum_history_days: int = DEFAULT_CONFIG.universe.minimum_history_days,
) -> tuple[UniverseEntry, ...]:
    return tuple(
        entry
        for entry in entries
        if entry.inception_date <= evaluation_date
        and price_history_days.get(entry.ticker, 0) >= minimum_history_days
    )

