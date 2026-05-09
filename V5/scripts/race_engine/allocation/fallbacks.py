"""Graduated sleeve fallback hierarchy."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.audit.events import AuditEvent
from race_engine.config.constants import DEFAULT_CONFIG

from .sleeves import SISTER_SLEEVES


@dataclass(frozen=True)
class FallbackInput:
    sleeve: str
    target_weight: float
    eligible_tickers: tuple[str, ...]
    gate2_relaxed_tickers: tuple[str, ...]
    sister_sleeve_tickers: dict[str, tuple[str, ...]]
    failure_reason: str


@dataclass(frozen=True)
class FallbackResult:
    sleeve: str
    selected_tickers: tuple[str, ...]
    level: str | None
    event: AuditEvent | None


def apply_fallback(input_data: FallbackInput) -> FallbackResult:
    counts = DEFAULT_CONFIG.universe.counts_by_sleeve()[input_data.sleeve]
    if len(input_data.eligible_tickers) >= counts.min_count:
        return FallbackResult(input_data.sleeve, input_data.eligible_tickers, None, None)
    if input_data.eligible_tickers:
        return _event_result(input_data, input_data.eligible_tickers, "PARTIAL", input_data.sleeve)
    if len(input_data.gate2_relaxed_tickers) >= counts.min_count:
        return _event_result(input_data, input_data.gate2_relaxed_tickers, "L1_RELAX_GATE2", input_data.sleeve)
    for sister in SISTER_SLEEVES.get(input_data.sleeve, ()):
        tickers = input_data.sister_sleeve_tickers.get(sister, ())
        if tickers:
            return _event_result(input_data, tickers, "L2_SISTER_SLEEVE", sister)
    return _event_result(input_data, ("BIL",), "L3_CASH_REDIRECTION", "cash")


def _event_result(
    input_data: FallbackInput,
    tickers: tuple[str, ...],
    level: str,
    resulting_sleeve: str,
) -> FallbackResult:
    event = AuditEvent(
        event_type="SLEEVE_LOSS" if level == "L3_CASH_REDIRECTION" else "FALLBACK_EVENT",
        severity="WARN",
        series_name=input_data.sleeve,
        fallback_applied=level,
        details={
            "original_sleeve": input_data.sleeve,
            "target_weight": input_data.target_weight,
            "failure_reason": input_data.failure_reason,
            "level": level,
            "resulting_allocation": {resulting_sleeve: list(tickers)},
        },
    )
    return FallbackResult(resulting_sleeve, tickers, level, event)

