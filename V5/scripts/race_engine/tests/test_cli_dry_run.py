import json

from add_trim_sell_hold import main as atsh_main
from race_engine.execution.cli import main


def test_existing_behavior_unchanged_without_flag(capsys) -> None:
    assert atsh_main([]) == 0
    assert "RACE engine disabled" in capsys.readouterr().out


def test_dry_run_order_list_generated_but_not_transmitted(tmp_path) -> None:
    positions = tmp_path / "positions.csv"
    positions.write_text("ticker,current_weight\nSPY,10\n", encoding="utf-8")

    assert main([
        "--race-engine-enable",
        "--race-current-positions-csv",
        str(positions),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
    ]) == 0

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert data["diagnostic_only"] is False
    assert data["orders"][0]["ticker"] == "SPY"
    assert (tmp_path / "race_ats_handoff.md").exists()


def test_validation_fail_blocks_actionable_labeling(tmp_path) -> None:
    assert main([
        "--race-engine-enable",
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "FAIL",
    ]) == 0

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert data["diagnostic_only"] is True


def test_warn_requires_explicit_allow_flag(tmp_path) -> None:
    main(["--race-engine-enable", "--race-output-folder", str(tmp_path), "--race-validation-status", "WARN"])
    blocked = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert blocked["diagnostic_only"] is True

    main([
        "--race-engine-enable",
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "WARN",
        "--race-allow-warn-dry-run",
    ])
    allowed = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert allowed["diagnostic_only"] is False

