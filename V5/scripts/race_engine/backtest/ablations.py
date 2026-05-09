"""Ablation study configuration for RACE engines."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AblationConfig:
    name: str
    regime_allocation: bool = False
    blending: bool = False
    recovery: bool = False
    etf_ranking: bool = False
    risk_gates: bool = False
    risk_budget: bool = False
    trade_quality: bool = False
    signal_efficacy: bool = False


def ablation_configs() -> tuple[AblationConfig, ...]:
    baseline = AblationConfig("baseline_static_allocation")
    return (
        baseline,
        replace(baseline, name="regime_only", regime_allocation=True),
        replace(baseline, name="regime_blending", regime_allocation=True, blending=True),
        replace(baseline, name="recovery", regime_allocation=True, blending=True, recovery=True),
        replace(baseline, name="etf_ranking", regime_allocation=True, blending=True, recovery=True, etf_ranking=True),
        replace(baseline, name="risk_gates", regime_allocation=True, blending=True, recovery=True, etf_ranking=True, risk_gates=True),
        replace(baseline, name="risk_budget", regime_allocation=True, blending=True, recovery=True, etf_ranking=True, risk_gates=True, risk_budget=True),
        replace(baseline, name="trade_quality", regime_allocation=True, blending=True, recovery=True, etf_ranking=True, risk_gates=True, risk_budget=True, trade_quality=True),
        replace(baseline, name="signal_efficacy", regime_allocation=True, blending=True, recovery=True, etf_ranking=True, risk_gates=True, risk_budget=True, trade_quality=True, signal_efficacy=True),
    )


def engine_contributions(sharpes_by_config: dict[str, float]) -> dict[str, float]:
    configs = ablation_configs()
    contributions: dict[str, float] = {}
    for previous, current in zip(configs, configs[1:]):
        contributions[current.name] = sharpes_by_config[current.name] - sharpes_by_config[previous.name]
    return contributions

