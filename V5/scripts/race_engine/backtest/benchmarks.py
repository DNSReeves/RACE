"""Benchmark return helpers."""

from __future__ import annotations

from typing import Sequence


def spy_benchmark(spy_returns: Sequence[float]) -> tuple[float, ...]:
    return tuple(spy_returns)


def sixty_forty_benchmark(spy_returns: Sequence[float], ief_returns: Sequence[float]) -> tuple[float, ...]:
    length = min(len(spy_returns), len(ief_returns))
    return tuple(0.60 * spy_returns[idx] + 0.40 * ief_returns[idx] for idx in range(length))

