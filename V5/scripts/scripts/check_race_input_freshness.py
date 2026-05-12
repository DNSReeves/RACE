"""Check cached RACE macro and VIX CSV freshness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from race_engine.data.input_freshness import check_macro_vix_freshness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check RACE macro/VIX CSV freshness")
    parser.add_argument("--macro-csv", required=True)
    parser.add_argument("--vix-csv", required=True)
    parser.add_argument("--max-age-days", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check_macro_vix_freshness(args.macro_csv, args.vix_csv, args.max_age_days)
    for message in result.messages:
        print(message)
    for series, latest in sorted(result.latest_dates.items()):
        print(f"{series}_latest={latest}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

