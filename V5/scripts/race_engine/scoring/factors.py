"""Price-return factor calculations for ETF ranking."""

from __future__ import annotations

from math import sqrt
from statistics import pstdev
from typing import Sequence


TRADING_DAYS_PER_YEAR = 252


def period_return(prices: Sequence[float]) -> float:
    if len(prices) < 2:
        raise ValueError("at least two prices are required")
    return prices[-1] / prices[0] - 1.0


def weighted_total_return(prices_12m: Sequence[float], prices_6m: Sequence[float], prices_3m: Sequence[float]) -> float:
    return 0.40 * period_return(prices_12m) + 0.35 * period_return(prices_6m) + 0.25 * period_return(prices_3m)


def max_drawdown(prices: Sequence[float]) -> float:
    if not prices:
        raise ValueError("prices cannot be empty")
    peak = prices[0]
    worst = 0.0
    for price in prices:
        peak = max(peak, price)
        worst = min(worst, price / peak - 1.0)
    return worst


def realized_volatility(prices: Sequence[float]) -> float:
    if len(prices) < 3:
        return 0.0
    returns = [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]
    return pstdev(returns) * sqrt(TRADING_DAYS_PER_YEAR)

