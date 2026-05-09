"""Run standalone RACE validation checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    commands = [
        [sys.executable, "-m", "pytest", "race_engine/tests", "-q", "-k", "not atsh_bridge"],
        [sys.executable, "-m", "py_compile", "race_engine/execution/cli.py"],
        [sys.executable, "-m", "py_compile", "race_engine/reporting/json_report.py"],
        [sys.executable, "-m", "py_compile", "race_engine/reporting/markdown_report.py"],
        [sys.executable, "-m", "py_compile", "race_engine/reporting/html_report.py"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
