from race_engine.allocation.fallbacks import FallbackInput, apply_fallback


def test_no_fallback_when_minimum_holdings_available() -> None:
    result = apply_fallback(
        FallbackInput("cash", 7.0, ("BIL",), (), {}, "none")
    )

    assert result.level is None
    assert result.event is None


def test_partial_fallback_when_some_holdings_available() -> None:
    result = apply_fallback(
        FallbackInput("fixed_income", 18.0, ("IEF",), (), {}, "gate failures")
    )

    assert result.level == "PARTIAL"
    assert result.event is not None
    assert result.event.details["original_sleeve"] == "fixed_income"


def test_l1_relaxes_gate2_before_sister_or_cash() -> None:
    result = apply_fallback(
        FallbackInput("intl_equity", 12.0, (), ("EFA",), {"us_equity_core": ("SPY",)}, "overbought")
    )

    assert result.level == "L1_RELAX_GATE2"
    assert result.sleeve == "intl_equity"


def test_l2_sister_precedes_l3_cash() -> None:
    result = apply_fallback(
        FallbackInput("crisis_alpha", 10.0, (), (), {"fixed_income": ("IEF",)}, "gate failures")
    )

    assert result.level == "L2_SISTER_SLEEVE"
    assert result.sleeve == "fixed_income"


def test_l3_cash_redirection_logs_sleeve_loss() -> None:
    result = apply_fallback(
        FallbackInput("us_equity_core", 30.0, (), (), {}, "no eligible ETFs")
    )

    assert result.level == "L3_CASH_REDIRECTION"
    assert result.sleeve == "cash"
    assert result.event is not None
    assert result.event.event_type == "SLEEVE_LOSS"
    assert result.event.details["resulting_allocation"] == {"cash": ["BIL"]}

