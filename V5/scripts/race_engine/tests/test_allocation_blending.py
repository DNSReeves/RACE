import pytest

from race_engine.allocation.blending import (
    adjacent_regime_and_confidence,
    blend_targets,
    clamp_and_redistribute,
)
from race_engine.config.constants import DEFAULT_CONFIG


def test_neutral_minus_006_blends_40pct_neutral_60pct_risk_off() -> None:
    result = blend_targets("neutral", -0.06)

    assert result.adjacent_regime == "risk_off"
    assert result.confidence == pytest.approx(0.40)
    assert result.targets["us_equity_core"] == pytest.approx(21.0)
    assert result.targets["fixed_income"] == pytest.approx(22.2)
    assert sum(result.targets.values()) == pytest.approx(100.0)


def test_boundary_edge_cases() -> None:
    assert adjacent_regime_and_confidence("risk_off", -0.40) == ("cash_defensive", 0.0)
    assert adjacent_regime_and_confidence("neutral", -0.10) == ("risk_off", 0.0)
    assert adjacent_regime_and_confidence("risk_on", 0.30) == ("neutral", 0.0)


def test_cash_defensive_is_hard_floor_below_minus_040() -> None:
    result = blend_targets("cash_defensive", -0.50)

    assert result.adjacent_regime is None
    assert result.confidence == 1.0
    assert result.targets["cash"] == 35.0


def test_clamping_and_redistribution_preserves_total() -> None:
    confirmed = DEFAULT_CONFIG.allocations_by_regime()["risk_on"]
    targets = {
        "us_equity_core": 80.0,
        "us_equity_factor": 5.0,
        "intl_equity": 5.0,
        "fixed_income": 5.0,
        "real_assets": 3.0,
        "crisis_alpha": 1.0,
        "cash": 1.0,
    }

    result = clamp_and_redistribute(targets, confirmed)

    assert result["us_equity_core"] <= 50.0
    assert sum(result.values()) == pytest.approx(100.0)


def test_inflation_stress_blends_toward_base_regime() -> None:
    result = blend_targets(
        "inflation_stress",
        0.40,
        base_regime_without_override="risk_on",
        inflation_t10yie_excess=0.05,
        inflation_commodity_excess=0.05,
    )

    assert result.adjacent_regime == "risk_on"
    assert result.confidence == pytest.approx(0.50)
    assert sum(result.targets.values()) == pytest.approx(100.0)

