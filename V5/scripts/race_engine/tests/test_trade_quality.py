from dataclasses import asdict

from race_engine.execution.pipeline import _entry_quality_for_order
from race_engine.execution.order_list import proposed_order
from race_engine.execution.trade_quality import TradeQualityComponents, evaluate_trade_quality


def test_trade_quality_executes_deferred_and_abandons() -> None:
    good = evaluate_trade_quality("risk_on", TradeQualityComponents(1, 1, 1, 1, 1))
    deferred = evaluate_trade_quality("cash_defensive", TradeQualityComponents(0, 0, 0, 0, 0), prior_deferrals=0)
    abandoned = evaluate_trade_quality("cash_defensive", TradeQualityComponents(0, 0, 0, 0, 0), prior_deferrals=3)

    assert good.status == "EXECUTE"
    assert deferred.status == "DEFER"
    assert abandoned.status == "ABANDON"
    assert abandoned.deferral_count == 4


def test_trade_quality_component_breakdown_is_returned() -> None:
    decision = evaluate_trade_quality("neutral", TradeQualityComponents(0.5, 0.5, 0.5, 0.5, 0.5))

    assert set(decision.components) == {
        "score_gap",
        "execution_cost",
        "regime_alignment",
        "liquidity_quality",
        "timing",
    }
    assert decision.score == 0.5


def test_order_list_outputs_proposed_order_only() -> None:
    order = proposed_order("SPY", 10.0, 5.0, 100_000.0, 500.0, "P4", "SLEEVE_DRIFT", "EXECUTE")

    assert order.side == "BUY"
    assert order.dollar_change == 5000.0
    assert order.estimated_shares == 10
    assert order.trade_quality_status == "EXECUTE"
    assert order.entry_quality_status == "EXECUTE"
    assert order.entry_quality_reasons == ()


def test_buy_without_gate2_reasons_has_execute_entry_quality() -> None:
    status, reasons = _entry_quality_for_order(5.0, (), "EXECUTE")

    assert status == "EXECUTE"
    assert reasons == ()


def test_buy_with_one_gate2_reason_has_entry_caution() -> None:
    status, reasons = _entry_quality_for_order(5.0, ("rsi14_gt_72",), "EXECUTE")

    assert status == "ENTRY_CAUTION"
    assert reasons == ("rsi14_gt_72",)


def test_buy_with_two_gate2_reasons_has_stage_entry() -> None:
    gate2_reasons = ("rsi14_gt_72", "close_gt_20dma_plus_2std")

    status, reasons = _entry_quality_for_order(5.0, gate2_reasons, "EXECUTE")

    assert status == "STAGE_ENTRY"
    assert reasons == gate2_reasons


def test_buy_with_three_or_more_gate2_reasons_defers_overbought() -> None:
    gate2_reasons = ("rsi14_gt_72", "close_gt_20dma_plus_2std", "close_gt_50dma_1p12")

    status, reasons = _entry_quality_for_order(5.0, gate2_reasons, "EXECUTE")

    assert status == "DEFER_OVERBOUGHT"
    assert reasons == gate2_reasons


def test_sell_reduce_order_is_not_downgraded_by_gate2() -> None:
    status, reasons = _entry_quality_for_order(-5.0, ("rsi14_gt_72", "close_gt_20dma_plus_2std"), "EXECUTE")

    assert status == "EXECUTE"
    assert reasons == ()


def test_order_json_artifact_contains_entry_quality_fields() -> None:
    order = proposed_order(
        "SPY",
        10.0,
        5.0,
        100_000.0,
        500.0,
        "P4",
        "SLEEVE_DRIFT",
        "EXECUTE",
        entry_quality_status="ENTRY_CAUTION",
        entry_quality_reasons=("rsi14_gt_72",),
    )

    artifact_order = asdict(order)

    assert artifact_order["entry_quality_status"] == "ENTRY_CAUTION"
    assert artifact_order["entry_quality_reasons"] == ("rsi14_gt_72",)
