"""Structured audit events emitted by RACE components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    severity: str
    series_name: str | None = None
    last_valid_date: date | None = None
    fallback_applied: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "series_name": self.series_name,
            "last_valid_date": self.last_valid_date.isoformat() if self.last_valid_date else None,
            "fallback_applied": self.fallback_applied,
            "details": dict(self.details),
            "created_at": self.created_at.isoformat(),
        }


def data_event(
    event_type: str,
    severity: str,
    series_name: str,
    last_valid_date: date | None,
    fallback_applied: str | None,
    **details: Any,
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        severity=severity,
        series_name=series_name,
        last_valid_date=last_valid_date,
        fallback_applied=fallback_applied,
        details=details,
    )

