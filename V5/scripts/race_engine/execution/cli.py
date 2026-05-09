"""Standalone RACE dry-run CLI."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from race_engine.execution.pipeline import run_standalone_pipeline

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone RACE Engine dry-run")
    parser.add_argument("--race-engine-enable", action="store_true")
    parser.add_argument("--race-config")
    parser.add_argument("--race-market-data-cache")
    parser.add_argument("--race-current-positions-csv")
    parser.add_argument("--race-output-folder", default="race_engine_out")
    parser.add_argument("--race-validation-status", choices=("PASS", "WARN", "FAIL"), default="FAIL")
    parser.add_argument("--race-allow-warn-dry-run", action="store_true")
    parser.add_argument("--race-write-atsh-handoff", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.race_engine_enable:
        return 0
    output_folder = Path(args.race_output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    positions = _read_positions(Path(args.race_current_positions_csv)) if args.race_current_positions_csv else {}
    artifact = run_standalone_pipeline(
        config_path=args.race_config,
        market_data_cache=args.race_market_data_cache,
        current_positions=positions,
        validation_status=args.race_validation_status,
        allow_warn_dry_run=args.race_allow_warn_dry_run,
    )
    (output_folder / "race_order_list.json").write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    if args.race_write_atsh_handoff:
        from race_engine.reporting.ats_handoff import race_dry_run_panel

        (output_folder / "race_ats_handoff.md").write_text(race_dry_run_panel(artifact), encoding="utf-8")
    return 0


def _read_positions(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row["ticker"]: float(row.get("current_weight", 0.0))
            for row in reader
            if row.get("ticker")
        }


if __name__ == "__main__":
    raise SystemExit(main())
