"""Standalone RACE dry-run CLI."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from race_engine.execution.pipeline import run_standalone_pipeline
from race_engine.execution.sleeve_leader_review import sleeve_leaders_from_review

CASH_POSITION_LABELS = {"CASH", "CASH & CASH INVESTMENTS"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone RACE Engine dry-run")
    parser.add_argument("--race-engine-enable", action="store_true")
    parser.add_argument("--race-config")
    parser.add_argument("--race-market-data-cache")
    parser.add_argument("--race-current-positions-csv")
    parser.add_argument("--race-output-folder", default="race_engine_out")
    parser.add_argument("--race-validation-status", choices=("PASS", "WARN", "FAIL"), default="FAIL")
    parser.add_argument("--race-validation-message", action="append", default=[])
    parser.add_argument("--race-allow-warn-dry-run", action="store_true")
    parser.add_argument("--race-write-atsh-handoff", action="store_true")
    parser.add_argument("--race-sleeve-leader-state")
    parser.add_argument("--race-available-cash-dollars", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.race_engine_enable:
        return 0
    output_folder = Path(args.race_output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    leader_state_path = Path(args.race_sleeve_leader_state) if args.race_sleeve_leader_state else output_folder / "race_sleeve_leader_state.json"
    previous_sleeve_leaders = _read_sleeve_leader_state(leader_state_path)
    positions = _read_positions(Path(args.race_current_positions_csv)) if args.race_current_positions_csv else {}
    available_cash_weight = _available_cash_weight(positions)
    artifact = run_standalone_pipeline(
        config_path=args.race_config,
        market_data_cache=args.race_market_data_cache,
        current_positions=positions,
        validation_status=args.race_validation_status,
        allow_warn_dry_run=args.race_allow_warn_dry_run,
        previous_sleeve_leaders=previous_sleeve_leaders,
        available_cash_weight=available_cash_weight,
        available_cash_dollars=args.race_available_cash_dollars,
    )
    artifact.setdefault("validation_messages", []).extend(args.race_validation_message)
    (output_folder / "race_order_list.json").write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    _write_sleeve_leader_state(leader_state_path, artifact)
    if args.race_write_atsh_handoff:
        from race_engine.reporting.ats_handoff import race_dry_run_panel

        (output_folder / "race_ats_handoff.md").write_text(race_dry_run_panel(artifact), encoding="utf-8")
    return 0


def _read_sleeve_leader_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    leaders = payload.get("leaders", payload)
    if not isinstance(leaders, dict):
        return {}
    return {str(sleeve): str(leader) for sleeve, leader in leaders.items() if leader}


def _write_sleeve_leader_state(path: Path, artifact: dict[str, object]) -> None:
    review = artifact.get("sleeve_leader_review")
    if not isinstance(review, dict) or not review:
        return
    leaders = sleeve_leaders_from_review(review)
    if not leaders:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"leaders": leaders}, indent=2, sort_keys=True), encoding="utf-8")


def _read_positions(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header_index = _find_position_header(rows)
    if header_index is None:
        raise ValueError(f"could not find positions header in {path}")
    header = rows[header_index]
    positions: dict[str, float] = {}
    for values in rows[header_index + 1 :]:
        row = dict(zip(header, values))
        ticker = _first_present(row, ("ticker", "Ticker", "symbol", "Symbol"))
        weight = _first_present(
            row,
            (
                "current_weight",
                "Current Weight",
                "% of Acct (% of Account)",
                "% of Account",
                "Percent of Account",
            ),
        )
        if ticker and weight:
            parsed_weight = _parse_weight(weight)
            if parsed_weight is not None:
                positions[ticker.strip().upper()] = parsed_weight
    return positions


def _available_cash_weight(positions: dict[str, float]) -> float | None:
    cash_weight = sum(weight for ticker, weight in positions.items() if ticker in CASH_POSITION_LABELS)
    return cash_weight if cash_weight > 0 else None


def _find_position_header(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        normalized = {cell.strip().lower() for cell in row}
        if {"ticker", "current_weight"}.issubset(normalized):
            return index
        if "symbol" in normalized and any("% of acct" in cell.strip().lower() for cell in row):
            return index
    return None


def _first_present(row: dict[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _parse_weight(value: str) -> float | None:
    text = value.strip().replace("%", "").replace(",", "")
    if text in {"", "--", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
