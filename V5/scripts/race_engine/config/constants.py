"""Immutable default constants for the RACE engine."""

from __future__ import annotations

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


REGIMES: tuple[str, ...] = (
    "risk_on",
    "neutral",
    "risk_off",
    "inflation_stress",
    "cash_defensive",
)

SLEEVES: tuple[str, ...] = (
    "us_equity_core",
    "us_equity_factor",
    "intl_equity",
    "fixed_income",
    "real_assets",
    "crisis_alpha",
    "cash",
)

_TARGETS: dict[str, tuple[float, ...]] = {
    "risk_on": (40.0, 20.0, 15.0, 10.0, 5.0, 5.0, 5.0),
    "neutral": (30.0, 15.0, 12.0, 18.0, 8.0, 10.0, 7.0),
    "risk_off": (15.0, 10.0, 10.0, 25.0, 10.0, 15.0, 15.0),
    "inflation_stress": (20.0, 12.0, 10.0, 10.0, 28.0, 12.0, 8.0),
    "cash_defensive": (5.0, 5.0, 5.0, 25.0, 5.0, 20.0, 35.0),
}

_SLEEVE_MIN_MAX: dict[str, tuple[float, float]] = {
    "us_equity_core": (0.0, 50.0),
    "us_equity_factor": (0.0, 30.0),
    "intl_equity": (0.0, 25.0),
    "fixed_income": (5.0, 35.0),
    "real_assets": (0.0, 35.0),
    "crisis_alpha": (0.0, 25.0),
    "cash": (0.0, 50.0),
}

DEFAULT_ALLOCATIONS: tuple[RegimeAllocation, ...] = tuple(
    RegimeAllocation(
        regime=regime,
        sleeves=tuple(
            SleeveAllocation(
                sleeve=sleeve,
                target=target,
                min_weight=_SLEEVE_MIN_MAX[sleeve][0],
                max_weight=_SLEEVE_MIN_MAX[sleeve][1],
            )
            for sleeve, target in zip(SLEEVES, targets)
        ),
    )
    for regime, targets in _TARGETS.items()
)

DEFAULT_DRIFT_BANDS: tuple[DriftBand, ...] = (
    DriftBand("us_equity_core", 5.0),
    DriftBand("us_equity_factor", 4.0),
    DriftBand("intl_equity", 4.0),
    DriftBand("fixed_income", 4.0),
    DriftBand("real_assets", 4.0),
    DriftBand("crisis_alpha", 4.0),
    DriftBand("cash", 3.0),
)

DEFAULT_UNIVERSE = ETFUniverseConfig(
    selection_counts=(
        HoldingCountRange("us_equity_core", 1, 2),
        HoldingCountRange("us_equity_factor", 2, 2),
        HoldingCountRange("intl_equity", 1, 2),
        HoldingCountRange("fixed_income", 2, 3),
        HoldingCountRange("real_assets", 1, 2),
        HoldingCountRange("crisis_alpha", 1, 2),
        HoldingCountRange("cash", 1, 1),
    ),
    minimum_history_days=252,
)

DEFAULT_RISK_GATES = RiskGateConfig(
    absolute_momentum_months=(3, 6),
    overbought_rsi14=72.0,
    overbought_stddevs=2.0,
    overbought_ma50_multiple=1.12,
    overbought_percentile=95.0,
    min_adv_usd=25_000_000.0,
    min_aum_usd=100_000_000.0,
    max_bid_ask_spread_pct=0.25,
    min_price_history_days=252,
    sortino_min_downside_obs_12m=10,
    sortino_min_downside_obs_6m=5,
    sortino_min_downside_obs_3m=3,
)

DEFAULT_RANKING_WEIGHTS = RankingWeights(
    sortino_level=0.25,
    sortino_trend=0.15,
    total_return=0.20,
    max_drawdown=0.15,
    realized_volatility=0.10,
    vehicle_quality=0.10,
    diversification=0.05,
)

DEFAULT_RISK_BUDGET = RiskBudgetCaps(
    hard_volatility_caps=(
        ("risk_on", 16.0),
        ("neutral", 14.0),
        ("risk_off", 12.0),
        ("inflation_stress", 14.0),
        ("cash_defensive", 10.0),
    ),
    max_single_position_weight=25.0,
    max_single_etf_average_portfolio_value=30.0,
    duplicate_correlation_threshold=0.95,
    duplicate_combined_exposure_cap=25.0,
    low_volatility_floor_ratio=0.70,
)

DEFAULT_REBALANCING = RebalancingThresholds(
    replacement_margins=(
        ("risk_on", 0.40),
        ("neutral", 0.50),
        ("risk_off", 0.65),
        ("inflation_stress", 0.60),
        ("cash_defensive", 0.75),
    ),
    high_turnover_threshold=150.0,
    high_turnover_margin_addon=0.15,
    minimum_trade_weight=0.50,
    max_deferred_weeks=4,
)

DEFAULT_TRADE_QUALITY = TradeQualityThresholds(
    component_weights=TradeQualityComponentWeights(
        score_gap=0.30,
        execution_cost=0.25,
        regime_alignment=0.20,
        liquidity_quality=0.15,
        timing=0.10,
    ),
    thresholds=(
        ("risk_on", 0.40),
        ("neutral", 0.45),
        ("risk_off", 0.55),
        ("inflation_stress", 0.50),
        ("cash_defensive", 0.60),
    ),
)

DEFAULT_BACKTEST = BacktestSettings(
    initial_training_years=5,
    walk_forward_step_weeks=13,
    first_oos_year=2010,
    risk_free_rate=0.03,
)

DEFAULT_CONFIG = RaceConfig(
    regimes=REGIMES,
    sleeves=SLEEVES,
    allocations=DEFAULT_ALLOCATIONS,
    drift_bands=DEFAULT_DRIFT_BANDS,
    universe=DEFAULT_UNIVERSE,
    risk_gates=DEFAULT_RISK_GATES,
    ranking_weights=DEFAULT_RANKING_WEIGHTS,
    risk_budget=DEFAULT_RISK_BUDGET,
    rebalancing=DEFAULT_REBALANCING,
    trade_quality=DEFAULT_TRADE_QUALITY,
    backtest=DEFAULT_BACKTEST,
)
