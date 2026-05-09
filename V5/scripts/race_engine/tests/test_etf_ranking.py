import pytest

from race_engine.scoring.composite import ETFScoreInput, composite_scores
from race_engine.scoring.diversification import diversification_score
from race_engine.scoring.factors import max_drawdown, realized_volatility, weighted_total_return
from race_engine.scoring.sortino import sortino_trend_score, weighted_sortino_level
from race_engine.scoring.vehicle_quality import VehicleMetrics, vehicle_quality_score


def test_factor_calculations_are_deterministic() -> None:
    prices = tuple(float(100 + i) for i in range(252))
    returns = tuple(0.001 for _ in range(252))

    assert weighted_total_return(prices, prices[-126:], prices[-63:]) > 0
    assert max_drawdown((100.0, 110.0, 90.0, 120.0)) == pytest.approx(-0.18181818)
    assert realized_volatility(prices) >= 0
    assert weighted_sortino_level(returns, returns[-126:], returns[-63:]) == pytest.approx(10.0)


def test_small_sleeve_sortino_trend_falls_back_to_zero() -> None:
    assert sortino_trend_score((1.0,), 1.0, 1.0) == 0.0


def test_vehicle_quality_and_diversification_scores() -> None:
    quality = vehicle_quality_score(VehicleMetrics(50_000_000, 0.10, 0.8, 0.9))
    diversification = diversification_score((0.01, -0.01, 0.02), sleeve_peer_returns={"A": (0.01, -0.01, 0.02)})

    assert 0 <= quality <= 1
    assert diversification == pytest.approx(0.0)


def test_composite_scores_only_for_eligible_etfs() -> None:
    factors = {
        "sortino_level": 1.0,
        "sortino_trend": 0.5,
        "total_return": 0.1,
        "max_drawdown": -0.1,
        "realized_volatility": 0.2,
        "vehicle_quality": 0.8,
        "diversification": 0.1,
    }

    with pytest.raises(ValueError):
        composite_scores((ETFScoreInput("BAD", "cash", factors, eligible=False),))


def test_composite_scores_emit_audit_and_small_sleeve_flag() -> None:
    factors = {
        "sortino_level": 1.0,
        "sortino_trend": 0.5,
        "total_return": 0.1,
        "max_drawdown": -0.1,
        "realized_volatility": 0.2,
        "vehicle_quality": 0.8,
        "diversification": 0.1,
    }

    scores = composite_scores((ETFScoreInput("BIL", "cash", factors),))

    assert scores[0].score == 0.0
    assert scores[0].audit["flags"] == ("SMALL_SLEEVE",)
    assert scores[0].audit["final_composite_score"] == 0.0

