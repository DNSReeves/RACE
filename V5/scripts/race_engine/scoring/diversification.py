"""Diversification factor calculations."""

from __future__ import annotations

from math import sqrt
from statistics import fmean, pstdev
from typing import Mapping, Sequence


def diversification_score(
    candidate_returns: Sequence[float],
    current_portfolio_returns: Sequence[float] | None = None,
    sleeve_peer_returns: Mapping[str, Sequence[float]] | None = None,
) -> float:
    if current_portfolio_returns:
        length = min(len(candidate_returns), len(current_portfolio_returns))
        if length < 2:
            return 0.0
        candidate = tuple(candidate_returns[-length:])
        current = tuple(current_portfolio_returns[-length:])
        combined = tuple(0.95 * current[i] + 0.05 * candidate[i] for i in range(length))
        marginal_vol = pstdev(combined) - pstdev(current)
        return -marginal_vol
    if not sleeve_peer_returns:
        return 0.0
    correlations = [
        abs(correlation(candidate_returns, peer_returns))
        for peer_returns in sleeve_peer_returns.values()
        if len(peer_returns) >= 2
    ]
    if not correlations:
        return 0.0
    return 1.0 - fmean(correlations)


def correlation(a: Sequence[float], b: Sequence[float]) -> float:
    length = min(len(a), len(b))
    if length < 2:
        return 0.0
    x = tuple(float(value) for value in a[-length:])
    y = tuple(float(value) for value in b[-length:])
    x_mean = fmean(x)
    y_mean = fmean(y)
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(length))
    denominator = sqrt(sum((value - x_mean) ** 2 for value in x) * sum((value - y_mean) ** 2 for value in y))
    return 0.0 if denominator == 0.0 else numerator / denominator

