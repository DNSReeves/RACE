import pytest

from race_engine.regime.engine import (
    RegimeInputs,
    apply_inflation_override,
    composite_score,
    compute_regime_decision,
    map_base_regime,
)
from race_engine.regime.signals import (
    SignalResult,
    breadth_signal,
    hy_oas_signal,
    qqq_spy_relative_strength_signal,
    vix_level_signal,
)


def _series(start: float, step: float, count: int) -> tuple[float, ...]:
    return tuple(start + step * i for i in range(count))


def test_each_signal_returns_direction_and_raw_inputs() -> None:
    signals = (
        qqq_spy_relative_strength_signal(_series(100, 1, 64), _series(100, 0.1, 64)),
        breadth_signal(percent_above_50dma=0.70),
        vix_level_signal(14.0),
        hy_oas_signal(700.0),
    )

    assert [signal.value for signal in signals] == [1, 1, 1, -1]
    assert all(signal.raw_inputs for signal in signals)


def test_composite_weights_must_sum_to_one() -> None:
    signals = (SignalResult("a", 1), SignalResult("b", -1))
    assert composite_score(signals, {"a": 0.75, "b": 0.25}) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        composite_score(signals, {"a": 0.50, "b": 0.25})


def test_base_regime_mapping_and_inflation_override_boundary() -> None:
    assert map_base_regime(0.30) == "risk_on"
    assert map_base_regime(-0.10) == "neutral"
    assert map_base_regime(-0.40) == "risk_off"
    assert map_base_regime(-0.41) == "cash_defensive"
    assert apply_inflation_override("neutral", True, True) == "inflation_stress"
    assert apply_inflation_override("risk_off", True, True) == "risk_off"


def test_engine_computes_inflation_stress_only_from_risk_on_or_neutral() -> None:
    inputs = RegimeInputs(
        spy_closes=_series(100, 0.2, 220),
        qqq_closes=_series(100, 0.5, 220),
        vix_values=_series(18, -0.1, 30),
        hyg_closes=_series(80, 0.1, 30),
        lqd_closes=_series(100, 0.01, 30),
        dbc_closes=_series(20, 0.2, 80),
        t10yie_values=_series(2.0, 0.01, 30),
        hy_oas_bps=300.0,
        t10y2y_spread=0.60,
        percent_above_50dma=0.70,
    )

    decision = compute_regime_decision(inputs)

    assert decision.base_regime == "risk_on"
    assert decision.proposed_regime == "inflation_stress"
    assert decision.confirmed_regime == "neutral"

