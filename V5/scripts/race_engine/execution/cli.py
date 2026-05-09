"""RACE dry-run CLI integration."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from race_engine.execution.order_list import proposed_order
from race_engine.reporting.ats_handoff import race_dry_run_panel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RACE Engine dry-run")
    parser.add_argument("--race-engine-enable", action="store_true")
    parser.add_argument("--race-config")
    parser.add_argument("--race-market-data-cache")
    parser.add_argument("--race-current-positions-csv")
    parser.add_argument("--race-output-folder", default="race_engine_out")
    parser.add_argument("--race-validation-status", choices=("PASS", "WARN", "FAIL"), default="FAIL")
    parser.add_argument("--race-allow-warn-dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.race_engine_enable:
        return 0
    output_folder = Path(args.race_output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    diagnostic_only = args.race_validation_status == "FAIL" or (
        args.race_validation_status == "WARN" and not args.race_allow_warn_dry_run
    )
    positions = _read_positions(Path(args.race_current_positions_csv)) if args.race_current_positions_csv else {}
    orders = [
        proposed_order(
            ticker=ticker,
            target_weight=current_weight,
            current_weight=current_weight,
            portfolio_value=100_000.0,
            price=100.0,
            reason_code="DRY_RUN_NO_CHANGE",
            priority="DIAGNOSTIC",
            trade_quality_status="DIAGNOSTIC_ONLY" if diagnostic_only else "READY_FOR_MANUAL_REVIEW",
        ).__dict__
        for ticker, current_weight in positions.items()
    ]
    artifact = {
        "diagnostic_only": diagnostic_only,
        "validation_status": args.race_validation_status,
        "orders": orders,
    }
    (output_folder / "race_order_list.json").write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
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

