import json

from race_engine.reporting.html_report import render_html_report
from race_engine.reporting.json_report import SUMMARY_BLOCKS, dumps_summary
from race_engine.reporting.markdown_report import render_markdown_report


def test_json_report_has_deterministic_keys_and_schema_version() -> None:
    rendered = dumps_summary({"regime": {"confirmed": "neutral"}})
    data = json.loads(rendered)

    assert list(data.keys()) == ["schema_version", "migration_note", *SUMMARY_BLOCKS]
    assert data["regime"]["confirmed"] == "neutral"


def test_markdown_report_shows_diagnostic_and_actionable_sections() -> None:
    report = render_markdown_report(
        {"order_list": [{"ticker": "SPY"}], "fallbacks": {"synthetic": "IEF/GLD"}},
        diagnostic_only=True,
    )

    assert "Diagnostic-Only Section" in report
    assert "Actionable Section" in report
    assert "Fallbacks and Synthetic Substitutions" in report
    assert "diagnostic_only" in report


def test_html_report_renders_reviewable_document() -> None:
    html = render_html_report({"regime": {"confirmed": "neutral"}})

    assert html.startswith("<!doctype html>")
    assert "RACE Engine Report" in html

