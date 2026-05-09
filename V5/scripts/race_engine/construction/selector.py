"""ETF selection from ranked eligible candidates."""

from __future__ import annotations

from dataclasses import dataclass

from race_engine.config.constants import DEFAULT_CONFIG


@dataclass(frozen=True)
class RankedETF:
    ticker: str
    sleeve: str
    score: float


def select_top_ranked(candidates: tuple[RankedETF, ...]) -> dict[str, tuple[RankedETF, ...]]:
    by_sleeve: dict[str, list[RankedETF]] = {}
    for candidate in candidates:
        by_sleeve.setdefault(candidate.sleeve, []).append(candidate)

    selected: dict[str, tuple[RankedETF, ...]] = {}
    counts = DEFAULT_CONFIG.universe.counts_by_sleeve()
    for sleeve, items in by_sleeve.items():
        ordered = sorted(items, key=lambda item: item.score, reverse=True)
        max_count = counts[sleeve].max_count
        selected[sleeve] = tuple(ordered[:max_count])
    return selected

