"""Standalone RACE strategy pipeline used by the dry-run CLI."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from race_engine.allocation.blending import blend_targets
from race_engine.allocation.sleeves import BASELINE_UNIVERSE
from race_engine.config.load_config import load_config
from race_engine.config.schema import RaceConfig
from race_engine.construction.risk_budget import apply_volatility_cap
from race_engine.construction.selector import RankedETF, select_top_ranked
from race_engine.construction.weights import construct_position_weights
from race_engine.data.adapter import RaceMarketDataAdapter
from race_engine.data.macro_loader import REQUIRED_TIER1_SERIES
from race_engine.execution.order_list import proposed_order
from race_engine.execution.rebalance import RebalanceTrigger, TriggerPriority, batch_triggers
from race_engine.execution.replacement import replacement_decision
from race_engine.execution.sleeve_leader_review import (
    SleeveLeaderReviewInputs,
    build_sleeve_leader_review,
    leader_persistence_status_by_sleeve,
)
from race_engine.execution.trade_quality import TradeQualityComponents, evaluate_trade_quality
from race_engine.risk.gates import RiskGateInput, evaluate_risk_gates
from race_engine.scoring.composite import ETFScoreInput, composite_scores
from race_engine.scoring.factors import max_drawdown, realized_volatility, weighted_total_return
from race_engine.scoring.sortino import sortino_trend_score, weighted_sortino_level
from race_engine.regime.engine import RegimeInputs, compute_regime_decision


STATUS_ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2}


def run_standalone_pipeline(
    config_path: str | None,
    market_data_cache: str | None,
    current_positions: dict[str, float],
    validation_status: str,
    allow_warn_dry_run: bool,
    portfolio_value: float = 100_000.0,
    previous_sleeve_leaders: dict[str, str] | None = None,
    available_cash_weight: float | None = None,
    available_cash_dollars: float | None = None,
) -> dict[str, Any]:
    messages: list[str] = []
    try:
        config = _load_config_path(config_path)
    except Exception as exc:
        return _base_artifact(
            diagnostic_only=True,
            validation_status="FAIL",
            validation_messages=[f"FAIL: config could not be loaded: {exc}"],
            config_path=config_path,
            market_data_source=market_data_cache,
            current_positions=current_positions,
        )
    if config_path:
        messages.append(f"PASS: loaded config overrides from {config_path}")
    readiness_status = _readiness_status(market_data_cache, messages)
    effective_status = _worst_status(readiness_status, validation_status)
    diagnostic_only = effective_status == "FAIL" or (
        effective_status == "WARN" and not allow_warn_dry_run
    )
    artifact = _base_artifact(
        diagnostic_only=diagnostic_only,
        validation_status=effective_status,
        validation_messages=messages,
        config_path=config_path,
        market_data_source=market_data_cache,
        current_positions=current_positions,
    )
    if readiness_status == "FAIL":
        return artifact

    try:
        pipeline = _compute_pipeline(
            config,
            Path(market_data_cache or ""),
            current_positions,
            portfolio_value,
            diagnostic_only,
            previous_sleeve_leaders or {},
            available_cash_weight,
            available_cash_dollars,
        )
    except Exception as exc:
        artifact["diagnostic_only"] = True
        artifact["validation_status"] = "FAIL"
        artifact["validation_messages"].append(f"PIPELINE_FAIL: {exc}")
        return artifact

    artifact.update(pipeline)
    if diagnostic_only:
        artifact["orders"] = []
    return artifact


def _compute_pipeline(
    config: RaceConfig,
    market_data_cache: Path,
    current_positions: dict[str, float],
    portfolio_value: float,
    diagnostic_only: bool,
    previous_sleeve_leaders: dict[str, str],
    available_cash_weight: float | None,
    available_cash_dollars: float | None,
) -> dict[str, Any]:
    adapter = RaceMarketDataAdapter(market_data_cache)
    price_bars = {ticker: adapter.get_ohlcv(ticker) for ticker in _required_price_tickers()}
    closes = {
        ticker: tuple(bar.adjusted_close for bar in bars)
        for ticker, bars in price_bars.items()
    }
    macro = _read_macro_history(market_data_cache)
    regime_inputs = RegimeInputs(
        spy_closes=closes["SPY"],
        qqq_closes=closes["QQQ"],
        vix_values=closes["VIX"],
        hyg_closes=closes["HYG"],
        lqd_closes=closes["LQD"],
        dbc_closes=closes["DBC"],
        t10yie_values=macro["T10YIE"],
        hy_oas_bps=macro["BAMLH0A0HYM2"][-1],
        t10y2y_spread=macro["T10Y2Y"][-1],
        percent_above_50dma=0.70 if closes["SPY"][-1] > sum(closes["SPY"][-50:]) / 50 else 0.30,
    )
    regime = compute_regime_decision(regime_inputs)
    blended = blend_targets(
        regime.confirmed_regime,
        regime.composite_score,
        config=config,
        base_regime_without_override=regime.base_regime,
        inflation_t10yie_excess=max(0.0, regime.raw_inputs.get("t10yie_4w_change", 0.0)),
        inflation_commodity_excess=max(0.0, regime.raw_inputs.get("dbc_spy_63d_relative_strength", 0.0)),
    )

    gate_reports = []
    score_inputs = []
    for entry in BASELINE_UNIVERSE:
        bars = adapter.get_ohlcv(entry.ticker)
        if len(bars) < 800:
            continue
        ticker_closes = tuple(bar.adjusted_close for bar in bars)
        returns = _returns(ticker_closes)
        metrics = adapter.get_metrics(entry.ticker)
        report = evaluate_risk_gates(
            RiskGateInput(
                ticker=entry.ticker,
                adjusted_closes=ticker_closes,
                daily_returns=returns,
                adv_usd=_adv_usd(bars),
                aum_usd=0.0 if metrics is None or metrics.aum is None else metrics.aum,
                bid_ask_spread_pct=0.0 if metrics is None or metrics.bid_ask_spread is None else metrics.bid_ask_spread,
                price_history_days=len(bars),
                held=entry.ticker in current_positions,
            )
        )
        gate_reports.append(report)
        if report.eligible_for_new_purchase:
            score_inputs.append(ETFScoreInput(entry.ticker, entry.sleeve, _factor_payload(ticker_closes, returns)))

    scores = composite_scores(tuple(score_inputs)) if score_inputs else ()
    ranked = tuple(RankedETF(score.ticker, score.sleeve, score.score) for score in scores)
    selected = select_top_ranked(ranked)
    selected_etfs = {sleeve: [item.ticker for item in items] for sleeve, items in selected.items()}
    gate_report_by_ticker = {report.ticker: report for report in gate_reports}
    target_positions = construct_position_weights(blended.targets, selected) if selected else {}
    returns_by_ticker = {
        ticker: _returns(tuple(bar.adjusted_close for bar in adapter.get_ohlcv(ticker)))[-63:]
        for ticker in target_positions
    }
    risk_budget = apply_volatility_cap(target_positions, returns_by_ticker, regime.confirmed_regime)
    target_positions = risk_budget.weights
    triggers = batch_triggers(
        tuple(
            RebalanceTrigger(ticker, TriggerPriority.SLEEVE_DRIFT, "target_weight_change")
            for ticker, target in target_positions.items()
            if abs(target - current_positions.get(ticker, 0.0)) >= config.rebalancing.minimum_trade_weight
        )
    )
    orders = []
    latest_price = {}
    if not diagnostic_only:
        score_by_ticker = {score.ticker: score.score for score in scores}
        latest_price = {ticker: adapter.get_ohlcv(ticker)[-1].adjusted_close for ticker in target_positions}
        for trigger in triggers:
            ticker = trigger.ticker
            target = target_positions[ticker]
            current = current_positions.get(ticker, 0.0)
            replacement = replacement_decision(0.0, score_by_ticker.get(ticker, 0.0), regime.confirmed_regime)
            quality = evaluate_trade_quality(
                regime.confirmed_regime,
                TradeQualityComponents(
                    score_gap=max(0.0, min(1.0, replacement.margin)),
                    execution_cost=1.0,
                    regime_alignment=1.0,
                    liquidity_quality=1.0,
                    timing=1.0,
                ),
            )
            if quality.status == "EXECUTE":
                entry_quality_status, entry_quality_reasons = _entry_quality_for_order(
                    target - current,
                    gate_report_by_ticker.get(ticker).gate2_reasons if ticker in gate_report_by_ticker else (),
                    quality.status,
                )
                orders.append(
                    asdict(
                        proposed_order(
                            ticker=ticker,
                            target_weight=target,
                            current_weight=current,
                            portfolio_value=portfolio_value,
                            price=latest_price[ticker],
                            reason_code=trigger.reason,
                            priority=trigger.priority.name,
                            trade_quality_status=quality.status,
                            entry_quality_status=entry_quality_status,
                            entry_quality_reasons=entry_quality_reasons,
                        )
                    )
                )
    cash_summary = _apply_available_cash_limit(
        orders,
        portfolio_value=portfolio_value,
        available_cash_weight=available_cash_weight,
        available_cash_dollars=available_cash_dollars,
        latest_price=latest_price,
    )
    sleeve_leader_review = build_sleeve_leader_review(
        SleeveLeaderReviewInputs(
            ranked=ranked,
            current_positions=current_positions,
            target_positions=target_positions,
            sleeve_targets=blended.targets,
            leader_gate2_reasons={
                report.ticker: report.gate2_reasons
                for report in gate_reports
                if report.ticker in {item.ticker for item in ranked}
            },
            gate_failures={report.ticker: report.gate_failures for report in gate_reports if report.gate_failures},
            minimum_trade_weight=config.rebalancing.minimum_trade_weight,
            leader_persistence_by_sleeve=leader_persistence_status_by_sleeve(ranked, previous_sleeve_leaders),
        )
    )

    return {
        "confirmed_regime": regime.confirmed_regime,
        "composite_regime_score": regime.composite_score,
        "regime_confidence": blended.confidence,
        "sleeve_targets": blended.targets,
        "selected_etfs": selected_etfs,
        "target_positions": target_positions,
        "orders": orders,
        "cash_available_for_buys": cash_summary,
        "sleeve_leader_review": sleeve_leader_review,
        "gate_failures": {report.ticker: report.gate_failures for report in gate_reports if report.gate_failures},
    }


def _load_config_path(config_path: str | None) -> RaceConfig:
    if not config_path:
        return load_config()
    with Path(config_path).open("r", encoding="utf-8") as handle:
        overrides = json.load(handle)
    return load_config(overrides)


def _entry_quality_for_order(
    weight_delta: float,
    gate2_reasons: tuple[str, ...],
    trade_quality_status: str,
) -> tuple[str, tuple[str, ...]]:
    if trade_quality_status != "EXECUTE" or weight_delta <= 0:
        return trade_quality_status, ()
    reason_count = len(gate2_reasons)
    if reason_count == 0:
        return "EXECUTE", ()
    if reason_count == 1:
        return "ENTRY_CAUTION", gate2_reasons
    if reason_count == 2:
        return "STAGE_ENTRY", gate2_reasons
    return "DEFER_OVERBOUGHT", gate2_reasons


def _readiness_status(market_data_cache: str | None, messages: list[str]) -> str:
    if not market_data_cache:
        messages.append("FAIL: --race-market-data-cache is required for standalone pipeline execution")
        return "FAIL"
    path = Path(market_data_cache)
    if not path.exists():
        messages.append(f"FAIL: market data cache not found: {path}")
        return "FAIL"
    try:
        missing_prices = _missing_price_tickers(path)
        missing_macro = _missing_macro_series(path)
    except sqlite3.Error as exc:
        messages.append(f"FAIL: market data cache cannot be read: {exc}")
        return "FAIL"
    if missing_prices or missing_macro:
        if missing_prices:
            messages.append(f"FAIL: missing required price series: {', '.join(missing_prices)}")
        if missing_macro:
            messages.append(f"FAIL: missing required macro series: {', '.join(missing_macro)}")
        return "FAIL"
    return "PASS"


def _missing_price_tickers(path: Path) -> tuple[str, ...]:
    with _connect_ro(path) as connection:
        existing = {
            row[0]
            for row in connection.execute(
                "select ticker from prices group by ticker having count(*) >= 800"
            )
        }
    return tuple(ticker for ticker in _required_price_tickers() if ticker not in existing)


def _missing_macro_series(path: Path) -> tuple[str, ...]:
    with _connect_ro(path) as connection:
        existing = {
            row[0]: row[1]
            for row in connection.execute(
                "select series_name, count(*) from macro_observations group by series_name"
            )
        }
    required = {"T10Y2Y": 1, "BAMLH0A0HYM2": 1, "T10YIE": 21}
    return tuple(name for name, minimum in required.items() if existing.get(name, 0) < minimum)


def _read_macro_history(path: Path) -> dict[str, tuple[float, ...]]:
    with _connect_ro(path) as connection:
        rows = connection.execute(
            "select series_name, value from macro_observations order by date"
        ).fetchall()
    output: dict[str, list[float]] = {}
    for series, value in rows:
        output.setdefault(series, []).append(float(value))
    return {series: tuple(values) for series, values in output.items()}


def _connect_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _required_price_tickers() -> tuple[str, ...]:
    universe_tickers = tuple(entry.ticker for entry in BASELINE_UNIVERSE)
    tier1_price_tickers = tuple(ticker for ticker in REQUIRED_TIER1_SERIES if ticker not in {"T10Y2Y", "T10YIE", "BAMLH0A0HYM2"})
    return tuple(dict.fromkeys((*tier1_price_tickers, *universe_tickers)))


def _factor_payload(closes: tuple[float, ...], returns: tuple[float, ...]) -> dict[str, float]:
    return {
        "sortino_level": weighted_sortino_level(returns[-252:], returns[-126:], returns[-63:]),
        "sortino_trend": sortino_trend_score((0.0,) * 52, 0.0, 0.0),
        "total_return": weighted_total_return(closes[-252:], closes[-126:], closes[-63:]),
        "max_drawdown": max_drawdown(closes[-252:]),
        "realized_volatility": realized_volatility(closes[-63:]),
        "vehicle_quality": 0.75,
        "diversification": 0.0,
    }


def _returns(closes: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes)))


def _adv_usd(bars: tuple[Any, ...]) -> float:
    sample = bars[-21:]
    return sum(bar.adjusted_close * bar.volume for bar in sample) / len(sample)


def _base_artifact(
    diagnostic_only: bool,
    validation_status: str,
    validation_messages: list[str],
    config_path: str | None,
    market_data_source: str | None,
    current_positions: dict[str, float],
) -> dict[str, Any]:
    return {
        "diagnostic_only": diagnostic_only,
        "validation_status": validation_status,
        "validation_messages": validation_messages,
        "confirmed_regime": None,
        "composite_regime_score": None,
        "regime_confidence": None,
        "sleeve_targets": {},
        "selected_etfs": {},
        "current_positions": current_positions,
        "target_positions": {},
        "orders": [],
        "cash_available_for_buys": {
            "available_cash_dollars": None,
            "available_cash_weight": None,
            "buy_demand_dollars": 0.0,
            "cash_limited": False,
            "scale_factor": 1.0,
        },
        "sleeve_leader_review": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path,
        "market_data_source": market_data_source,
    }


def _worst_status(left: str, right: str) -> str:
    return left if STATUS_ORDER[left] >= STATUS_ORDER[right] else right


def _apply_available_cash_limit(
    orders: list[dict[str, Any]],
    portfolio_value: float,
    available_cash_weight: float | None,
    available_cash_dollars: float | None,
    latest_price: dict[str, float],
) -> dict[str, Any]:
    resolved_cash = available_cash_dollars
    if resolved_cash is None and available_cash_weight is not None:
        resolved_cash = portfolio_value * available_cash_weight / 100.0
    buy_orders = [order for order in orders if order.get("side") == "BUY"]
    buy_demand = round(sum(float(order.get("dollar_change", 0.0)) for order in buy_orders), 2)
    summary = {
        "available_cash_dollars": None if resolved_cash is None else round(max(0.0, resolved_cash), 2),
        "available_cash_weight": available_cash_weight,
        "buy_demand_dollars": buy_demand,
        "cash_limited": False,
        "scale_factor": 1.0,
    }
    if resolved_cash is None or buy_demand <= 0:
        for order in buy_orders:
            order["cash_adjustment_status"] = "CASH_NOT_PROVIDED" if resolved_cash is None else "WITHIN_AVAILABLE_CASH"
        return summary
    available_cash = max(0.0, resolved_cash)
    if buy_demand <= available_cash:
        for order in buy_orders:
            order["cash_adjustment_status"] = "WITHIN_AVAILABLE_CASH"
        return summary

    scale_factor = available_cash / buy_demand if buy_demand else 1.0
    summary["cash_limited"] = True
    summary["scale_factor"] = round(scale_factor, 6)
    for order in buy_orders:
        original_dollar = float(order.get("dollar_change", 0.0))
        original_target = float(order.get("target_weight", 0.0))
        adjusted_dollar = round(original_dollar * scale_factor, 2)
        current_weight = float(order.get("current_weight", 0.0))
        adjusted_target = current_weight + (adjusted_dollar / portfolio_value * 100.0)
        ticker = str(order.get("ticker", ""))
        price = latest_price.get(ticker, 0.0)
        order["uncapped_dollar_change"] = round(original_dollar, 2)
        order["uncapped_target_weight"] = round(original_target, 6)
        order["dollar_change"] = adjusted_dollar
        order["target_weight"] = round(adjusted_target, 6)
        order["estimated_shares"] = 0 if price <= 0 else int(abs(adjusted_dollar) / price)
        order["cash_adjustment_status"] = "CASH_LIMITED"
    return summary
