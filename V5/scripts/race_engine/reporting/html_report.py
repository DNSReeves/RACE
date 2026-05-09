"""HTML report renderer for manual review."""

from __future__ import annotations

from html import escape
from typing import Any

from .markdown_report import render_markdown_report


def render_html_report(blocks: dict[str, Any], diagnostic_only: bool = True) -> str:
    markdown = render_markdown_report(blocks, diagnostic_only)
    body = "<br>\n".join(escape(line) for line in markdown.splitlines())
    return f"<!doctype html><html><head><meta charset=\"utf-8\"><title>RACE Engine Report</title></head><body>{body}</body></html>"

