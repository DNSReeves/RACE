"""Held ETF mandatory review flags."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewFlag:
    ticker: str
    flag_type: str
    mandatory: bool
    reasons: tuple[str, ...]


def review_flags_for_gate_report(ticker: str, gate_failures: dict[str, tuple[str, ...]], held: bool) -> tuple[ReviewFlag, ...]:
    if not held:
        return ()
    flags = []
    if gate_failures.get("gate1"):
        flags.append(ReviewFlag(ticker, "MANDATORY_REPLACEMENT_REVIEW_GATE1", True, gate_failures["gate1"]))
    if gate_failures.get("gate3"):
        flags.append(ReviewFlag(ticker, "MANDATORY_REPLACEMENT_REVIEW_GATE3", True, gate_failures["gate3"]))
    if gate_failures.get("gate2"):
        flags.append(ReviewFlag(ticker, "HEIGHTENED_MONITORING_OVERBOUGHT", False, gate_failures["gate2"]))
    return tuple(flags)

