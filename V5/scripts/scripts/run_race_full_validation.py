"""Run a lightweight local RACE validation sequence."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    commands = [
        [sys.executable, "-m", "pytest", "race_engine/tests", "-q"],
        [sys.executable, "-m", "py_compile", "add_trim_sell_hold.py"],
        [sys.executable, "harness/sanity_check.py", "summary_dict_debug.json"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

