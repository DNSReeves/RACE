from race_engine.risk.gates import RiskGateInput, evaluate_risk_gates


def _prices_up(count: int) -> tuple[float, ...]:
    return tuple(100.0 + i * 0.05 for i in range(count))


def _returns(count: int) -> tuple[float, ...]:
    return tuple(-0.001 if i % 5 == 0 else 0.001 for i in range(count))


def test_gate_failures_trace_raw_values() -> None:
    report = evaluate_risk_gates(
        RiskGateInput(
            "BAD",
            tuple(200.0 - i * 0.1 for i in range(800)),
            _returns(252),
            adv_usd=10_000_000,
            aum_usd=50_000_000,
            bid_ask_spread_pct=0.30,
            price_history_days=100,
        )
    )

    assert report.eligible_for_new_purchase is False
    assert "gate1" in report.gate_failures
    assert "gate3" in report.gate_failures
    assert "ret_3m" in report.raw_values
    assert "adv_usd" in report.raw_values


def test_gate2_blocks_new_buys_but_not_held_sell() -> None:
    closes = tuple(float(100 + i * 0.01) for i in range(779)) + tuple(
        float(120 + i * 4) for i in range(21)
    )
    base = dict(
        ticker="HOT",
        adjusted_closes=closes,
        daily_returns=_returns(252),
        adv_usd=100_000_000,
        aum_usd=200_000_000,
        bid_ask_spread_pct=0.01,
        price_history_days=800,
    )

    new_report = evaluate_risk_gates(RiskGateInput(**base, held=False))
    held_report = evaluate_risk_gates(RiskGateInput(**base, held=True))

    assert new_report.gate_passes["gate2"] is False
    assert new_report.eligible_for_new_purchase is False
    assert held_report.eligible_for_new_purchase is True
    assert held_report.review_flags[0].flag_type == "HEIGHTENED_MONITORING_OVERBOUGHT"


def test_held_gate1_gate3_failures_generate_mandatory_review_flags() -> None:
    report = evaluate_risk_gates(
        RiskGateInput(
            "HELD",
            tuple(200.0 - i * 0.1 for i in range(800)),
            _returns(252),
            adv_usd=1_000_000,
            aum_usd=1_000_000,
            bid_ask_spread_pct=0.40,
            price_history_days=800,
            held=True,
        )
    )

    flags = {flag.flag_type: flag for flag in report.review_flags}
    assert flags["MANDATORY_REPLACEMENT_REVIEW_GATE1"].mandatory is True
    assert flags["MANDATORY_REPLACEMENT_REVIEW_GATE3"].mandatory is True
