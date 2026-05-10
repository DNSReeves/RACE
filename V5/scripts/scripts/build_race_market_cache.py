"""CLI wrapper for building the standalone RACE market data cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from race_engine.data.cache_builder import SourceMapping, build_race_market_cache


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build RACE-specific SQLite market cache")
    parser.add_argument("--source-db", required=True, help="Existing generic ETF SQLite database")
    parser.add_argument(
        "--output-db",
        default="race_engine_out/race_market_cache.sqlite",
        help="RACE cache output path",
    )
    parser.add_argument("--price-table", default="prices")
    parser.add_argument("--metrics-table", default="etf_metrics")
    parser.add_argument("--macro-table", default="macro_observations")
    parser.add_argument("--adjusted-close-column", default="adjusted_close")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_race_market_cache(
        args.source_db,
        args.output_db,
        SourceMapping(
            price_table=args.price_table,
            metrics_table=args.metrics_table,
            macro_table=args.macro_table,
            price_adjusted_close=args.adjusted_close_column,
        ),
    )
    print(f"output={result.output_path}")
    print(f"price_rows={result.price_rows}")
    print(f"metric_rows={result.metric_rows}")
    print(f"macro_rows={result.macro_rows}")
    for warning in result.warnings:
        print(f"WARN: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
