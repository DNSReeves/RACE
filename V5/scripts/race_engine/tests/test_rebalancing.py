from datetime import date

from race_engine.execution.rebalance import (
    RebalanceTrigger,
    TriggerPriority,
    batch_triggers,
    quality_score_applies,
)
from race_engine.execution.replacement import replacement_decision
from race_engine.execution.turnover import trailing_one_way_turnover, turnover_margin_addon


def test_priority_rules_are_deterministic() -> None:
    triggers = (
        RebalanceTrigger("B", TriggerPriority.REPLACEMENT_THRESHOLD, "candidate"),
        RebalanceTrigger("A", TriggerPriority.HELD_FAILS_GATE1, "momentum"),
        RebalanceTrigger("C", TriggerPriority.CONFIRMED_REGIME_TRANSITION, "regime"),
    )

    ordered = batch_triggers(triggers)

    assert [item.priority for item in ordered] == [
        TriggerPriority.CONFIRMED_REGIME_TRANSITION,
        TriggerPriority.HELD_FAILS_GATE1,
        TriggerPriority.REPLACEMENT_THRESHOLD,
    ]


def test_p4_p5_quality_scored_but_p1_p2_p3_are_not() -> None:
    assert quality_score_applies(TriggerPriority.CONFIRMED_REGIME_TRANSITION) is False
    assert quality_score_applies(TriggerPriority.HELD_FAILS_GATE1) is False
    assert quality_score_applies(TriggerPriority.HELD_FAILS_GATE3) is False
    assert quality_score_applies(TriggerPriority.SLEEVE_DRIFT) is True
    assert quality_score_applies(TriggerPriority.REPLACEMENT_THRESHOLD) is True


def test_replacement_margins_vary_by_regime_and_turnover_adds_margin() -> None:
    assert replacement_decision(1.0, 1.5, "risk_on").replace is True
    assert replacement_decision(1.0, 1.5, "cash_defensive").replace is False
    assert replacement_decision(1.0, 1.7, "risk_off", 0.15).required_score == 1.80


def test_turnover_monitoring_adds_margin_above_threshold() -> None:
    turnover = trailing_one_way_turnover(((date(2026, 1, 1), 100.0), (date(2026, 5, 1), 60.0)), date(2026, 5, 9))

    assert turnover == 160.0
    assert turnover_margin_addon(turnover) == 0.15

