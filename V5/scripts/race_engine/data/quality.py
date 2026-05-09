"""Data quality and degraded-mode rules for RACE inputs."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from race_engine.audit.events import AuditEvent, data_event

from .models import ETFMetrics, PriceBar, QualityResult


def is_stale(last_valid_date: date | None, as_of: date, max_calendar_days: int) -> bool:
    if last_valid_date is None:
        return True
    return (as_of - last_valid_date).days > max_calendar_days


def forward_fill_single_gaps(values: Iterable[float | None]) -> tuple[tuple[float | None, ...], bool]:
    filled: list[float | None] = []
    previous: float | None = None
    consecutive_gaps = 0
    manual_review = False
    for value in values:
        if value is None:
            consecutive_gaps += 1
            if consecutive_gaps == 1 and previous is not None:
                filled.append(previous)
            else:
                filled.append(None)
                manual_review = True
            continue
        consecutive_gaps = 0
        previous = value
        filled.append(value)
    return tuple(filled), manual_review


def evaluate_tier1_series(
    series_name: str,
    last_valid_date: date | None,
    as_of: date,
    fallback_applied: str | None = None,
) -> QualityResult:
    events: list[AuditEvent] = []
    if last_valid_date is None:
        events.append(
            data_event("TIER1_MISSING", "FAIL", series_name, None, fallback_applied)
        )
        return QualityResult(status="FAIL", eligible=False, events=tuple(events))
    if is_stale(last_valid_date, as_of, 2):
        severity = "WARN" if fallback_applied else "FAIL"
        events.append(
            data_event("TIER1_STALE", severity, series_name, last_valid_date, fallback_applied)
        )
        return QualityResult(status=severity, eligible=fallback_applied is not None, events=tuple(events))
    return QualityResult(status="PASS", eligible=True)


def evaluate_etf_quality(
    ticker: str,
    price_bars: tuple[PriceBar, ...],
    metrics: ETFMetrics | None,
    as_of: date,
    sleeve_median_spread: float | None = None,
) -> QualityResult:
    events: list[AuditEvent] = []
    values: dict[str, float | None] = {}

    if not price_bars:
        event = data_event("OHLCV_MISSING", "FAIL", ticker, None, None)
        return QualityResult(status="FAIL", eligible=False, events=(event,), values=values)
    if len(price_bars) < 252:
        events.append(
            data_event(
                "ETF_HISTORY_SHORT",
                "FAIL",
                ticker,
                price_bars[-1].date,
                None,
                observation_count=len(price_bars),
            )
        )
        return QualityResult(status="FAIL", eligible=False, events=tuple(events), values=values)

    if metrics is None:
        events.append(data_event("ETF_METRICS_MISSING", "WARN", ticker, price_bars[-1].date, "neutral_metrics"))
        return QualityResult(status="WARN", eligible=True, events=tuple(events), values=values)

    values["aum"] = _quality_value(
        ticker,
        "AUM_STALE",
        metrics.aum,
        metrics.as_of,
        as_of,
        max_age_days=30,
        fallback="AUM_UNVERIFIED",
        events=events,
    )
    values["expense_ratio"] = _quality_value(
        ticker,
        "EXPENSE_RATIO_STALE",
        metrics.expense_ratio,
        metrics.as_of,
        as_of,
        max_age_days=90,
        fallback="neutral_cost_score",
        events=events,
    )
    values["bid_ask_spread"] = _quality_value(
        ticker,
        "SPREAD_STALE",
        metrics.bid_ask_spread,
        metrics.as_of,
        as_of,
        max_age_days=30,
        fallback="sleeve_median_spread" if sleeve_median_spread is not None else "neutral_spread",
        events=events,
    )
    if values["bid_ask_spread"] is None:
        values["bid_ask_spread"] = sleeve_median_spread

    return QualityResult(
        status="WARN" if events else "PASS",
        eligible=True,
        events=tuple(events),
        values=values,
    )


def _quality_value(
    ticker: str,
    event_type: str,
    value: float | None,
    last_valid_date: date,
    as_of: date,
    max_age_days: int,
    fallback: str,
    events: list[AuditEvent],
) -> float | None:
    if value is None or is_stale(last_valid_date, as_of, max_age_days):
        events.append(data_event(event_type, "WARN", ticker, last_valid_date, fallback))
    return value

