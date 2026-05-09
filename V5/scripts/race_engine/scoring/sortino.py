"""Sortino factor calculations for ETF ranking."""

from __future__ import annotations

from math import sqrt
from statistics import fmean, pstdev
from typing import Sequence


TRADING_DAYS_PER_YEAR = 252
DOWNSIDE_DEVIATION_FLOOR = 0.005


def sortino_ratio(returns: Sequence[float], mar: float = 0.0) -> float:
    if not returns:
        raise ValueError("returns cannot be empty")
    excess = [value - mar for value in returns]
    downside = [min(0.0, value) for value in excess if value < 0.0]
    if not downside:
        downside_deviation = DOWNSIDE_DEVIATION_FLOOR
    else:
        downside_deviation = max(pstdev(downside) * sqrt(TRADING_DAYS_PER_YEAR), DOWNSIDE_DEVIATION_FLOOR)
    annualized_excess_return = fmean(excess) * TRADING_DAYS_PER_YEAR
    return max(-10.0, min(10.0, annualized_excess_return / downside_deviation))


def weighted_sortino_level(
    returns_12m: Sequence[float],
    returns_6m: Sequence[float],
    returns_3m: Sequence[float],
) -> float:
    return (
        0.50 * sortino_ratio(returns_12m)
        + 0.30 * sortino_ratio(returns_6m)
        + 0.20 * sortino_ratio(returns_3m)
    )


def sortino_trend_score(weekly_sortinos: Sequence[float], sortino_3m: float, sortino_12m: float) -> float:
    if len(weekly_sortinos) < 2:
        return 0.0
    slope = _ols_slope(tuple(float(value) for value in weekly_sortinos[-52:]))
    spread = sortino_3m - sortino_12m
    persistence = sum(1 for value in weekly_sortinos[-26:] if value > 0) / min(26, len(weekly_sortinos))
    return slope + spread + persistence


def _ols_slope(values: Sequence[float]) -> float:
    x_mean = (len(values) - 1) / 2
    y_mean = fmean(values)
    denominator = sum((i - x_mean) ** 2 for i in range(len(values)))
    if denominator == 0:
        return 0.0
    return sum((i - x_mean) * (value - y_mean) for i, value in enumerate(values)) / denominator

