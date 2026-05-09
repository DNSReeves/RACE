from datetime import date

from race_engine.regime.recovery import (
    RecoveryConditions,
    RecoveryState,
    evaluate_recovery_entry,
)


ALL_TRUE = RecoveryConditions(True, True, True, True, True)


def test_recovery_entry_requires_all_five_conditions() -> None:
    conditions = RecoveryConditions(True, True, True, True, False)

    decision = evaluate_recovery_entry("risk_off", conditions, date(2026, 5, 9))

    assert decision.triggered is False
    assert decision.event is None


def test_recovery_entry_only_from_stress_regimes() -> None:
    decision = evaluate_recovery_entry("neutral", ALL_TRUE, date(2026, 5, 9))

    assert decision.triggered is False


def test_recovery_entry_emits_audit_event_and_cooldown() -> None:
    decision = evaluate_recovery_entry("cash_defensive", ALL_TRUE, date(2026, 5, 9))

    assert decision.triggered is True
    assert decision.blend_fraction_toward_risk_on == 0.50
    assert decision.next_confirmation_weeks == 1
    assert decision.state == RecoveryState(12, True)
    assert decision.event is not None
    assert decision.event.last_valid_date == date(2026, 5, 9)
    assert decision.event.details["conditions"]["r5_momentum_confirmation"] is True
    assert decision.event.details["one_time_blend"] is True


def test_recovery_entry_respects_cooldown() -> None:
    decision = evaluate_recovery_entry(
        "risk_off",
        ALL_TRUE,
        date(2026, 5, 9),
        RecoveryState(cooldown_weeks_remaining=2, used_for_current_stress=False),
    )

    assert decision.triggered is False
    assert decision.state.cooldown_weeks_remaining == 1

