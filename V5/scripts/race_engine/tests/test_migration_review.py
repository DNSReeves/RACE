from race_engine.execution.migration_review import MigrationReviewInputs, build_migration_review


def test_cash_and_money_market_are_used_first() -> None:
    review = build_migration_review(
        _inputs(current_positions={"CASH & CASH INVESTMENTS": 2.0, "SWVXX": 20.0})
    )

    actions = {row["current_ticker"]: row["migration_action"] for row in review["rows"]}
    assert actions["CASH & CASH INVESTMENTS"] == "USE_CASH_FIRST"
    assert actions["SWVXX"] == "USE_CASH_FIRST"


def test_current_target_holding_is_kept_race_aligned() -> None:
    review = build_migration_review(_inputs(current_positions={"IVV": 4.0}))

    row = review["rows"][0]
    assert row["classification"] == "us_equity_core"
    assert row["migration_action"] == "KEEP_RACE_ALIGNED"
    assert row["suggested_sell_percent"] == 0.0


def test_outside_race_position_gets_tranche_migration_diagnostic() -> None:
    review = build_migration_review(_inputs(current_positions={"CPSM": 4.0}))

    row = review["rows"][0]
    assert row["classification"] == "outside_race_universe"
    assert row["migration_action"] == "MIGRATE_IN_TRANCHES"
    assert row["suggested_sell_percent"] == 25.0
    assert row["suggested_sell_dollars"] == 1000.0
    assert row["race_destination_sleeve"] == "us_equity_core"


def test_cautious_destination_stages_migration() -> None:
    review = build_migration_review(
        _inputs(
            current_positions={"CPSM": 4.0},
            orders=[
                {"ticker": "MTUM", "side": "BUY", "uncapped_dollar_change": 9_000.0, "entry_quality_status": "ENTRY_CAUTION"},
            ],
            selected_etfs={"us_equity_factor": ["MTUM"]},
            target_positions={"MTUM": 9.0},
        )
    )

    row = review["rows"][0]
    assert row["migration_action"] == "STAGE_MIGRATION"
    assert row["entry_quality"] == "ENTRY_CAUTION"


def _inputs(
    current_positions: dict[str, float],
    orders: list[dict[str, object]] | None = None,
    selected_etfs: dict[str, list[str]] | None = None,
    target_positions: dict[str, float] | None = None,
) -> MigrationReviewInputs:
    return MigrationReviewInputs(
        current_positions=current_positions,
        target_positions=target_positions or {"IVV": 18.0, "SPY": 12.0},
        selected_etfs=selected_etfs or {"us_equity_core": ["IVV", "SPY"]},
        orders=orders
        or [
            {"ticker": "IVV", "side": "BUY", "uncapped_dollar_change": 13_000.0, "entry_quality_status": "EXECUTE"},
            {"ticker": "SPY", "side": "BUY", "uncapped_dollar_change": 12_000.0, "entry_quality_status": "EXECUTE"},
        ],
        portfolio_value=100_000.0,
    )
