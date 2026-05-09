"""Sensitivity sweep definitions and comparable result rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


REQUIRED_SWEEPS: tuple[str, ...] = (
    "replacement_margin",
    "confirmation_weeks",
    "3m_momentum_threshold",
    "vix_bound",
    "hy_spread_threshold",
    "etf_score_weight_perturbation",
    "confidence_distance",
    "efficacy_on_off_range",
    "risk_hard_cap",
    "trade_quality_threshold",
    "recovery_entry_on_off",
)


@dataclass(frozen=True)
class SweepResult:
    parameter: str
    value: object
    metric_name: str
    metric_value: float


def run_sensitivity_sweeps(
    values_by_parameter: dict[str, Iterable[object]],
    evaluator: Callable[[str, object], float],
    metric_name: str = "score",
) -> tuple[SweepResult, ...]:
    missing = set(REQUIRED_SWEEPS) - set(values_by_parameter)
    if missing:
        raise ValueError(f"missing required sweeps: {sorted(missing)}")
    rows = []
    for parameter in REQUIRED_SWEEPS:
        for value in values_by_parameter[parameter]:
            rows.append(SweepResult(parameter, value, metric_name, evaluator(parameter, value)))
    return tuple(rows)

