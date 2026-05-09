"""Rebalance trigger priority handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class TriggerPriority(IntEnum):
    CONFIRMED_REGIME_TRANSITION = 1
    HELD_FAILS_GATE1 = 2
    HELD_FAILS_GATE3 = 3
    SLEEVE_DRIFT = 4
    REPLACEMENT_THRESHOLD = 5
    QUARTERLY_FULL_REVIEW = 6


@dataclass(frozen=True)
class RebalanceTrigger:
    ticker: str
    priority: TriggerPriority
    reason: str


def batch_triggers(triggers: tuple[RebalanceTrigger, ...]) -> tuple[RebalanceTrigger, ...]:
    return tuple(sorted(triggers, key=lambda item: (item.priority, item.ticker, item.reason)))


def quality_score_applies(priority: TriggerPriority) -> bool:
    return priority in {TriggerPriority.SLEEVE_DRIFT, TriggerPriority.REPLACEMENT_THRESHOLD}

