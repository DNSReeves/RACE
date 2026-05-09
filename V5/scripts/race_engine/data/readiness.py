"""Readiness validation for RACE data inputs."""

from __future__ import annotations

from datetime import date
from typing import Mapping

from .macro_loader import REQUIRED_TIER1_SERIES
from .models import MacroObservation, ReadinessResult
from .quality import evaluate_tier1_series


def evaluate_tier1_readiness(
    observations: Mapping[str, MacroObservation | None],
    as_of: date,
    fallbacks: Mapping[str, str] | None = None,
) -> ReadinessResult:
    fallback_map = fallbacks or {}
    missing: list[str] = []
    events = []

    for series_name in REQUIRED_TIER1_SERIES:
        observation = observations.get(series_name)
        result = evaluate_tier1_series(
            series_name=series_name,
            last_valid_date=None if observation is None else observation.date,
            as_of=as_of,
            fallback_applied=fallback_map.get(series_name),
        )
        events.extend(result.events)
        if not result.eligible:
            missing.append(series_name)

    return ReadinessResult(
        can_execute=not missing,
        degraded=bool(events),
        missing_tier1=tuple(missing),
        events=tuple(events),
    )

