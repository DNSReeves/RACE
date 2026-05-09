from datetime import date

import pytest

from race_engine.backtest.paired_runs import static_adaptive_pair
from race_engine.regime.efficacy import adaptive_signal_weights, base_signal_weights, spearman_rank_correlation
from race_engine.regime.engine import SIGNAL_NAMES


def _history() -> dict[str, tuple[int, ...]]:
    return {
        name: tuple((-1, 0, 1)[(i + idx) % 3] for i in range(156))
        for idx, name in enumerate(SIGNAL_NAMES)
    }


def test_spearman_rank_correlation() -> None:
    assert spearman_rank_correlation((1, 2, 3), (10, 20, 30)) == pytest.approx(1.0)
    assert spearman_rank_correlation((1, 2, 3), (30, 20, 10)) == pytest.approx(-1.0)


def test_adaptive_weights_are_bounded_and_normalized() -> None:
    result = adaptive_signal_weights(
        _history(),
        tuple(float(i) for i in range(156)),
        date(2026, 4, 3),
    )

    base = base_signal_weights()
    assert result.updated is True
    assert sum(result.weights.values()) == pytest.approx(1.0)
    for name, weight in result.weights.items():
        assert weight > 0
        raw_modulator = result.events[[event.series_name for event in result.events].index(name)].details["modulator"]
        assert 0.5 <= raw_modulator <= 1.5
        assert result.events[0].details["base_weight"] == base[name]


def test_weights_update_quarterly_not_weekly() -> None:
    result = adaptive_signal_weights(
        _history(),
        tuple(float(i) for i in range(156)),
        date(2026, 4, 10),
        last_update_date=date(2026, 4, 3),
    )

    assert result.updated is False


def test_disabled_when_insufficient_or_manual_static() -> None:
    insufficient = adaptive_signal_weights(_history(), tuple(float(i) for i in range(100)), date(2026, 4, 3))
    static = adaptive_signal_weights(_history(), tuple(float(i) for i in range(156)), date(2026, 4, 3), enabled=False)

    assert insufficient.enabled is False
    assert static.enabled is False
    assert static.weights == base_signal_weights()


def test_static_and_adaptive_configs_can_run_side_by_side() -> None:
    static, adaptive = static_adaptive_pair()

    assert static.regime_signal_efficacy_enabled is False
    assert adaptive.regime_signal_efficacy_enabled is True
    assert static.name != adaptive.name

