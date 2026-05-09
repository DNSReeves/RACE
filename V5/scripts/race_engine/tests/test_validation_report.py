from race_engine.backtest.overfitting import parameter_count_status
from race_engine.backtest.validation_report import build_validation_report


def test_validation_report_labels_pass_warn_fail_and_keeps_bad_regimes() -> None:
    report = build_validation_report(
        race_metrics={"sharpe": 1.0, "max_drawdown": -0.20, "calmar": 0.8},
        spy_metrics={"sharpe": 0.9, "max_drawdown": -0.30, "calmar": 0.7},
        regime_segment_excess_returns={
            "risk_on": 0.1,
            "neutral": 0.1,
            "risk_off": 0.1,
            "inflation_stress": 0.1,
            "cash_defensive": -0.1,
        },
        engine_contribution_table={"risk_gates": 0.0, "risk_budget": 0.1},
        sensitivity_values=(0.90, 0.95, 1.0),
        period_returns=(0.1, 0.1, 0.1),
        regime_parameter_count=15,
    )

    assert report.overall_status == "PASS"
    assert "cash_defensive" in report.regime_segment_excess_returns
    assert report.criteria["four_of_five_regimes_positive"] == "PASS"


def test_validation_report_fails_on_negative_engine_contribution() -> None:
    report = build_validation_report(
        race_metrics={"sharpe": 0.8, "max_drawdown": -0.25, "calmar": 0.6},
        spy_metrics={"sharpe": 0.9, "max_drawdown": -0.30, "calmar": 0.7},
        regime_segment_excess_returns={"risk_on": 0.1},
        engine_contribution_table={"trade_quality": -0.1},
        sensitivity_values=(1.0, 1.5),
        period_returns=(1.0, 0.01, 0.01),
        regime_parameter_count=16,
    )

    assert report.overall_status == "FAIL"
    assert report.criteria["no_negative_engine_contribution"] == "FAIL"


def test_parameter_count_rule() -> None:
    assert parameter_count_status(15) == "PASS"
    assert parameter_count_status(16) == "FAIL"

