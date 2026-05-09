"""Position-weight construction from sleeve targets and selected ETFs."""

from __future__ import annotations

from .selector import RankedETF


RANK_WEIGHTS: dict[int, tuple[float, ...]] = {
    1: (1.0,),
    2: (0.60, 0.40),
    3: (0.50, 0.30, 0.20),
}


def construct_position_weights(
    sleeve_targets: dict[str, float],
    selected: dict[str, tuple[RankedETF, ...]],
    minimum_position_weight: float = 0.50,
) -> dict[str, float]:
    weights: dict[str, float] = {}
    for sleeve, etfs in selected.items():
        if not etfs:
            continue
        rank_weights = RANK_WEIGHTS[len(etfs)]
        sleeve_weights = {
            etf.ticker: sleeve_targets[sleeve] * rank_weights[index]
            for index, etf in enumerate(etfs)
        }
        sleeve_weights = _drop_and_redistribute(sleeve_weights, minimum_position_weight)
        weights.update(sleeve_weights)
    return _normalize(weights)


def _drop_and_redistribute(weights: dict[str, float], minimum: float) -> dict[str, float]:
    kept = {ticker: weight for ticker, weight in weights.items() if weight >= minimum}
    if not kept:
        top_ticker = max(weights, key=weights.get)
        return {top_ticker: sum(weights.values())}
    dropped = sum(weights.values()) - sum(kept.values())
    if dropped <= 0:
        return kept
    total_kept = sum(kept.values())
    return {ticker: weight + dropped * (weight / total_kept) for ticker, weight in kept.items()}


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total == 0:
        return weights
    return {ticker: round(weight * 100.0 / total, 6) for ticker, weight in weights.items()}
