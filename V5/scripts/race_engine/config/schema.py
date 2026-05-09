"""Typed configuration schema for the RACE engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PCT_TOLERANCE = 0.0001


@dataclass(frozen=True)
class SleeveAllocation:
    """Target and allowed bounds for one sleeve in one regime."""

    sleeve: str
    target: float
    min_weight: float
    max_weight: float

    def __post_init__(self) -> None:
        _require_pct(self.target, "target")
        _require_pct(self.min_weight, "min_weight")
        _require_pct(self.max_weight, "max_weight")
        if self.min_weight > self.target:
            raise ValueError(f"{self.sleeve}: min_weight exceeds target")
        if self.target > self.max_weight:
            raise ValueError(f"{self.sleeve}: target exceeds max_weight")


@dataclass(frozen=True)
class RegimeAllocation:
    """All sleeve allocations for one confirmed regime."""

    regime: str
    sleeves: tuple[SleeveAllocation, ...]

    def __post_init__(self) -> None:
        _require_unique([item.sleeve for item in self.sleeves], "sleeves")
        total = sum(item.target for item in self.sleeves)
        if abs(total - 100.0) > PCT_TOLERANCE:
            raise ValueError(f"{self.regime}: targets sum to {total}, not 100")

    def by_sleeve(self) -> dict[str, SleeveAllocation]:
        return {item.sleeve: item for item in self.sleeves}


@dataclass(frozen=True)
class DriftBand:
    sleeve: str
    band: float

    def __post_init__(self) -> None:
        _require_pct(self.band, "band")


@dataclass(frozen=True)
class HoldingCountRange:
    sleeve: str
    min_count: int
    max_count: int

    def __post_init__(self) -> None:
        if self.min_count < 1:
            raise ValueError(f"{self.sleeve}: min_count must be >= 1")
        if self.max_count < self.min_count:
            raise ValueError(f"{self.sleeve}: max_count below min_count")


@dataclass(frozen=True)
class ETFUniverseConfig:
    selection_counts: tuple[HoldingCountRange, ...]
    minimum_history_days: int = 252

    def __post_init__(self) -> None:
        if self.minimum_history_days < 1:
            raise ValueError("minimum_history_days must be positive")
        _require_unique([item.sleeve for item in self.selection_counts], "selection_counts")

    def counts_by_sleeve(self) -> dict[str, HoldingCountRange]:
        return {item.sleeve: item for item in self.selection_counts}


@dataclass(frozen=True)
class RiskGateConfig:
    absolute_momentum_months: tuple[int, ...]
    overbought_rsi14: float
    overbought_stddevs: float
    overbought_ma50_multiple: float
    overbought_percentile: float
    min_adv_usd: float
    min_aum_usd: float
    max_bid_ask_spread_pct: float
    min_price_history_days: int
    sortino_min_downside_obs_12m: int
    sortino_min_downside_obs_6m: int
    sortino_min_downside_obs_3m: int

    def __post_init__(self) -> None:
        if not self.absolute_momentum_months:
            raise ValueError("absolute_momentum_months cannot be empty")
        _require_pct(self.max_bid_ask_spread_pct, "max_bid_ask_spread_pct")
        if min(self.min_adv_usd, self.min_aum_usd, self.min_price_history_days) <= 0:
            raise ValueError("risk gate minimums must be positive")


@dataclass(frozen=True)
class RankingWeights:
    sortino_level: float
    sortino_trend: float
    total_return: float
    max_drawdown: float
    realized_volatility: float
    vehicle_quality: float
    diversification: float

    def __post_init__(self) -> None:
        total = sum(self.as_dict().values())
        if abs(total - 1.0) > PCT_TOLERANCE:
            raise ValueError(f"ranking weights sum to {total}, not 1")

    def as_dict(self) -> dict[str, float]:
        return {
            "sortino_level": self.sortino_level,
            "sortino_trend": self.sortino_trend,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "realized_volatility": self.realized_volatility,
            "vehicle_quality": self.vehicle_quality,
            "diversification": self.diversification,
        }


@dataclass(frozen=True)
class RiskBudgetCaps:
    hard_volatility_caps: tuple[tuple[str, float], ...]
    max_single_position_weight: float
    max_single_etf_average_portfolio_value: float
    duplicate_correlation_threshold: float
    duplicate_combined_exposure_cap: float
    low_volatility_floor_ratio: float

    def __post_init__(self) -> None:
        _require_unique([item[0] for item in self.hard_volatility_caps], "hard_volatility_caps")
        for _, cap in self.hard_volatility_caps:
            _require_pct(cap, "hard_volatility_cap")
        for value_name in (
            "max_single_position_weight",
            "max_single_etf_average_portfolio_value",
            "duplicate_combined_exposure_cap",
        ):
            _require_pct(getattr(self, value_name), value_name)
        if not 0 <= self.duplicate_correlation_threshold <= 1:
            raise ValueError("duplicate_correlation_threshold must be between 0 and 1")

    def caps_by_regime(self) -> dict[str, float]:
        return dict(self.hard_volatility_caps)


@dataclass(frozen=True)
class RebalancingThresholds:
    replacement_margins: tuple[tuple[str, float], ...]
    high_turnover_threshold: float
    high_turnover_margin_addon: float
    minimum_trade_weight: float
    max_deferred_weeks: int

    def __post_init__(self) -> None:
        _require_unique([item[0] for item in self.replacement_margins], "replacement_margins")
        if self.high_turnover_threshold < 0:
            raise ValueError("high_turnover_threshold must be non-negative")
        _require_pct(self.minimum_trade_weight, "minimum_trade_weight")
        if self.max_deferred_weeks < 1:
            raise ValueError("max_deferred_weeks must be positive")

    def margins_by_regime(self) -> dict[str, float]:
        return dict(self.replacement_margins)


@dataclass(frozen=True)
class TradeQualityThresholds:
    component_weights: "TradeQualityComponentWeights"
    thresholds: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        _require_unique([item[0] for item in self.thresholds], "trade_quality_thresholds")

    def thresholds_by_regime(self) -> dict[str, float]:
        return dict(self.thresholds)


@dataclass(frozen=True)
class TradeQualityComponentWeights:
    score_gap: float
    execution_cost: float
    regime_alignment: float
    liquidity_quality: float
    timing: float

    def __post_init__(self) -> None:
        total = sum(self.as_dict().values())
        if abs(total - 1.0) > PCT_TOLERANCE:
            raise ValueError(f"trade-quality weights sum to {total}, not 1")

    def as_dict(self) -> dict[str, float]:
        return {
            "score_gap": self.score_gap,
            "execution_cost": self.execution_cost,
            "regime_alignment": self.regime_alignment,
            "liquidity_quality": self.liquidity_quality,
            "timing": self.timing,
        }


@dataclass(frozen=True)
class BacktestSettings:
    initial_training_years: int
    walk_forward_step_weeks: int
    first_oos_year: int
    risk_free_rate: float

    def __post_init__(self) -> None:
        if min(self.initial_training_years, self.walk_forward_step_weeks, self.first_oos_year) <= 0:
            raise ValueError("backtest settings must be positive")


@dataclass(frozen=True)
class RaceConfig:
    regimes: tuple[str, ...]
    sleeves: tuple[str, ...]
    allocations: tuple[RegimeAllocation, ...]
    drift_bands: tuple[DriftBand, ...]
    universe: ETFUniverseConfig
    risk_gates: RiskGateConfig
    ranking_weights: RankingWeights
    risk_budget: RiskBudgetCaps
    rebalancing: RebalancingThresholds
    trade_quality: TradeQualityThresholds
    backtest: BacktestSettings

    def __post_init__(self) -> None:
        _require_unique(self.regimes, "regimes")
        _require_unique(self.sleeves, "sleeves")
        _require_unique([item.regime for item in self.allocations], "allocations")
        _require_unique([item.sleeve for item in self.drift_bands], "drift_bands")
        if set(item.regime for item in self.allocations) != set(self.regimes):
            raise ValueError("allocations must cover every regime exactly once")
        if set(item.sleeve for item in self.drift_bands) != set(self.sleeves):
            raise ValueError("drift_bands must cover every sleeve exactly once")
        for allocation in self.allocations:
            if set(item.sleeve for item in allocation.sleeves) != set(self.sleeves):
                raise ValueError(f"{allocation.regime}: allocation must cover every sleeve")

    def allocations_by_regime(self) -> dict[str, RegimeAllocation]:
        return {item.regime: item for item in self.allocations}


def _require_pct(value: float, name: str) -> None:
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100")


def _require_unique(values: Any, name: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{name} contains duplicates")
