"""Technical indicators used by RACE risk gates."""

from __future__ import annotations

from statistics import fmean, pstdev
from typing import Sequence


def simple_moving_average(values: Sequence[float], window: int) -> float:
    if len(values) < window:
        raise ValueError(f"requires at least {window} observations")
    return fmean(values[-window:])


def total_return(values: Sequence[float], window: int) -> float:
    if len(values) <= window:
        raise ValueError(f"requires more than {window} observations")
    return values[-1] / values[-window - 1] - 1.0


def rsi(values: Sequence[float], window: int = 14) -> float:
    if len(values) <= window:
        raise ValueError(f"requires more than {window} observations")
    gains = []
    losses = []
    for idx in range(len(values) - window, len(values)):
        change = values[idx] - values[idx - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = fmean(gains)
    avg_loss = fmean(losses)
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def rolling_return_percentile(values: Sequence[float], window: int, lookback: int, current_return: float) -> float:
    if len(values) < lookback + window:
        raise ValueError("insufficient values for rolling percentile")
    returns = [
        values[idx] / values[idx - window] - 1.0
        for idx in range(len(values) - lookback, len(values))
    ]
    less_or_equal = sum(1 for value in returns if value <= current_return)
    return 100.0 * less_or_equal / len(returns)


def downside_observations(returns: Sequence[float]) -> int:
    return sum(1 for value in returns if value < 0.0)


def rolling_std(values: Sequence[float], window: int) -> float:
    if len(values) < window:
        raise ValueError(f"requires at least {window} observations")
    return pstdev(values[-window:])

