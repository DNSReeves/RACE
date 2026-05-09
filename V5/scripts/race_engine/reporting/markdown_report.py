"""Markdown report renderer for manual review."""

from __future__ import annotations

from typing import Any

from .json_report import build_summary_json


def render_markdown_report(blocks: dict[str, Any], diagnostic_only: bool = True) -> str:
    summary = build_summary_json(blocks)
    mode = "Diagnostic-only" if diagnostic_only else "Actionable dry-run"
    lines = [
        "# RACE Engine Report",
        "",
        f"Schema version: `{summary['schema_version']}`",
        "",
        f"Mode: **{mode}**",
        "",
        "## Diagnostic-Only Section",
        "",
        _format_block("Regime", summary["regime"]),
        _format_block("Targets", summary["targets"]),
        _format_block("Fallbacks and Synthetic Substitutions", blocks.get("fallbacks", {})),
        "",
        "## Actionable Section",
        "",
        _format_block("Order List", summary["order_list"] if not diagnostic_only else {"diagnostic_only": True}),
    ]
    return "\n".join(lines)


def _format_block(title: str, block: Any) -> str:
    return f"### {title}\n\n```json\n{block}\n```"

