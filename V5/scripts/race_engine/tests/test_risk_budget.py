import pytest

from race_engine.construction.risk_budget import apply_volatility_cap


def test_hard_cap_breach_scales_non_cash_and_increases_cash() -> None:
    weights = {"SPY": 80.0, "BIL": 20.0}
    returns = {
        "SPY": tuple(0.03 if i % 2 == 0 else -0.03 for i in range(63)),
        "BIL": tuple(0.0 for _ in range(63)),
    }

    result = apply_volatility_cap(weights, returns, "cash_defensive")

    assert result.event is not None
    assert result.weights["SPY"] < 80.0
    assert result.weights["BIL"] > 20.0
    assert sum(result.weights.values()) == pytest.approx(100.0)


def test_no_cap_event_when_volatility_under_cap() -> None:
    weights = {"SPY": 20.0, "BIL": 80.0}
    returns = {
        "SPY": tuple(0.001 if i % 2 == 0 else -0.001 for i in range(63)),
        "BIL": tuple(0.0 for _ in range(63)),
    }

    result = apply_volatility_cap(weights, returns, "risk_on")

    assert result.event is None
    assert result.weights == weights

