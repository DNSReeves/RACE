"""Freshness checks for local RACE macro and VIX CSV inputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


REQUIRED_MACRO_SERIES = ("T10Y2Y", "T10YIE", "BAMLH0A0HYM2")


@dataclass(frozen=True)
class FreshnessResult:
    ok: bool
    messages: tuple[str, ...]
    latest_dates: dict[str, str]


def check_macro_vix_freshness(
    macro_csv: str | Path,
    vix_csv: str | Path,
    max_age_days: int = 7,
    as_of: date | None = None,
) -> FreshnessResult:
    today = as_of or date.today()
    messages: list[str] = []
    latest_dates: dict[str, str] = {}
    macro_path = Path(macro_csv)
    vix_path = Path(vix_csv)
    if not macro_path.exists():
        messages.append(f"FAIL: missing macro CSV: {macro_path}")
    if not vix_path.exists():
        messages.append(f"FAIL: missing VIX CSV: {vix_path}")
    if messages:
        return FreshnessResult(False, tuple(messages), latest_dates)

    macro_latest = _latest_macro_dates(macro_path)
    for series in REQUIRED_MACRO_SERIES:
        latest = macro_latest.get(series)
        if latest is None:
            messages.append(f"FAIL: macro CSV missing series {series}")
            continue
        latest_dates[series] = latest.isoformat()
        if latest < today - timedelta(days=max_age_days):
            messages.append(f"FAIL: macro series {series} stale: latest {latest.isoformat()}")

    vix_latest = _latest_vix_date(vix_path)
    if vix_latest is None:
        messages.append("FAIL: VIX CSV has no rows")
    else:
        latest_dates["VIX"] = vix_latest.isoformat()
        if vix_latest < today - timedelta(days=max_age_days):
            messages.append(f"FAIL: VIX CSV stale: latest {vix_latest.isoformat()}")

    if not messages:
        messages.append("PASS: cached macro/VIX CSV freshness accepted")
    return FreshnessResult(not any(message.startswith("FAIL:") for message in messages), tuple(messages), latest_dates)


def _latest_macro_dates(path: Path) -> dict[str, date]:
    latest: dict[str, date] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            series = row.get("series_name")
            if series not in REQUIRED_MACRO_SERIES:
                continue
            row_date = date.fromisoformat(row["date"])
            if series not in latest or row_date > latest[series]:
                latest[series] = row_date
    return latest


def _latest_vix_date(path: Path) -> date | None:
    latest: date | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_date = date.fromisoformat(row["date"])
            if latest is None or row_date > latest:
                latest = row_date
    return latest

