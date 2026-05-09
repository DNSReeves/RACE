"""Execution-aware trade-quality scoring and deferral aging."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.config.constants import DEFAULT_CONFIG


@dataclass(frozen=True)
class TradeQualityComponents:
    score_gap: float
    execution_cost: float
    regime_alignment: float
    liquidity_quality: float
    timing: float


@dataclass(frozen=True)
class TradeQualityDecision:
    status: str
    score: float
    threshold: float
    components: dict[str, float]
    deferral_count: int


def trade_quality_score(components: TradeQualityComponents) -> tuple[float, dict[str, float]]:
    weights = DEFAULT_CONFIG.trade_quality.component_weights.as_dict()
    values = {
        "score_gap": components.score_gap,
        "execution_cost": components.execution_cost,
        "regime_alignment": components.regime_alignment,
        "liquidity_quality": components.liquidity_quality,
        "timing": components.timing,
    }
    return sum(values[name] * weights[name] for name in weights), values


def evaluate_trade_quality(
    regime: str,
    components: TradeQualityComponents,
    prior_deferrals: int = 0,
) -> TradeQualityDecision:
    score, values = trade_quality_score(components)
    threshold = DEFAULT_CONFIG.trade_quality.thresholds_by_regime()[regime]
    if score >= threshold:
        return TradeQualityDecision("EXECUTE", score, threshold, values, 0)
    deferrals = prior_deferrals + 1
    if deferrals >= DEFAULT_CONFIG.rebalancing.max_deferred_weeks:
        return TradeQualityDecision("ABANDON", score, threshold, values, deferrals)
    return TradeQualityDecision("DEFER", score, threshold, values, deferrals)

