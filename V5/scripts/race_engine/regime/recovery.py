"""Strict recovery-entry exception for post-stress re-entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from race_engine.audit.events import AuditEvent


@dataclass(frozen=True)
class RecoveryConditions:
    r1_price_recovery: bool
    r2_breadth_recovery: bool
    r3_volatility_easing: bool
    r4_credit_recovery: bool
    r5_momentum_confirmation: bool

    def all_true(self) -> bool:
        return all(
            (
                self.r1_price_recovery,
                self.r2_breadth_recovery,
                self.r3_volatility_easing,
                self.r4_credit_recovery,
                self.r5_momentum_confirmation,
            )
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "r1_price_recovery": self.r1_price_recovery,
            "r2_breadth_recovery": self.r2_breadth_recovery,
            "r3_volatility_easing": self.r3_volatility_easing,
            "r4_credit_recovery": self.r4_credit_recovery,
            "r5_momentum_confirmation": self.r5_momentum_confirmation,
        }


@dataclass(frozen=True)
class RecoveryState:
    cooldown_weeks_remaining: int = 0
    used_for_current_stress: bool = False


@dataclass(frozen=True)
class RecoveryDecision:
    triggered: bool
    blend_fraction_toward_risk_on: float
    next_confirmation_weeks: int
    state: RecoveryState
    event: AuditEvent | None


def evaluate_recovery_entry(
    confirmed_regime: str,
    conditions: RecoveryConditions,
    evaluation_date: date,
    state: RecoveryState | None = None,
) -> RecoveryDecision:
    current_state = state or RecoveryState()
    eligible_regime = confirmed_regime in {"risk_off", "cash_defensive"}
    can_fire = (
        eligible_regime
        and conditions.all_true()
        and current_state.cooldown_weeks_remaining == 0
        and not current_state.used_for_current_stress
    )
    if not can_fire:
        next_cooldown = max(0, current_state.cooldown_weeks_remaining - 1)
        return RecoveryDecision(
            triggered=False,
            blend_fraction_toward_risk_on=0.0,
            next_confirmation_weeks=3,
            state=RecoveryState(next_cooldown, current_state.used_for_current_stress),
            event=None,
        )

    next_state = RecoveryState(cooldown_weeks_remaining=12, used_for_current_stress=True)
    event = AuditEvent(
        event_type="RECOVERY_ENTRY",
        severity="INFO",
        series_name=confirmed_regime,
        last_valid_date=evaluation_date,
        fallback_applied="50pct_risk_on_blend",
        details={
            "conditions": conditions.as_dict(),
            "cooldown_weeks_remaining": next_state.cooldown_weeks_remaining,
            "one_time_blend": True,
            "next_confirmation_weeks": 1,
        },
    )
    return RecoveryDecision(
        triggered=True,
        blend_fraction_toward_risk_on=0.50,
        next_confirmation_weeks=1,
        state=next_state,
        event=event,
    )

