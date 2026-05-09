import pytest

from race_engine.audit.logger import JsonlAuditLogger, read_jsonl
from race_engine.audit.schema import AUDIT_SCHEMA_VERSION, AuditRecord


def test_audit_record_has_stable_schema_version_and_event_type() -> None:
    record = AuditRecord("evt-1", "REGIME_SIGNALS", "INFO", {"score": 0.1})

    data = record.as_dict()
    assert data["schema_version"] == AUDIT_SCHEMA_VERSION
    assert data["event_type"] == "REGIME_SIGNALS"
    assert "migration_note" in data


def test_audit_record_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError):
        AuditRecord("evt-1", "UNKNOWN", "INFO")


def test_jsonl_logger_round_trips(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    logger = JsonlAuditLogger(path)
    logger.append(AuditRecord("evt-1", "FALLBACK_EVENT", "WARN", {"fallback": "cash"}))

    rows = read_jsonl(path)
    assert rows[0]["event_id"] == "evt-1"
    assert rows[0]["payload"]["fallback"] == "cash"

