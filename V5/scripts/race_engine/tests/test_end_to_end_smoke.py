import json

from race_engine.backtest.ablations import ablation_configs
from race_engine.reporting.json_report import dumps_summary
from race_engine.reporting.markdown_report import render_markdown_report
from race_engine.execution.cli import main as race_cli_main


def test_end_to_end_smoke_report_generation_and_cli(tmp_path) -> None:
    summary = dumps_summary({"regime": {"confirmed": "neutral"}, "validation_flags": {"status": "WARN"}})
    markdown = render_markdown_report({"regime": {"confirmed": "neutral"}}, diagnostic_only=True)

    assert "schema_version" in summary
    assert "Diagnostic-Only Section" in markdown
    assert ablation_configs()

    positions = tmp_path / "positions.csv"
    positions.write_text("ticker,current_weight\nSPY,10\n", encoding="utf-8")
    assert race_cli_main([
        "--race-engine-enable",
        "--race-current-positions-csv",
        str(positions),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "FAIL",
    ]) == 0

    artifact = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert artifact["diagnostic_only"] is True
    assert artifact["orders"][0]["trade_quality_status"] == "DIAGNOSTIC_ONLY"

