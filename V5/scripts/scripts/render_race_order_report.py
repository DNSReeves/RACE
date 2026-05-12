"""Render a production-style RACE dry-run HTML report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from race_engine.reporting.order_html_report import write_order_html_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render RACE order-list JSON as HTML")
    parser.add_argument("--input-json", default="race_engine_out/race_order_list.json")
    parser.add_argument("--output-html", default="race_engine_out/race_order_report.html")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = write_order_html_report(args.input_json, args.output_html)
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

