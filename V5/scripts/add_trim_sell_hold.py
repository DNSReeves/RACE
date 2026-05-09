"""Local ATSH entry point shim with optional RACE dry-run integration."""

from __future__ import annotations

import sys

from race_engine.execution.cli import main as race_cli_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--race-engine-enable" in args:
        return race_cli_main(args)
    print("ATSH behavior unchanged: RACE engine disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

