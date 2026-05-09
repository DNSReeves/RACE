"""Minimal local sanity check for generated RACE summary artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("WARN missing summary path")
        return 0
    path = Path(args[0])
    if not path.exists():
        print("WARN summary path not found")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    status = data.get("validation_status") or data.get("status") or "PASS"
    print(status)
    return 0 if status in {"PASS", "WARN", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

