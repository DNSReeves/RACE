"""Concentration and duplicate-risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.config.constants import DEFAULT_CONFIG
from race_engine.scoring.diversification import correlation


@dataclass(frozen=True)
class ConcentrationIssue:
    issue_type: str
    tickers: tuple[str, ...]
    exposure: float
    limit: float


def concentration_issues(
    weights: dict[str, float],
    returns_by_ticker: dict[str, tuple[float, ...]] | None = None,
) -> tuple[ConcentrationIssue, ...]:
    cfg = DEFAULT_CONFIG.risk_budget
    issues: list[ConcentrationIssue] = []
    for ticker, weight in weights.items():
        if weight > cfg.max_single_position_weight:
            issues.append(ConcentrationIssue("MAX_SINGLE_POSITION", (ticker,), weight, cfg.max_single_position_weight))
    if returns_by_ticker:
        tickers = list(weights)
        for i, left in enumerate(tickers):
            for right in tickers[i + 1 :]:
                if left not in returns_by_ticker or right not in returns_by_ticker:
                    continue
                corr = correlation(returns_by_ticker[left], returns_by_ticker[right])
                exposure = weights[left] + weights[right]
                if corr > cfg.duplicate_correlation_threshold and exposure > cfg.duplicate_combined_exposure_cap:
                    issues.append(
                        ConcentrationIssue("DUPLICATE_CORRELATION", (left, right), exposure, cfg.duplicate_combined_exposure_cap)
                    )
    return tuple(issues)

