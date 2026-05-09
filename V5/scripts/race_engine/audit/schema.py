"""Stable audit schema for RACE outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


AUDIT_SCHEMA_VERSION = "race.audit.v1"
MIGRATION_NOTE = "Initial RACE audit schema; future migrations must preserve event_type and event_id."

STABLE_EVENT_TYPES: tuple[str, ...] = (
    "DATA_STALE_UNAVAILABLE",
    "DEGRADED_MODE",
    "REGIME_SIGNALS",
    "REGIME_TRANSITION",
    "RECOVERY_TRIGGER",
    "BLENDED_TARGETS",
    "FALLBACK_EVENT",
    "GATE_FAILURE",
    "ETF_SCORE",
    "REPLACEMENT_DECISION",
    "RISK_BUDGET_CAP",
    "TRADE_QUALITY_DEFERRAL",
    "EXECUTED_ORDER_LIST_ITEM",
    "WEIGHT_SUM_ERROR",
)


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    event_type: str
    severity: str
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AUDIT_SCHEMA_VERSION
    migration_note: str = MIGRATION_NOTE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.event_type not in STABLE_EVENT_TYPES:
            raise ValueError(f"unsupported audit event_type: {self.event_type}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "migration_note": self.migration_note,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "created_at": self.created_at,
            "payload": dict(self.payload),
        }

