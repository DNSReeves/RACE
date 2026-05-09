"""Core RACE regime engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .signals import (
    SignalResult,
    breadth_signal,
    hyg_lqd_relative_trend_signal,
    hy_oas_signal,
    inflation_stress_flags,
    qqq_spy_relative_strength_signal,
    spy_ma_buffer_signal,
    spy_ols_trend_signal,
    spy_realized_vol_signal,
    t10y2y_signal,
    vix_change_signal,
    vix_level_signal,
)
from .state import RegimeState, update_regime_state


SIGNAL_NAMES: tuple[str, ...] = (
    "spy_200d_normalized_ols_slope",
    "spy_close_vs_150d_ma",
    "qqq_spy_63d_relative_strength",
    "breadth",
    "vix_level",
    "vix_20d_change",
    "spy_21d_realized_vol",
    "hy_oas",
    "hyg_lqd_21d_relative_trend",
    "t10y2y",
)


@dataclass(frozen=True)
class RegimeInputs:
    spy_closes: tuple[float, ...]
    qqq_closes: tuple[float, ...]
    vix_values: tuple[float, ...]
    hyg_closes: tuple[float, ...]
    lqd_closes: tuple[float, ...]
    dbc_closes: tuple[float, ...]
    t10yie_values: tuple[float, ...]
    hy_oas_bps: float
    t10y2y_spread: float
    percent_above_50dma: float | None = None
    rsp_closes: tuple[float, ...] | None = None


@dataclass(frozen=True)
class RegimeDecision:
    signals: tuple[SignalResult, ...]
    composite_score: float
    base_regime: str
    proposed_regime: str
    confirmed_regime: str
    state: RegimeState
    inflation_flags: tuple[bool, bool]
    raw_inputs: dict[str, float]


def compute_regime_decision(
    inputs: RegimeInputs,
    state: RegimeState | None = None,
    weights: Mapping[str, float] | None = None,
) -> RegimeDecision:
    current_state = state or RegimeState()
    signals = _compute_signals(inputs)
    composite = composite_score(signals, weights)
    base = map_base_regime(composite)
    inflation_flag_a, inflation_flag_b, raw = inflation_stress_flags(
        inputs.t10yie_values,
        inputs.dbc_closes,
        inputs.spy_closes,
    )
    proposed = apply_inflation_override(base, inflation_flag_a, inflation_flag_b)
    next_state = update_regime_state(current_state, proposed, composite)
    return RegimeDecision(
        signals=signals,
        composite_score=composite,
        base_regime=base,
        proposed_regime=proposed,
        confirmed_regime=next_state.confirmed_regime,
        state=next_state,
        inflation_flags=(inflation_flag_a, inflation_flag_b),
        raw_inputs=raw,
    )


def composite_score(
    signals: tuple[SignalResult, ...],
    weights: Mapping[str, float] | None = None,
) -> float:
    if weights is None:
        weight_map = {signal.name: 1.0 / len(signals) for signal in signals}
    else:
        weight_map = dict(weights)
    total_weight = sum(weight_map.get(signal.name, 0.0) for signal in signals)
    if abs(total_weight - 1.0) > 0.0001:
        raise ValueError(f"composite weights sum to {total_weight}, not 1")
    return sum(signal.value * weight_map.get(signal.name, 0.0) for signal in signals)


def map_base_regime(score: float) -> str:
    if score >= 0.30:
        return "risk_on"
    if score >= -0.10:
        return "neutral"
    if score >= -0.40:
        return "risk_off"
    return "cash_defensive"


def apply_inflation_override(base_regime: str, t10yie_flag: bool, commodity_flag: bool) -> str:
    if base_regime in {"risk_on", "neutral"} and t10yie_flag and commodity_flag:
        return "inflation_stress"
    return base_regime


def _compute_signals(inputs: RegimeInputs) -> tuple[SignalResult, ...]:
    breadth = breadth_signal(
        percent_above_50dma=inputs.percent_above_50dma,
        rsp_closes=inputs.rsp_closes,
        spy_closes=inputs.spy_closes,
    )
    return (
        spy_ols_trend_signal(inputs.spy_closes),
        spy_ma_buffer_signal(inputs.spy_closes),
        qqq_spy_relative_strength_signal(inputs.qqq_closes, inputs.spy_closes),
        SignalResult("breadth", breadth.value, breadth.raw_inputs),
        vix_level_signal(inputs.vix_values[-1]),
        vix_change_signal(inputs.vix_values),
        spy_realized_vol_signal(inputs.spy_closes),
        hy_oas_signal(inputs.hy_oas_bps),
        hyg_lqd_relative_trend_signal(inputs.hyg_closes, inputs.lqd_closes),
        t10y2y_signal(inputs.t10y2y_spread),
    )

