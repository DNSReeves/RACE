"""ETF eligibility risk gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from race_engine.config.constants import DEFAULT_CONFIG

from .indicators import (
    downside_observations,
    rolling_return_percentile,
    rolling_std,
    rsi,
    simple_moving_average,
    total_return,
)
from .review_flags import ReviewFlag, review_flags_for_gate_report


@dataclass(frozen=True)
class RiskGateInput:
    ticker: str
    adjusted_closes: tuple[float, ...]
    daily_returns: tuple[float, ...]
    adv_usd: float
    aum_usd: float
    bid_ask_spread_pct: float
    price_history_days: int
    held: bool = False


@dataclass(frozen=True)
class GateReport:
    ticker: str
    eligible_for_new_purchase: bool
    held: bool
    gate_passes: dict[str, bool]
    gate_failures: dict[str, tuple[str, ...]]
    raw_values: dict[str, float | int]
    review_flags: tuple[ReviewFlag, ...] = field(default_factory=tuple)


def evaluate_risk_gates(input_data: RiskGateInput) -> GateReport:
    gate_passes: dict[str, bool] = {}
    failures: dict[str, tuple[str, ...]] = {}
    raw: dict[str, float | int] = {}

    gate_passes["gate1"] = _gate1(input_data.adjusted_closes, failures, raw)
    gate_passes["gate2"] = _gate2(input_data.adjusted_closes, failures, raw)
    gate_passes["gate3"] = _gate3(input_data, failures, raw)
    gate_passes["gate4"] = _gate4(input_data.daily_returns, failures, raw)

    eligible = gate_passes["gate1"] and gate_passes["gate3"] and gate_passes["gate4"]
    if not input_data.held:
        eligible = eligible and gate_passes["gate2"]

    return GateReport(
        ticker=input_data.ticker,
        eligible_for_new_purchase=eligible,
        held=input_data.held,
        gate_passes=gate_passes,
        gate_failures=failures,
        raw_values=raw,
        review_flags=review_flags_for_gate_report(input_data.ticker, failures, input_data.held),
    )


def _gate1(closes: Sequence[float], failures: dict[str, tuple[str, ...]], raw: dict[str, float | int]) -> bool:
    ret_3m = total_return(closes, 63)
    ret_6m = total_return(closes, 126)
    sma200 = simple_moving_average(closes, 200)
    close = closes[-1]
    raw.update({"ret_3m": ret_3m, "ret_6m": ret_6m, "close_vs_sma200": close / sma200})
    reasons = []
    if ret_3m <= 0:
        reasons.append("3m_return_nonpositive")
    if ret_6m <= 0:
        reasons.append("6m_return_nonpositive")
    if close <= sma200:
        reasons.append("close_below_200d_sma")
    if reasons:
        failures["gate1"] = tuple(reasons)
    return not reasons


def _gate2(closes: Sequence[float], failures: dict[str, tuple[str, ...]], raw: dict[str, float | int]) -> bool:
    rsi14 = rsi(closes, 14)
    ma20 = simple_moving_average(closes, 20)
    std20 = rolling_std(closes, 20)
    ma50 = simple_moving_average(closes, 50)
    ret21 = total_return(closes, 21)
    percentile = rolling_return_percentile(closes, 21, 756, ret21)
    raw.update({"rsi14": rsi14, "ma20_plus_2std": ma20 + 2.0 * std20, "ma50_multiple": ma50 * 1.12, "ret21_percentile": percentile})
    conditions = []
    if rsi14 > 72:
        conditions.append("rsi14_gt_72")
    if closes[-1] > ma20 + 2.0 * std20:
        conditions.append("close_gt_20dma_plus_2std")
    if closes[-1] > ma50 * 1.12:
        conditions.append("close_gt_50dma_1p12")
    if percentile > 95:
        conditions.append("ret21_gt_95th_percentile")
    if len(conditions) >= 2:
        failures["gate2"] = tuple(conditions)
        return False
    return True


def _gate3(input_data: RiskGateInput, failures: dict[str, tuple[str, ...]], raw: dict[str, float | int]) -> bool:
    cfg = DEFAULT_CONFIG.risk_gates
    raw.update(
        {
            "adv_usd": input_data.adv_usd,
            "aum_usd": input_data.aum_usd,
            "bid_ask_spread_pct": input_data.bid_ask_spread_pct,
            "price_history_days": input_data.price_history_days,
        }
    )
    reasons = []
    if input_data.adv_usd < cfg.min_adv_usd:
        reasons.append("adv_below_25m")
    if input_data.aum_usd < cfg.min_aum_usd:
        reasons.append("aum_below_100m")
    if input_data.bid_ask_spread_pct > cfg.max_bid_ask_spread_pct:
        reasons.append("spread_above_0p25pct")
    if input_data.price_history_days < cfg.min_price_history_days:
        reasons.append("price_history_below_252")
    if reasons:
        failures["gate3"] = tuple(reasons)
    return not reasons


def _gate4(returns: Sequence[float], failures: dict[str, tuple[str, ...]], raw: dict[str, float | int]) -> bool:
    windows = {"12m": 252, "6m": 126, "3m": 63}
    minimums = {"12m": 10, "6m": 5, "3m": 3}
    passing = []
    for label, window in windows.items():
        sample = returns[-window:] if len(returns) >= window else returns
        obs = downside_observations(sample)
        raw[f"sortino_downside_obs_{label}"] = obs
        if obs >= minimums[label]:
            passing.append(label)
    if not passing:
        failures["gate4"] = ("all_sortino_horizons_insufficient_downside_obs",)
        return False
    raw["sortino_horizons_used"] = len(passing)
    return True

