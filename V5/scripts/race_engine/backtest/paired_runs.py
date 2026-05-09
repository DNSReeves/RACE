"""Static/adaptive paired-run configuration hooks."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class BacktestRunConfig:
    name: str
    regime_signal_efficacy_enabled: bool


def static_adaptive_pair(base_name: str = "race") -> tuple[BacktestRunConfig, BacktestRunConfig]:
    static = BacktestRunConfig(f"{base_name}_static", False)
    adaptive = replace(static, name=f"{base_name}_adaptive", regime_signal_efficacy_enabled=True)
    return static, adaptive

