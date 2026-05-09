"""Validation and falsification reporting."""

from __future__ import annotations

from dataclasses import dataclass

from .overfitting import parameter_count_status, returns_concentrated, sensitivity_fragility


@dataclass(frozen=True)
class ValidationReport:
    overall_status: str
    criteria: dict[str, str]
    deltas: dict[str, float]
    regime_segment_excess_returns: dict[str, float]
    engine_contribution_table: dict[str, float]


def build_validation_report(
    race_metrics: dict[str, float],
    spy_metrics: dict[str, float],
    regime_segment_excess_returns: dict[str, float],
    engine_contribution_table: dict[str, float],
    sensitivity_values: tuple[float, ...],
    period_returns: tuple[float, ...],
    regime_parameter_count: int,
) -> ValidationReport:
    deltas = {
        "sharpe_delta_vs_spy": race_metrics["sharpe"] - spy_metrics["sharpe"],
        "max_drawdown_delta_vs_spy": race_metrics["max_drawdown"] - spy_metrics["max_drawdown"],
        "calmar_delta_vs_spy": race_metrics["calmar"] - spy_metrics["calmar"],
    }
    criteria = {
        "sharpe_above_spy": "PASS" if deltas["sharpe_delta_vs_spy"] >= 0 else "FAIL",
        "drawdown_materially_lower": "PASS" if deltas["max_drawdown_delta_vs_spy"] >= 0.10 - 1e-9 else "FAIL",
        "calmar_above_spy": "PASS" if deltas["calmar_delta_vs_spy"] > 0 else "FAIL",
        "four_of_five_regimes_positive": "PASS" if sum(1 for value in regime_segment_excess_returns.values() if value > 0) >= 4 else "FAIL",
        "no_negative_engine_contribution": "PASS" if all(value >= 0 for value in engine_contribution_table.values()) else "FAIL",
        "sensitivity_not_fragile": "PASS" if not sensitivity_fragility(sensitivity_values) else "WARN",
        "returns_not_concentrated": "PASS" if not returns_concentrated(period_returns) else "FAIL",
        "regime_parameter_count": parameter_count_status(regime_parameter_count),
    }
    if "FAIL" in criteria.values():
        overall = "FAIL"
    elif "WARN" in criteria.values():
        overall = "WARN"
    else:
        overall = "PASS"
    return ValidationReport(overall, criteria, deltas, regime_segment_excess_returns, engine_contribution_table)
