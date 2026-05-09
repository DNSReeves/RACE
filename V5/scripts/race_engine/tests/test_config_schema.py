from dataclasses import FrozenInstanceError

import pytest

from race_engine.config.constants import DEFAULT_CONFIG, REGIMES, SLEEVES
from race_engine.config.load_config import load_config


def test_default_allocations_sum_to_100() -> None:
    expected = {
        "risk_on": (40.0, 20.0, 15.0, 10.0, 5.0, 5.0, 5.0),
        "neutral": (30.0, 15.0, 12.0, 18.0, 8.0, 10.0, 7.0),
        "risk_off": (15.0, 10.0, 10.0, 25.0, 10.0, 15.0, 15.0),
        "inflation_stress": (20.0, 12.0, 10.0, 10.0, 28.0, 12.0, 8.0),
        "cash_defensive": (5.0, 5.0, 5.0, 25.0, 5.0, 20.0, 35.0),
    }

    for allocation in DEFAULT_CONFIG.allocations:
        targets = tuple(item.target for item in allocation.sleeves)
        assert targets == expected[allocation.regime]
        assert sum(targets) == pytest.approx(100.0)


def test_every_regime_has_target_min_max_for_every_sleeve() -> None:
    assert set(DEFAULT_CONFIG.regimes) == set(REGIMES)
    assert set(DEFAULT_CONFIG.sleeves) == set(SLEEVES)

    for allocation in DEFAULT_CONFIG.allocations:
        by_sleeve = allocation.by_sleeve()
        assert set(by_sleeve) == set(SLEEVES)
        for sleeve in SLEEVES:
            item = by_sleeve[sleeve]
            assert item.min_weight <= item.target <= item.max_weight


def test_drift_bands_cover_all_sleeves() -> None:
    assert {item.sleeve for item in DEFAULT_CONFIG.drift_bands} == set(SLEEVES)
    assert all(item.band > 0 for item in DEFAULT_CONFIG.drift_bands)


def test_later_task_constants_are_encoded() -> None:
    assert DEFAULT_CONFIG.universe.counts_by_sleeve()["fixed_income"].max_count == 3
    assert DEFAULT_CONFIG.risk_budget.caps_by_regime()["cash_defensive"] == 10.0
    assert DEFAULT_CONFIG.rebalancing.margins_by_regime()["risk_off"] == 0.65
    assert DEFAULT_CONFIG.trade_quality.thresholds_by_regime()["inflation_stress"] == 0.50


def test_sensitivity_overrides_return_copy_without_mutating_default() -> None:
    cfg = load_config(
        {
            "risk_budget": {"hard_volatility_caps": (("risk_on", 15.0), ("neutral", 14.0), ("risk_off", 12.0), ("inflation_stress", 14.0), ("cash_defensive", 10.0))},
            "backtest": {"risk_free_rate": 0.04},
        }
    )

    assert cfg is not DEFAULT_CONFIG
    assert cfg.risk_budget.caps_by_regime()["risk_on"] == 15.0
    assert cfg.backtest.risk_free_rate == 0.04
    assert DEFAULT_CONFIG.risk_budget.caps_by_regime()["risk_on"] == 16.0
    assert DEFAULT_CONFIG.backtest.risk_free_rate == 0.03


def test_default_config_is_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        DEFAULT_CONFIG.regimes = ("risk_on",)

