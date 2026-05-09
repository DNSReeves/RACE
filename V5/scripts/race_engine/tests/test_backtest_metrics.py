from datetime import date

import pytest

from race_engine.backtest.benchmarks import sixty_forty_benchmark, spy_benchmark
from race_engine.backtest.costs import one_way_transaction_cost
from race_engine.backtest.metrics import compute_metrics
from race_engine.backtest.walk_forward import quarterly_walk_forward_periods


def test_walk_forward_starts_oos_in_2010_and_flags_substitution_periods() -> None:
    periods = quarterly_walk_forward_periods(date(2005, 1, 1), date(2010, 7, 1), substitution_cutoff=date(2020, 5, 1))

    assert periods[0].oos_start == date(2010, 1, 1)
    assert periods[0].substitution_period is True
    assert periods[0].training_start == date(2005, 1, 1)


def test_transaction_costs_follow_aum_and_trade_size_rules() -> None:
    assert one_way_transaction_cost(100_000, 2_000_000_000) == pytest.approx(100.0)
    assert one_way_transaction_cost(600_000, 200_000_000) == pytest.approx(1500.0)


def test_metrics_compute_headline_oos_values() -> None:
    returns = (0.01, -0.02, 0.03, 0.01) * 13
    benchmark = (0.005, -0.01, 0.02, 0.0) * 13

    metrics = compute_metrics(returns, benchmark, turnover=25.0, regime_hits=(True, False, True))

    assert metrics.cagr > 0
    assert metrics.max_drawdown < 0
    assert metrics.turnover == 25.0
    assert metrics.regime_hit_rate == pytest.approx(2 / 3)


def test_benchmarks() -> None:
    assert spy_benchmark((0.01,)) == (0.01,)
    assert sixty_forty_benchmark((0.10,), (0.0,)) == (0.06,)
