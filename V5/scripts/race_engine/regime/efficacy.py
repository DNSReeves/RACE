"""Adaptive regime-signal efficacy weighting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import fmean
from typing import Mapping, Sequence

from race_engine.audit.events import AuditEvent
from race_engine.regime.engine import SIGNAL_NAMES


TRAILING_WINDOW_WEEKS = 156


@dataclass(frozen=True)
class EfficacyResult:
    enabled: bool
    weights: dict[str, float]
    events: tuple[AuditEvent, ...]
    updated: bool


def base_signal_weights() -> dict[str, float]:
    return {name: 1.0 / len(SIGNAL_NAMES) for name in SIGNAL_NAMES}


def adaptive_signal_weights(
    signal_history: Mapping[str, Sequence[int]],
    forward_spy_returns_13w: Sequence[float],
    evaluation_date: date,
    last_update_date: date | None = None,
    enabled: bool = True,
    base_weights: Mapping[str, float] | None = None,
) -> EfficacyResult:
    base = dict(base_weights or base_signal_weights())
    if not enabled:
        return EfficacyResult(False, base, (), False)
    if last_update_date is not None and _quarter_key(last_update_date) == _quarter_key(evaluation_date):
        return EfficacyResult(True, base, (), False)
    if len(forward_spy_returns_13w) < TRAILING_WINDOW_WEEKS:
        return EfficacyResult(False, base, (), False)

    adjusted: dict[str, float] = {}
    events = []
    for signal_name in SIGNAL_NAMES:
        values = tuple(signal_history.get(signal_name, ()))
        if len(values) < TRAILING_WINDOW_WEEKS:
            return EfficacyResult(False, base, (), False)
        efficacy = spearman_rank_correlation(
            values[-TRAILING_WINDOW_WEEKS:],
            forward_spy_returns_13w[-TRAILING_WINDOW_WEEKS:],
        )
        modulator = min(1.5, max(0.5, 1.0 + 0.5 * efficacy))
        adjusted_weight = base[signal_name] * modulator
        adjusted[signal_name] = adjusted_weight
        events.append(
            AuditEvent(
                event_type="REGIME_SIGNAL_EFFICACY",
                severity="INFO",
                series_name=signal_name,
                last_valid_date=evaluation_date,
                details={
                    "base_weight": base[signal_name],
                    "efficacy_score": efficacy,
                    "modulator": modulator,
                    "adjusted_weight": adjusted_weight,
                    "update_date": evaluation_date.isoformat(),
                },
            )
        )
    total = sum(adjusted.values())
    normalized = {name: weight / total for name, weight in adjusted.items()}
    normalized_events = tuple(
        AuditEvent(
            event_type=event.event_type,
            severity=event.severity,
            series_name=event.series_name,
            last_valid_date=event.last_valid_date,
            details={**event.details, "final_normalized_weight": normalized[event.series_name or ""]},
        )
        for event in events
    )
    return EfficacyResult(True, normalized, normalized_events, True)


def spearman_rank_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Spearman inputs must have matching length >= 2")
    left_ranks = _ranks(left)
    right_ranks = _ranks(right)
    return _pearson(left_ranks, right_ranks)


def _ranks(values: Sequence[float]) -> tuple[float, ...]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        rank = (cursor + end) / 2 + 1
        for idx in range(cursor, end + 1):
            ranks[ordered[idx][1]] = rank
        cursor = end + 1
    return tuple(ranks)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum((left[i] - left_mean) * (right[i] - right_mean) for i in range(len(left)))
    denominator = sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return 0.0 if denominator == 0.0 else numerator / denominator


def _quarter_key(value: date) -> tuple[int, int]:
    return value.year, (value.month - 1) // 3

