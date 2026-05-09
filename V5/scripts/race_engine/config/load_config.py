"""Configuration loader with explicit copy-on-write override support."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .constants import DEFAULT_CONFIG
from .schema import (
    BacktestSettings,
    DriftBand,
    ETFUniverseConfig,
    HoldingCountRange,
    RaceConfig,
    RankingWeights,
    RebalancingThresholds,
    RegimeAllocation,
    RiskBudgetCaps,
    RiskGateConfig,
    SleeveAllocation,
    TradeQualityComponentWeights,
    TradeQualityThresholds,
)


def load_config(overrides: Mapping[str, Any] | None = None) -> RaceConfig:
    """Return a validated config copy with optional sensitivity overrides.

    Overrides are nested dictionaries matching the dataclass field names. The
    module-level defaults are never mutated.
    """

    raw = asdict(DEFAULT_CONFIG)
    if overrides:
        _deep_merge(raw, overrides)
    return _config_from_mapping(raw)


def _deep_merge(base: dict[str, Any], overrides: Mapping[str, Any]) -> None:
    for key, value in overrides.items():
        if key not in base:
            raise KeyError(f"unknown config override: {key}")
        if isinstance(base[key], dict) and isinstance(value, Mapping):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _config_from_mapping(raw: Mapping[str, Any]) -> RaceConfig:
    return RaceConfig(
        regimes=tuple(raw["regimes"]),
        sleeves=tuple(raw["sleeves"]),
        allocations=tuple(
            RegimeAllocation(
                regime=item["regime"],
                sleeves=tuple(SleeveAllocation(**sleeve) for sleeve in item["sleeves"]),
            )
            for item in raw["allocations"]
        ),
        drift_bands=tuple(DriftBand(**item) for item in raw["drift_bands"]),
        universe=ETFUniverseConfig(
            selection_counts=tuple(
                HoldingCountRange(**item) for item in raw["universe"]["selection_counts"]
            ),
            minimum_history_days=raw["universe"]["minimum_history_days"],
        ),
        risk_gates=RiskGateConfig(**raw["risk_gates"]),
        ranking_weights=RankingWeights(**raw["ranking_weights"]),
        risk_budget=RiskBudgetCaps(
            hard_volatility_caps=tuple(tuple(item) for item in raw["risk_budget"]["hard_volatility_caps"]),
            max_single_position_weight=raw["risk_budget"]["max_single_position_weight"],
            max_single_etf_average_portfolio_value=raw["risk_budget"][
                "max_single_etf_average_portfolio_value"
            ],
            duplicate_correlation_threshold=raw["risk_budget"]["duplicate_correlation_threshold"],
            duplicate_combined_exposure_cap=raw["risk_budget"]["duplicate_combined_exposure_cap"],
            low_volatility_floor_ratio=raw["risk_budget"]["low_volatility_floor_ratio"],
        ),
        rebalancing=RebalancingThresholds(
            replacement_margins=tuple(tuple(item) for item in raw["rebalancing"]["replacement_margins"]),
            high_turnover_threshold=raw["rebalancing"]["high_turnover_threshold"],
            high_turnover_margin_addon=raw["rebalancing"]["high_turnover_margin_addon"],
            minimum_trade_weight=raw["rebalancing"]["minimum_trade_weight"],
            max_deferred_weeks=raw["rebalancing"]["max_deferred_weeks"],
        ),
        trade_quality=TradeQualityThresholds(
            component_weights=TradeQualityComponentWeights(
                **raw["trade_quality"]["component_weights"]
            ),
            thresholds=tuple(tuple(item) for item in raw["trade_quality"]["thresholds"]),
        ),
        backtest=BacktestSettings(**raw["backtest"]),
    )
