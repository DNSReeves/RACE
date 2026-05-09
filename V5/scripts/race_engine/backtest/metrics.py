"""Backtest metrics for weekly return series."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import fmean, pstdev
from typing import Sequence

from race_engine.scoring.diversification import correlation


WEEKS_PER_YEAR = 52


@dataclass(frozen=True)
class BacktestMetrics:
    cagr: float
    annual_volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    drawdown_duration: int
    turnover: float
    quarterly_hit_rate: float
    win_loss_ratio: float
    transaction_cost_adjusted_return: float
    regime_hit_rate: float
    beta: float
    correlation: float


def compute_metrics(
    weekly_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    turnover: float = 0.0,
    transaction_cost_adjusted_return: float | None = None,
    regime_hits: Sequence[bool] | None = None,
    risk_free_rate: float = 0.03,
) -> BacktestMetrics:
    if not weekly_returns:
        raise ValueError("weekly_returns cannot be empty")
    equity = _equity_curve(weekly_returns)
    cagr = equity[-1] ** (WEEKS_PER_YEAR / len(weekly_returns)) - 1.0
    annual_vol = pstdev(weekly_returns) * sqrt(WEEKS_PER_YEAR) if len(weekly_returns) > 1 else 0.0
    weekly_rf = risk_free_rate / WEEKS_PER_YEAR
    excess = [value - weekly_rf for value in weekly_returns]
    sharpe = 0.0 if annual_vol == 0 else fmean(excess) * WEEKS_PER_YEAR / annual_vol
    downside = [value for value in excess if value < 0]
    downside_dev = pstdev(downside) * sqrt(WEEKS_PER_YEAR) if len(downside) > 1 else 0.0
    sortino = 0.0 if downside_dev == 0 else fmean(excess) * WEEKS_PER_YEAR / downside_dev
    max_dd, duration = _drawdown(equity)
    calmar = 0.0 if max_dd == 0 else cagr / abs(max_dd)
    wins = sum(1 for value in weekly_returns if value > 0)
    losses = sum(1 for value in weekly_returns if value < 0)
    win_loss = float(wins) if losses == 0 else wins / losses
    corr = correlation(weekly_returns, benchmark_returns)
    beta = _beta(weekly_returns, benchmark_returns)
    return BacktestMetrics(
        cagr,
        annual_vol,
        sharpe,
        sortino,
        calmar,
        max_dd,
        duration,
        turnover,
        _quarterly_hit_rate(weekly_returns),
        win_loss,
        transaction_cost_adjusted_return if transaction_cost_adjusted_return is not None else sum(weekly_returns),
        0.0 if not regime_hits else sum(1 for item in regime_hits if item) / len(regime_hits),
        beta,
        corr,
    )


def _equity_curve(returns: Sequence[float]) -> tuple[float, ...]:
    equity = 1.0
    values = []
    for value in returns:
        equity *= 1.0 + value
        values.append(equity)
    return tuple(values)


def _drawdown(equity: Sequence[float]) -> tuple[float, int]:
    peak = equity[0]
    worst = 0.0
    current_duration = 0
    worst_duration = 0
    for value in equity:
        if value >= peak:
            peak = value
            current_duration = 0
        else:
            current_duration += 1
            worst_duration = max(worst_duration, current_duration)
            worst = min(worst, value / peak - 1.0)
    return worst, worst_duration


def _quarterly_hit_rate(returns: Sequence[float]) -> float:
    chunks = [returns[idx : idx + 13] for idx in range(0, len(returns), 13)]
    hits = [sum(chunk) > 0 for chunk in chunks if chunk]
    return sum(1 for hit in hits if hit) / len(hits)


def _beta(returns: Sequence[float], benchmark: Sequence[float]) -> float:
    length = min(len(returns), len(benchmark))
    if length < 2:
        return 0.0
    x = benchmark[-length:]
    y = returns[-length:]
    mean_x = fmean(x)
    mean_y = fmean(y)
    variance = sum((value - mean_x) ** 2 for value in x)
    if variance == 0:
        return 0.0
    covariance = sum((x[idx] - mean_x) * (y[idx] - mean_y) for idx in range(length))
    return covariance / variance

