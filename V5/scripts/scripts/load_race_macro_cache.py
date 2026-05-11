"""Fetch local RACE macro and VIX CSV inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from race_engine.data.macro_cache_loader import prepare_race_macro_inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch local RACE macro and VIX CSV inputs")
    parser.add_argument("--output-dir", default="race_engine_out")
    parser.add_argument("--start-date", default="2005-01-01")
    parser.add_argument("--fred-api-key-file")
    parser.add_argument("--eodhd-api-key-file")
    parser.add_argument("--fmp-api-key-file")
    parser.add_argument("--min-vix-rows", type=int, default=800)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = prepare_race_macro_inputs(
        output_dir=args.output_dir,
        start_date=args.start_date,
        fred_api_key_file=args.fred_api_key_file,
        eodhd_api_key_file=args.eodhd_api_key_file,
        fmp_api_key_file=args.fmp_api_key_file,
        min_vix_rows=args.min_vix_rows,
    )
    print(f"macro_csv={result.macro_csv}")
    print(f"macro_rows={result.macro_rows}")
    print(f"vix_csv={result.vix_csv}")
    print(f"vix_rows={result.vix_rows}")
    print(f"vix_source={result.vix_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

