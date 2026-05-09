"""ATSH report handoff helpers for the RACE dry-run panel."""

from __future__ import annotations

from typing import Any


def race_dry_run_panel(artifact: dict[str, Any]) -> str:
    label = "diagnostic_only=true" if artifact.get("diagnostic_only") else "manual_review_ready=true"
    lines = [
        "## RACE Engine Dry Run",
        "",
        f"Validation status: `{artifact.get('validation_status')}`",
        f"Guardrail: `{label}`",
        "",
        "### Proposed Order List",
    ]
    for order in artifact.get("orders", []):
        lines.append(
            f"- {order['ticker']} {order['side']} target={order['target_weight']} current={order['current_weight']} status={order['trade_quality_status']}"
        )
    return "\n".join(lines) + "\n"

