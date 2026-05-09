"""Deterministic JSON summary output."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from race_engine.audit.schema import AUDIT_SCHEMA_VERSION, MIGRATION_NOTE


SUMMARY_BLOCKS: tuple[str, ...] = (
    "regime",
    "targets",
    "eligible_universe",
    "gates",
    "rankings",
    "construction",
    "risk_budget",
    "rebalance",
    "trade_quality",
    "order_list",
    "validation_flags",
)


def build_summary_json(blocks: dict[str, Any]) -> OrderedDict[str, Any]:
    output: OrderedDict[str, Any] = OrderedDict()
    output["schema_version"] = AUDIT_SCHEMA_VERSION
    output["migration_note"] = MIGRATION_NOTE
    for block in SUMMARY_BLOCKS:
        output[block] = blocks.get(block, {})
    return output


def dumps_summary(blocks: dict[str, Any]) -> str:
    return json.dumps(build_summary_json(blocks), indent=2, sort_keys=False)

