import pytest

from race_engine.construction.concentration import concentration_issues
from race_engine.construction.risk_contribution import sleeve_variance_contribution
from race_engine.construction.selector import RankedETF, select_top_ranked
from race_engine.construction.weights import construct_position_weights


def test_selects_top_ranked_with_configured_counts_and_weights_sum_to_100() -> None:
    candidates = (
        RankedETF("A", "fixed_income", 3.0),
        RankedETF("B", "fixed_income", 2.0),
        RankedETF("C", "fixed_income", 1.0),
        RankedETF("D", "fixed_income", 0.0),
        RankedETF("BIL", "cash", 1.0),
    )

    selected = select_top_ranked(candidates)
    weights = construct_position_weights({"fixed_income": 80.0, "cash": 20.0}, selected)

    assert tuple(etf.ticker for etf in selected["fixed_income"]) == ("A", "B", "C")
    assert weights["A"] == pytest.approx(40.0)
    assert weights["B"] == pytest.approx(24.0)
    assert weights["C"] == pytest.approx(16.0)
    assert sum(weights.values()) == pytest.approx(100.0)


def test_drop_positions_below_minimum_and_redistribute_inside_sleeve() -> None:
    selected = {"real_assets": (RankedETF("GLD", "real_assets", 2.0), RankedETF("DBC", "real_assets", 1.0))}

    weights = construct_position_weights({"real_assets": 0.6}, selected)

    assert weights == {"GLD": 100.0}


def test_concentration_detects_single_and_duplicate_risk() -> None:
    weights = {"SPY": 20.0, "IVV": 10.0, "BIL": 70.0}
    returns = {"SPY": (0.01, 0.02, 0.03), "IVV": (0.01, 0.02, 0.03), "BIL": (0.0, 0.0, 0.0)}

    issues = concentration_issues(weights, returns)

    assert {issue.issue_type for issue in issues} == {"MAX_SINGLE_POSITION", "DUPLICATE_CORRELATION"}


def test_sleeve_variance_contribution_sums_to_one() -> None:
    result = sleeve_variance_contribution(
        {"SPY": 50.0, "BIL": 50.0},
        {"SPY": "core", "BIL": "cash"},
        {"SPY": 0.04, "BIL": 0.01},
    )

    assert sum(result.values()) == pytest.approx(1.0)

