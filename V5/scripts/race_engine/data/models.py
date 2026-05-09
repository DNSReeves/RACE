"""Data models used by RACE read-only adapters and quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from race_engine.audit.events import AuditEvent


@dataclass(frozen=True)
class PriceBar:
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: float


@dataclass(frozen=True)
class ETFMetrics:
    ticker: str
    as_of: date
    aum: float | None = None
    expense_ratio: float | None = None
    bid_ask_spread: float | None = None


@dataclass(frozen=True)
class MacroObservation:
    series_name: str
    date: date
    value: float


@dataclass(frozen=True)
class QualityResult:
    status: str
    eligible: bool
    events: tuple[AuditEvent, ...] = field(default_factory=tuple)
    values: dict[str, float | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessResult:
    can_execute: bool
    degraded: bool
    missing_tier1: tuple[str, ...]
    events: tuple[AuditEvent, ...]

