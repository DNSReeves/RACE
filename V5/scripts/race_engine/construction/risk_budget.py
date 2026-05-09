"""Portfolio volatility hard-cap logic."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import fmean

from race_engine.audit.events import AuditEvent
from race_engine.config.constants import DEFAULT_CONFIG


@dataclass(frozen=True)
class RiskBudgetResult:
    weights: dict[str, float]
    forecast_volatility: float
    event: AuditEvent | None


def forecast_portfolio_volatility(weights: dict[str, float], returns_by_ticker: dict[str, tuple[float, ...]]) -> float:
    tickers = [ticker for ticker in weights if ticker in returns_by_ticker]
    if not tickers:
        return 0.0
    length = min(len(returns_by_ticker[ticker]) for ticker in tickers)
    if length < 2:
        return 0.0
    weights_decimal = [weights[ticker] / 100.0 for ticker in tickers]
    matrix = [_demean(returns_by_ticker[ticker][-length:]) for ticker in tickers]
    cov = _shrunk_covariance(matrix, alpha=0.20)
    variance = 0.0
    for i, wi in enumerate(weights_decimal):
        for j, wj in enumerate(weights_decimal):
            variance += wi * wj * cov[i][j]
    return sqrt(max(variance, 0.0)) * sqrt(252)


def apply_volatility_cap(
    weights: dict[str, float],
    returns_by_ticker: dict[str, tuple[float, ...]],
    regime: str,
    cash_ticker: str = "BIL",
) -> RiskBudgetResult:
    cap = DEFAULT_CONFIG.risk_budget.caps_by_regime()[regime]
    forecast = forecast_portfolio_volatility(weights, returns_by_ticker) * 100.0
    if forecast <= cap:
        return RiskBudgetResult(weights, forecast, None)
    scale = cap / forecast
    adjusted = dict(weights)
    freed = 0.0
    for ticker, weight in weights.items():
        if ticker == cash_ticker:
            continue
        new_weight = weight * scale
        freed += weight - new_weight
        adjusted[ticker] = new_weight
    adjusted[cash_ticker] = adjusted.get(cash_ticker, 0.0) + freed
    adjusted = _normalize(adjusted)
    event = AuditEvent(
        event_type="PORTFOLIO_VOL_CAPPED",
        severity="WARN",
        series_name=regime,
        details={"forecast_volatility": forecast, "cap": cap, "scale": scale},
    )
    return RiskBudgetResult(adjusted, forecast, event)


def _demean(values: tuple[float, ...]) -> tuple[float, ...]:
    mean = fmean(values)
    return tuple(value - mean for value in values)


def _shrunk_covariance(matrix: list[tuple[float, ...]], alpha: float) -> list[list[float]]:
    n = len(matrix)
    length = len(matrix[0])
    cov = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            sample_cov = sum(matrix[i][k] * matrix[j][k] for k in range(length)) / (length - 1)
            cov[i][j] = sample_cov if i == j else (1.0 - alpha) * sample_cov
    return cov


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {ticker: round(weight * 100.0 / total, 6) for ticker, weight in weights.items()}

