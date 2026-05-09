"""Overfitting diagnostics for RACE validation."""

from __future__ import annotations


MAX_REGIME_FREE_PARAMETERS = 15


def parameter_count_status(parameter_count: int) -> str:
    return "PASS" if parameter_count <= MAX_REGIME_FREE_PARAMETERS else "FAIL"


def sensitivity_fragility(values: tuple[float, ...], max_range: float = 0.20) -> bool:
    if not values:
        return True
    return max(values) - min(values) > max_range


def returns_concentrated(period_returns: tuple[float, ...], max_single_period_share: float = 0.50) -> bool:
    positive = [value for value in period_returns if value > 0]
    total = sum(positive)
    if total <= 0:
        return True
    return max(positive) / total > max_single_period_share

