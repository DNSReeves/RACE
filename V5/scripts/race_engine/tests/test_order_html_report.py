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
                "recommended_action": "STAGE_ENTRY",
                "trade_quality_status": "EXECUTE",
                "entry_quality_status": "STAGE_ENTRY",
                "entry_quality_reasons": ["rsi14_gt_72", "close_gt_20dma_plus_2std"],
            }
        ],
        "sleeve_leader_review": {
            "intl_equity": {
                "leader": "EEM",
                "leader_score": 0.82,
                "held_tickers": ["AVEM"],
                "comparisons": [
                    {
                        "held_ticker": "AVEM",
                        "held_score": 0.68,
                        "score_gap": 0.14,
                        "score_gap_tier": "MODERATE_ADVANTAGE",
                        "leader_entry_quality_status": "ENTRY_CAUTION",
                        "leader_persistence_status": "UNKNOWN",
                        "replacement_action": "STAGE_ENTRY",
                        "replacement_allowed": False,
                        "blockers": ["leader_persistence_unknown", "entry_quality_not_execute", "diagnostic_only_phase"],
                        "operator_note": "EEM currently leads AVEM tactically, but replacement is diagnostic-only.",
                    }
                ],
            }
        },
        "gate_failures": {"SPY": {"gate2": ["rsi14_gt_72"]}},
        "validation_messages": [],
    }

    html = render_order_html_report(artifact)

    assert "RACE Dry-Run Report" in html
    assert "Manual Review Ready" in html
    assert "Sleeve Targets" in html
    assert "Dry-Run Orders" in html
    assert "VTI" in html
    assert "Trade Quality" in html
    assert "Recommended Action" in html
    assert "STAGE ENTRY" in html
    assert "Entry Quality" in html
    assert html.index("Entry Quality") < html.index("Recommended Action") < html.index("Entry Notes")
    assert "STAGE_ENTRY" in html
    assert "rsi14_gt_72" in html
    assert "Sleeve Leader Review" in html
    assert "Diagnostic only. Does not authorize automatic sells or replacements." in html
    assert "AVEM" in html
    assert "Replacement Action" in html
    assert "class=\"pill action-stage-entry\"" in html
    assert "class=\"pill persistence-unknown\"" in html
    assert "class=\"blockers\"" in html
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
