"""Local CSV preparation utilities for RACE macro and VIX inputs."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, quote
from urllib.request import urlopen
from urllib.error import HTTPError, URLError


FRED_SERIES: tuple[str, ...] = ("T10Y2Y", "T10YIE", "BAMLH0A0HYM2")


@dataclass(frozen=True)
class MacroFetchResult:
    macro_csv: Path
    vix_csv: Path
    macro_rows: int
    vix_rows: int
    vix_source: str


UrlReader = Callable[[str], bytes]


def prepare_race_macro_inputs(
    output_dir: str | Path = "race_engine_out",
    start_date: str = "2005-01-01",
    fred_api_key_file: str | Path | None = None,
    eodhd_api_key_file: str | Path | None = None,
    fmp_api_key_file: str | Path | None = None,
    min_vix_rows: int = 800,
    url_reader: UrlReader | None = None,
) -> MacroFetchResult:
    """Fetch local CSV inputs for the RACE cache builder.

    API keys are read only from environment variables or explicitly supplied
    local key files. This function does not import or call ``dbloader.py``.
    """

    reader = url_reader or _read_url
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    macro_csv = output_path / "race_macro.csv"
    vix_csv = output_path / "vix.csv"
    fred_key = _read_key("FRED_API_KEY", fred_api_key_file)
    macro_rows = write_fred_macro_csv(macro_csv, start_date, fred_key, reader)
    vix_rows, source = write_vix_csv(
        vix_csv,
        start_date,
        _read_key("EODHD_API_KEY", eodhd_api_key_file),
        _read_key("FMP_API_KEY", fmp_api_key_file),
        reader,
    )
    if vix_rows < min_vix_rows:
        raise ValueError(f"VIX history has {vix_rows} rows, below required minimum {min_vix_rows}")
    return MacroFetchResult(macro_csv, vix_csv, macro_rows, vix_rows, source)


def write_fred_macro_csv(
    output_csv: str | Path,
    start_date: str,
    fred_api_key: str | None = None,
    url_reader: UrlReader | None = None,
) -> int:
    reader = url_reader or _read_url
    rows: list[tuple[str, str, float]] = []
    for series_name in FRED_SERIES:
        rows.extend((series_name, date, value) for date, value in _fetch_fred_series(series_name, start_date, fred_api_key, reader))
    if {row[0] for row in rows} != set(FRED_SERIES):
        raise ValueError("FRED macro output is missing one or more required series")
    with Path(output_csv).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("series_name", "date", "value"))
        writer.writerows(rows)
    return len(rows)


def write_vix_csv(
    output_csv: str | Path,
    start_date: str,
    eodhd_api_key: str | None,
    fmp_api_key: str | None,
    url_reader: UrlReader | None = None,
) -> tuple[int, str]:
    reader = url_reader or _read_url
    if eodhd_api_key:
        try:
            rows = _fetch_vix_eodhd(start_date, eodhd_api_key, reader)
            source = "EODHD"
        except ValueError:
            if not fmp_api_key:
                raise
            rows = _fetch_vix_fmp(start_date, fmp_api_key, reader)
            source = "FMP"
    elif fmp_api_key:
        rows = _fetch_vix_fmp(start_date, fmp_api_key, reader)
        source = "FMP"
    else:
        raise ValueError("VIX fetch requires EODHD_API_KEY or FMP_API_KEY, or a supplied local key file")
    if not rows:
        raise ValueError(f"{source} returned no VIX rows")
    with Path(output_csv).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", "value"))
        writer.writerows(rows)
    return len(rows), source


def _fetch_fred_series(
    series_name: str,
    start_date: str,
    fred_api_key: str | None,
    reader: UrlReader,
) -> tuple[tuple[str, float], ...]:
    if fred_api_key:
        query = urlencode(
            {
                "series_id": series_name,
                "api_key": fred_api_key,
                "file_type": "json",
                "observation_start": start_date,
            }
        )
        payload = json.loads(reader(f"https://api.stlouisfed.org/fred/series/observations?{query}").decode("utf-8"))
        observations = payload.get("observations", [])
        rows = []
        for item in observations:
            value = _parse_fred_value(item.get("value"))
            if value is not None:
                rows.append((item["date"], value))
        return tuple(rows)
    csv_payload = reader(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?{urlencode({'id': series_name, 'observation_start': start_date})}"
    ).decode("utf-8")
    parsed = csv.DictReader(csv_payload.splitlines())
    rows = []
    for row in parsed:
        value = _parse_fred_value(row.get(series_name))
        if value is not None:
            rows.append((row["observation_date"], value))
    return tuple(rows)


def _parse_fred_value(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", ".", "NaN", "nan", "None"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _fetch_vix_eodhd(start_date: str, api_key: str, reader: UrlReader) -> tuple[tuple[str, float], ...]:
    query = urlencode({"api_token": api_key, "fmt": "json", "period": "d", "from": start_date})
    errors = []
    for symbol in ("VIX.INDX", "VIX.IND", "^VIX.IND"):
        try:
            payload = json.loads(reader(f"https://eodhd.com/api/eod/{quote(symbol, safe='')}?{query}").decode("utf-8"))
            rows = tuple(
                (item["date"], float(item.get("adjusted_close") or item.get("close")))
                for item in payload
                if item.get("date") and (item.get("adjusted_close") is not None or item.get("close") is not None)
            )
            if rows:
                return rows
            errors.append(f"{symbol}: no rows")
        except (HTTPError, URLError, json.JSONDecodeError, TypeError, ValueError) as exc:
            errors.append(f"{symbol}: {exc.__class__.__name__}")
    raise ValueError(f"EODHD returned no usable VIX rows ({'; '.join(errors)})")


def _fetch_vix_fmp(start_date: str, api_key: str, reader: UrlReader) -> tuple[tuple[str, float], ...]:
    query = urlencode({"from": start_date, "apikey": api_key})
    payload = json.loads(reader(f"https://financialmodelingprep.com/api/v3/historical-price-full/%5EVIX?{query}").decode("utf-8"))
    historical = payload.get("historical", [])
    return tuple(
        (item["date"], float(item.get("adjClose") or item.get("close")))
        for item in historical
        if item.get("date") and (item.get("adjClose") is not None or item.get("close") is not None)
    )


def _read_key(env_name: str, key_file: str | Path | None) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value.strip()
    if key_file:
        return Path(key_file).read_text(encoding="utf-8").strip()
    return None


def _read_url(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()
