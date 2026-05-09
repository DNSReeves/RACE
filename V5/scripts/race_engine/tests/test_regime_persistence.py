from race_engine.regime.state import RegimeState, update_regime_state


def test_regime_change_requires_three_consecutive_observations() -> None:
    state = RegimeState("neutral")

    state = update_regime_state(state, "risk_on", 0.40)
    assert state.confirmed_regime == "neutral"
    assert state.pending_regime == "risk_on"
    assert state.pending_count == 1

    state = update_regime_state(state, "risk_on", 0.45)
    assert state.confirmed_regime == "neutral"
    assert state.pending_count == 2

    state = update_regime_state(state, "risk_on", 0.50)
    assert state.confirmed_regime == "risk_on"
    assert state.pending_regime is None


def test_immediate_cash_defensive_exception() -> None:
    state = update_regime_state(RegimeState("risk_on"), "risk_off", -0.61)

    assert state.confirmed_regime == "cash_defensive"
    assert state.pending_regime is None
    assert state.pending_count == 0


def test_pending_state_resets_when_proposed_matches_confirmed() -> None:
    state = RegimeState("neutral", "risk_on", 2)
    state = update_regime_state(state, "neutral", 0.0)

    assert state == RegimeState("neutral")

