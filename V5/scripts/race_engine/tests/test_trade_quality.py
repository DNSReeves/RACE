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

