"""JSONL audit ledger writer."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import AuditRecord


class JsonlAuditLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: AuditRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> tuple[dict, ...]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return tuple(json.loads(line) for line in handle if line.strip())

