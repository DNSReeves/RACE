"""Regime-boundary target blending for RACE allocations."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.config.constants import DEFAULT_CONFIG
from race_engine.config.schema import RaceConfig, RegimeAllocation


@dataclass(frozen=True)
class BlendResult:
    confirmed_regime: str
    adjacent_regime: str | None
    confidence: float
    targets: dict[str, float]


def blend_targets(
    confirmed_regime: str,
    composite_score: float,
    config: RaceConfig = DEFAULT_CONFIG,
    base_regime_without_override: str | None = None,
    inflation_t10yie_excess: float | None = None,
    inflation_commodity_excess: float | None = None,
) -> BlendResult:
    allocations = config.allocations_by_regime()
    confirmed = allocations[confirmed_regime]

    if confirmed_regime == "inflation_stress":
        adjacent_name = base_regime_without_override or "neutral"
        confidence = inflation_confidence(inflation_t10yie_excess or 0.0, inflation_commodity_excess or 0.0)
    else:
        adjacent_name, confidence = adjacent_regime_and_confidence(confirmed_regime, composite_score)

    if adjacent_name is None:
        raw_targets = _target_map(confirmed)
    else:
        adjacent = allocations[adjacent_name]
        raw_targets = _blend_maps(_target_map(confirmed), _target_map(adjacent), confidence)

    clamped = clamp_and_redistribute(raw_targets, confirmed)
    return BlendResult(confirmed_regime, adjacent_name, confidence, clamped)


def adjacent_regime_and_confidence(regime: str, score: float) -> tuple[str | None, float]:
    if regime == "risk_on":
        return "neutral", min(1.0, max(0.0, (score - 0.30) / 0.10))
    if regime == "neutral":
        distance_to_risk_on = abs(0.30 - score)
        distance_to_risk_off = abs(score - -0.10)
        if distance_to_risk_on < distance_to_risk_off:
            return "risk_on", min(1.0, distance_to_risk_on / 0.10)
        return "risk_off", min(1.0, distance_to_risk_off / 0.10)
    if regime == "risk_off":
        distance_to_neutral = abs(score - -0.10)
        distance_to_cash = abs(score - -0.40)
        if distance_to_neutral < distance_to_cash:
            return "neutral", min(1.0, distance_to_neutral / 0.10)
        return "cash_defensive", min(1.0, distance_to_cash / 0.10)
    if regime == "cash_defensive":
        if score < -0.40:
            return None, 1.0
        return "risk_off", min(1.0, (score - -0.40) / 0.10)
    raise ValueError(f"unsupported regime for boundary blending: {regime}")


def inflation_confidence(t10yie_excess: float, commodity_excess: float) -> float:
    if t10yie_excess <= 0.0 or commodity_excess <= 0.0:
        return 0.0
    return min(1.0, min(t10yie_excess, commodity_excess) / 0.10)


def clamp_and_redistribute(targets: dict[str, float], confirmed: RegimeAllocation) -> dict[str, float]:
    bounds = {
        item.sleeve: (item.min_weight, item.max_weight)
        for item in confirmed.sleeves
    }
    clamped = {
        sleeve: min(max(weight, bounds[sleeve][0]), bounds[sleeve][1])
        for sleeve, weight in targets.items()
    }
    residual = 100.0 - sum(clamped.values())
    while abs(residual) > 0.0001:
        if residual > 0:
            candidates = [s for s, w in clamped.items() if w < bounds[s][1]]
        else:
            candidates = [s for s, w in clamped.items() if w > bounds[s][0]]
        if not candidates:
            raise ValueError("cannot redistribute residual within sleeve bounds")
        share = residual / len(candidates)
        previous_residual = residual
        for sleeve in candidates:
            lower, upper = bounds[sleeve]
            clamped[sleeve] = min(max(clamped[sleeve] + share, lower), upper)
        residual = 100.0 - sum(clamped.values())
        if abs(residual - previous_residual) < 0.000001:
            raise ValueError("redistribution did not converge")
    return {sleeve: round(weight, 6) for sleeve, weight in clamped.items()}


def _target_map(allocation: RegimeAllocation) -> dict[str, float]:
    return {item.sleeve: item.target for item in allocation.sleeves}


def _blend_maps(confirmed: dict[str, float], adjacent: dict[str, float], confidence: float) -> dict[str, float]:
    return {
        sleeve: confidence * confirmed[sleeve] + (1.0 - confidence) * adjacent[sleeve]
        for sleeve in confirmed
    }

