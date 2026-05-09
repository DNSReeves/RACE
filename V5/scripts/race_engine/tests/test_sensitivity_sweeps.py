import pytest

from race_engine.backtest.sensitivity import REQUIRED_SWEEPS, run_sensitivity_sweeps


def test_sensitivity_runner_produces_comparable_rows_for_all_required_parameters() -> None:
    values = {name: (0, 1) for name in REQUIRED_SWEEPS}

    rows = run_sensitivity_sweeps(values, lambda parameter, value: float(value))

    assert len(rows) == len(REQUIRED_SWEEPS) * 2
    assert {row.parameter for row in rows} == set(REQUIRED_SWEEPS)
    assert {row.metric_name for row in rows} == {"score"}


def test_sensitivity_runner_requires_all_parameters() -> None:
    with pytest.raises(ValueError):
        run_sensitivity_sweeps({}, lambda parameter, value: 0.0)

