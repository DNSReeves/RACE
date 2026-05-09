"""Sleeve variance contribution reporting."""

from __future__ import annotations


def sleeve_variance_contribution(
    weights: dict[str, float],
    ticker_to_sleeve: dict[str, str],
    return_variances: dict[str, float],
) -> dict[str, float]:
    raw: dict[str, float] = {}
    for ticker, weight in weights.items():
        sleeve = ticker_to_sleeve[ticker]
        raw[sleeve] = raw.get(sleeve, 0.0) + (weight / 100.0) ** 2 * return_variances.get(ticker, 0.0)
    total = sum(raw.values())
    if total == 0.0:
        return {sleeve: 0.0 for sleeve in raw}
    return {sleeve: value / total for sleeve, value in raw.items()}

