import csv
import json
import sqlite3
from datetime import date, timedelta

import pytest

from race_engine.data.cache_builder import build_race_market_cache, required_price_tickers
from race_engine.data.macro_cache_loader import prepare_race_macro_inputs


def test_prepare_race_macro_inputs_writes_fred_and_eodhd_csvs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EODHD_API_KEY", "local-eodhd-key")

    result = prepare_race_macro_inputs(
        output_dir=tmp_path,
        min_vix_rows=2,
        url_reader=_fake_reader,
    )

    assert result.macro_rows == 6
    assert result.vix_rows == 2
    assert result.vix_source == "EODHD"
    with result.macro_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["series_name"] for row in rows} == {"T10Y2Y", "T10YIE", "BAMLH0A0HYM2"}
    with result.vix_csv.open("r", encoding="utf-8") as handle:
        vix_rows = list(csv.DictReader(handle))
    assert vix_rows[0] == {"date": "2026-01-01", "value": "14.5"}


def test_prepare_race_macro_inputs_uses_fmp_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    monkeypatch.setenv("FMP_API_KEY", "local-fmp-key")

    result = prepare_race_macro_inputs(
        output_dir=tmp_path,
        min_vix_rows=2,
        url_reader=_fake_reader,
    )

    assert result.vix_source == "FMP"
    with result.vix_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[1] == {"date": "2026-01-02", "value": "15.0"}


def test_prepare_race_macro_inputs_requires_vix_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with pytest.raises(ValueError, match="VIX fetch requires"):
        prepare_race_macro_inputs(output_dir=tmp_path, min_vix_rows=2, url_reader=_fake_reader)


def test_generated_csvs_feed_cache_builder(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EODHD_API_KEY", "local-eodhd-key")
    source_db = tmp_path / "source.sqlite"
    output_db = tmp_path / "race_market_cache.sqlite"
    _create_source_without_macro_or_vix(source_db)
    result = prepare_race_macro_inputs(
        output_dir=tmp_path,
        min_vix_rows=2,
        url_reader=_fake_reader,
    )

    build = build_race_market_cache(
        source_db,
        output_db,
        macro_csv=result.macro_csv,
        vix_csv=result.vix_csv,
    )

    assert build.macro_rows == 6
    assert build.vix_rows == 2
    with sqlite3.connect(output_db) as connection:
        assert connection.execute("select count(*) from macro_observations").fetchone()[0] == 6
        assert connection.execute("select adjusted_close from prices where ticker = 'VIX' order by date limit 1").fetchone()[0] == 14.5


def _fake_reader(url: str) -> bytes:
    if "fred/series/observations" in url:
        return json.dumps(
            {
                "observations": [
                    {"date": "2026-01-01", "value": "1.0"},
                    {"date": "2026-01-02", "value": "1.1"},
                ]
            }
        ).encode("utf-8")
    if "fredgraph.csv" in url:
        if "T10Y2Y" in url:
            return b"observation_date,T10Y2Y\n2026-01-01,0.5\n2026-01-02,0.6\n"
        if "T10YIE" in url:
            return b"observation_date,T10YIE\n2026-01-01,2.1\n2026-01-02,2.2\n"
        return b"observation_date,BAMLH0A0HYM2\n2026-01-01,300\n2026-01-02,310\n"
    if "eodhd.com" in url:
        return json.dumps(
            [
                {"date": "2026-01-01", "adjusted_close": 14.5},
                {"date": "2026-01-02", "close": 15.0},
            ]
        ).encode("utf-8")
    if "financialmodelingprep.com" in url:
        return json.dumps(
            {
                "historical": [
                    {"date": "2026-01-01", "adjClose": 14.5},
                    {"date": "2026-01-02", "close": 15.0},
                ]
            }
        ).encode("utf-8")
    raise AssertionError(f"unexpected URL: {url}")


def _create_source_without_macro_or_vix(path):
    tickers = tuple(ticker for ticker in required_price_tickers() if ticker != "VIX")
    start = date(2026, 1, 1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
        )
        for ticker in tickers:
            for offset in range(3):
                value = 100 + offset
                connection.execute(
                    "insert into prices values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, (start + timedelta(days=offset)).isoformat(), value, value, value, value, value, 1000),
                )
            connection.execute(
                "insert into etf_metrics values (?, ?, ?, ?, ?)",
                (ticker, start.isoformat(), 100_000_000, 0.1, 0.01),
            )

