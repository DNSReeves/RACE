"""Turnover monitoring."""

from __future__ import annotations

from datetime import date, timedelta

from race_engine.config.constants import DEFAULT_CONFIG


def trailing_one_way_turnover(trades: tuple[tuple[date, float], ...], as_of: date) -> float:
    start = as_of - timedelta(days=365)
    return sum(weight for trade_date, weight in trades if start <= trade_date <= as_of)


def turnover_margin_addon(trailing_turnover: float) -> float:
    if trailing_turnover > DEFAULT_CONFIG.rebalancing.high_turnover_threshold:
        return DEFAULT_CONFIG.rebalancing.high_turnover_margin_addon
    return 0.0

