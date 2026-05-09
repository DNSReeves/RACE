"""Regime persistence state machine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeState:
    confirmed_regime: str = "neutral"
    pending_regime: str | None = None
    pending_count: int = 0


def update_regime_state(
    state: RegimeState,
    proposed_regime: str,
    composite_score: float,
    confirmation_weeks: int = 3,
) -> RegimeState:
    if composite_score < -0.60:
        return RegimeState("cash_defensive", None, 0)
    if proposed_regime == state.confirmed_regime:
        return RegimeState(state.confirmed_regime, None, 0)
    if proposed_regime == state.pending_regime:
        count = state.pending_count + 1
    else:
        count = 1
    if count >= confirmation_weeks:
        return RegimeState(proposed_regime, None, 0)
    return RegimeState(state.confirmed_regime, proposed_regime, count)

