"""Composite ETF scoring within sleeves."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, pstdev
from typing import Mapping

from race_engine.config.constants import DEFAULT_CONFIG


@dataclass(frozen=True)
class ETFScoreInput:
    ticker: str
    sleeve: str
    factors: dict[str, float]
    eligible: bool = True


@dataclass(frozen=True)
class ETFCompositeScore:
    ticker: str
    sleeve: str
    score: float
    z_scores: dict[str, float]
    audit: dict[str, object]


FACTOR_DIRECTIONS: dict[str, float] = {
    "sortino_level": 1.0,
    "sortino_trend": 1.0,
    "total_return": 1.0,
    "max_drawdown": -1.0,
    "realized_volatility": -1.0,
    "vehicle_quality": 1.0,
    "diversification": 1.0,
}


def composite_scores(inputs: tuple[ETFScoreInput, ...]) -> tuple[ETFCompositeScore, ...]:
    if any(not item.eligible for item in inputs):
        raise ValueError("composite scores require pre-eligible ETFs only")
    by_sleeve: dict[str, list[ETFScoreInput]] = {}
    for item in inputs:
        by_sleeve.setdefault(item.sleeve, []).append(item)

    weights = DEFAULT_CONFIG.ranking_weights.as_dict()
    outputs: list[ETFCompositeScore] = []
    for sleeve_items in by_sleeve.values():
        factor_zscores = {
            factor: _zscores([item.factors[factor] * FACTOR_DIRECTIONS[factor] for item in sleeve_items])
            for factor in weights
        }
        small_sleeve = len(sleeve_items) == 1
        for index, item in enumerate(sleeve_items):
            z_by_factor = {factor: factor_zscores[factor][index] for factor in weights}
            score = sum(weights[factor] * z_by_factor[factor] for factor in weights)
            outputs.append(
                ETFCompositeScore(
                    ticker=item.ticker,
                    sleeve=item.sleeve,
                    score=score,
                    z_scores=z_by_factor,
                    audit={
                        "raw_factors": dict(item.factors),
                        "z_scores": z_by_factor,
                        "final_composite_score": score,
                        "flags": ("SMALL_SLEEVE",) if small_sleeve else (),
                    },
                )
            )
    return tuple(outputs)


def _zscores(values: list[float]) -> tuple[float, ...]:
    if len(values) == 1:
        return (0.0,)
    mean = fmean(values)
    deviation = pstdev(values)
    if deviation == 0.0:
        return tuple(0.0 for _ in values)
    return tuple(max(-3.0, min(3.0, (value - mean) / deviation)) for value in values)

