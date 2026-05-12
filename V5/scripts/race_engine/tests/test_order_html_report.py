from race_engine.reporting.order_html_report import render_order_html_report, write_order_html_report


def test_order_html_report_contains_production_sections(tmp_path) -> None:
    artifact = {
        "validation_status": "PASS",
        "diagnostic_only": False,
        "timestamp": "2026-05-11T21:11:12+00:00",
        "market_data_source": "race_engine_out\\race_market_cache.sqlite",
        "confirmed_regime": "neutral",
        "composite_regime_score": 0.6,
        "regime_confidence": 1.0,
        "sleeve_targets": {"cash": 7.0, "us_equity_core": 30.0},
        "target_positions": {"SGOV": 7.0, "VTI": 30.0},
        "selected_etfs": {"cash": ["SGOV"]},
        "orders": [
            {
                "ticker": "VTI",
                "side": "BUY",
                "target_weight": 30.0,
                "current_weight": 0.0,
                "dollar_change": 30000,
                "estimated_shares": 82,
                "priority": "SLEEVE_DRIFT",
                "trade_quality_status": "EXECUTE",
            }
        ],
        "gate_failures": {"SPY": {"gate2": ["rsi14_gt_72"]}},
        "validation_messages": [],
    }

    html = render_order_html_report(artifact)

    assert "RACE Dry-Run Report" in html
    assert "Manual Review Ready" in html
    assert "Sleeve Targets" in html
    assert "Dry-Run Orders" in html
    assert "VTI" in html
    assert "broker" in html


def test_write_order_html_report(tmp_path) -> None:
    input_json = tmp_path / "race_order_list.json"
    output_html = tmp_path / "race_order_report.html"
    input_json.write_text(
        '{"validation_status":"FAIL","diagnostic_only":true,"orders":[],"sleeve_targets":{},"target_positions":{}}',
        encoding="utf-8",
    )

    result = write_order_html_report(input_json, output_html)

    assert result == output_html
    assert "Diagnostic Only" in output_html.read_text(encoding="utf-8")

