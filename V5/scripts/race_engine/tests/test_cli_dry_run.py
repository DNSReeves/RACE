import json

from race_engine.execution.cli import main


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
    assert not (tmp_path / "race_ats_handoff.md").exists()


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


def test_atsh_handoff_is_optional_downstream_output(tmp_path) -> None:
    main([
        "--race-engine-enable",
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
        "--race-write-atsh-handoff",
    ])

    assert (tmp_path / "race_ats_handoff.md").exists()
