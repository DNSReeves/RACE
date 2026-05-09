"""Replacement decision logic."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.config.constants import DEFAULT_CONFIG


@dataclass(frozen=True)
class ReplacementDecision:
    replace: bool
    required_score: float
    margin: float


def replacement_decision(
    held_score: float,
    candidate_score: float,
    regime: str,
    turnover_margin_addon: float = 0.0,
) -> ReplacementDecision:
    margin = DEFAULT_CONFIG.rebalancing.margins_by_regime()[regime] + turnover_margin_addon
    required = held_score + margin
    return ReplacementDecision(candidate_score > required, required, margin)

