import json
import sqlite3
from datetime import date, timedelta

from race_engine.execution.cli import main, _available_cash_weight, _read_positions
from race_engine.allocation.sleeves import BASELINE_UNIVERSE
from race_engine.data.macro_loader import REQUIRED_TIER1_SERIES


def test_cli_exits_safely_when_flag_omitted(tmp_path) -> None:
    assert main(["--race-output-folder", str(tmp_path)]) == 0
    assert not (tmp_path / "race_order_list.json").exists()


def test_read_positions_supports_brokerage_export_with_title_row(tmp_path) -> None:
    positions = tmp_path / "positions.csv"
    positions.write_text(
        '"Positions for account DNSR-IRA ...985 as of 05:27 PM ET, 2026/05/11"\n\n'
        '"Symbol","Description","Qty (Quantity)","% of Acct (% of Account)","Asset Type",\n'
        '"DBMF","Managed Futures","1,014","6.83%","ETFs & Closed End Funds",\n'
        '"CASH","Cash","--","--","Cash",\n'
        '"BND","Bond ETF","200","3.18%","ETFs & Closed End Funds",\n',
        encoding="utf-8",
    )

    parsed = _read_positions(positions)

    assert parsed == {"DBMF": 6.83, "BND": 3.18}


def test_available_cash_weight_includes_brokerage_cash_and_money_market_funds() -> None:
    positions = {"CASH & CASH INVESTMENTS": 3.78, "SWVXX": 20.08, "DBMF": 9.01}

    assert _available_cash_weight(positions) == 23.86


def test_missing_data_returns_diagnostic_only(tmp_path) -> None:
    main(["--race-engine-enable", "--race-output-folder", str(tmp_path), "--race-validation-status", "PASS"])

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert data["diagnostic_only"] is True
    assert data["validation_status"] == "FAIL"
    assert data["orders"] == []
    assert data["validation_messages"]


def test_dry_run_order_list_generated_but_not_transmitted(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    positions = tmp_path / "positions.csv"
    positions.write_text("ticker,current_weight\nSPY,10\n", encoding="utf-8")

    assert main([
        "--race-engine-enable",
        "--race-current-positions-csv",
        str(positions),
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
    ]) == 0

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert data["diagnostic_only"] is False
    assert data["orders"]
    assert all("recommended_action" in order for order in data["orders"])
    assert data["sleeve_leader_review"]
    assert data["migration_to_pure_race"]
    assert data["confirmed_regime"]
    assert data["sleeve_targets"]
    assert data["target_positions"]
    assert not (tmp_path / "race_ats_handoff.md").exists()


def test_buy_recommendations_are_limited_to_available_cash(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    positions = tmp_path / "positions.csv"
    positions.write_text("ticker,current_weight\nSPY,10\nCASH & CASH INVESTMENTS,2\nSWVXX,20\n", encoding="utf-8")

    assert main([
        "--race-engine-enable",
        "--race-current-positions-csv",
        str(positions),
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
    ]) == 0

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    buy_total = sum(order["dollar_change"] for order in data["orders"] if order["side"] == "BUY")

    assert data["cash_available_for_buys"]["available_cash_dollars"] == 22000.0
    assert data["cash_available_for_buys"]["cash_limited"] is True
    assert buy_total <= 22000.01
    assert all(order["cash_adjustment_status"] == "CASH_LIMITED" for order in data["orders"] if order["side"] == "BUY")
    assert any("uncapped_dollar_change" in order for order in data["orders"] if order["side"] == "BUY")


def test_cli_persists_sleeve_leader_state_for_future_diagnostics(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    state = tmp_path / "leader_state.json"

    args = [
        "--race-engine-enable",
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-sleeve-leader-state",
        str(state),
        "--race-validation-status",
        "PASS",
    ]
    assert main(args) == 0
    first = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert state.exists()
    assert any(
        comparison["leader_persistence_status"] == "UNKNOWN"
        for sleeve in first["sleeve_leader_review"].values()
        for comparison in sleeve["comparisons"]
    )

    assert main(args) == 0
    second = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert any(
        comparison["leader_persistence_status"] == "PERSISTENT"
        for sleeve in second["sleeve_leader_review"].values()
        for comparison in sleeve["comparisons"]
    )


def test_validation_fail_blocks_actionable_labeling(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    assert main([
        "--race-engine-enable",
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "FAIL",
    ]) == 0

    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert data["diagnostic_only"] is True
    assert data["orders"] == []


def test_warn_requires_explicit_allow_flag(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    main([
        "--race-engine-enable",
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "WARN",
    ])
    blocked = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert blocked["diagnostic_only"] is True
    assert blocked["orders"] == []

    main([
        "--race-engine-enable",
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "WARN",
        "--race-allow-warn-dry-run",
    ])
    allowed = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))
    assert allowed["diagnostic_only"] is False
    assert allowed["orders"]


def test_cli_uses_config_and_market_data_cache(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    config = tmp_path / "race_config.json"
    config.write_text('{"backtest": {"risk_free_rate": 0.04}}', encoding="utf-8")

    main([
        "--race-engine-enable",
        "--race-config",
        str(config),
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
    ])
    data = json.loads((tmp_path / "race_order_list.json").read_text(encoding="utf-8"))

    assert data["config_path"] == str(config)
    assert data["market_data_source"] == str(cache)
    assert any("loaded config overrides" in message for message in data["validation_messages"])


def test_atsh_handoff_is_optional_downstream_output(tmp_path) -> None:
    cache = _market_cache(tmp_path)
    main([
        "--race-engine-enable",
        "--race-market-data-cache",
        str(cache),
        "--race-output-folder",
        str(tmp_path),
        "--race-validation-status",
        "PASS",
        "--race-write-atsh-handoff",
    ])

    assert (tmp_path / "race_ats_handoff.md").exists()


def test_no_core_module_imports_atsh_or_dbloader() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "add_trim_sell_hold" in text or "import dbloader" in text or "from dbloader" in text:
            offenders.append(str(path))
    assert offenders == []


def _market_cache(tmp_path):
    path = tmp_path / "market.sqlite"
    tickers = sorted({entry.ticker for entry in BASELINE_UNIVERSE} | {ticker for ticker in REQUIRED_TIER1_SERIES if ticker not in {"T10Y2Y", "T10YIE", "BAMLH0A0HYM2"}})
    start = date(2023, 1, 1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table prices (ticker text, date text, open real, high real, low real, close real, adjusted_close real, volume real)"
        )
        connection.execute(
            "create table etf_metrics (ticker text, as_of text, aum real, expense_ratio real, bid_ask_spread real)"
        )
        connection.execute(
            "create table macro_observations (series_name text, date text, value real)"
        )
        for t_index, ticker in enumerate(tickers):
            for day in range(820):
                value = 100.0 + day * (0.05 + t_index * 0.0001) + (0.5 if day % 5 else -0.5)
                connection.execute(
                    "insert into prices values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, (start + timedelta(days=day)).isoformat(), value, value + 1, value - 1, value, value, 1_000_000),
                )
            connection.execute(
                "insert into etf_metrics values (?, ?, ?, ?, ?)",
                (ticker, (start + timedelta(days=819)).isoformat(), 200_000_000.0, 0.10, 0.01),
            )
        for day in range(30):
            current = start + timedelta(days=790 + day)
            connection.execute("insert into macro_observations values ('T10YIE', ?, ?)", (current.isoformat(), 2.0 + day * 0.001))
            connection.execute("insert into macro_observations values ('T10Y2Y', ?, ?)", (current.isoformat(), 0.6))
            connection.execute("insert into macro_observations values ('BAMLH0A0HYM2', ?, ?)", (current.isoformat(), 300.0))
    return path
