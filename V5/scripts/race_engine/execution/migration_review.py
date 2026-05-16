"""Diagnostic migration review toward a pure RACE portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from race_engine.allocation.sleeves import BASELINE_UNIVERSE


CASH_EQUIVALENT_TICKERS = {
    "CASH",
    "CASH & CASH INVESTMENTS",
    "FDRXX",
    "SPAXX",
    "SPRXX",
    "SNSXX",
    "SNVXX",
    "SWVXX",
    "VMFXX",
    "VUSXX",
}
SLEEVE_BY_TICKER = {entry.ticker: entry.sleeve for entry in BASELINE_UNIVERSE}


@dataclass(frozen=True)
class MigrationReviewInputs:
    current_positions: dict[str, float]
    target_positions: dict[str, float]
    selected_etfs: dict[str, list[str]]
    orders: list[dict[str, Any]]
    portfolio_value: float
    tranche_fraction: float = 0.25


def build_migration_review(inputs: MigrationReviewInputs) -> dict[str, Any]:
    destination_by_sleeve = _destination_by_sleeve(inputs.selected_etfs, inputs.target_positions)
    order_by_ticker = {str(order.get("ticker")): order for order in inputs.orders}
    rows = [
        _migration_row(
            ticker=ticker,
            current_weight=float(weight),
            destination_by_sleeve=destination_by_sleeve,
            order_by_ticker=order_by_ticker,
            portfolio_value=inputs.portfolio_value,
            tranche_fraction=inputs.tranche_fraction,
        )
        for ticker, weight in sorted(inputs.current_positions.items(), key=lambda item: (_classification(str(item[0])), str(item[0])))
        if float(weight) > 0
    ]
    return {
        "diagnostic_only": True,
        "tranche_fraction": inputs.tranche_fraction,
        "rows": rows,
    }


def _migration_row(
    ticker: str,
    current_weight: float,
    destination_by_sleeve: dict[str, list[str]],
    order_by_ticker: dict[str, dict[str, Any]],
    portfolio_value: float,
    tranche_fraction: float,
) -> dict[str, Any]:
    normalized = ticker.strip().upper()
    sleeve = _classification(normalized)
    current_value = round(portfolio_value * current_weight / 100.0, 2)
    if normalized in CASH_EQUIVALENT_TICKERS:
        destination_sleeve = "cash"
        destination = _destinations_for_sleeve(destination_sleeve, destination_by_sleeve)
        return {
            "current_ticker": ticker,
            "classification": "cash",
            "current_weight": current_weight,
            "estimated_value": current_value,
            "race_destination_sleeve": destination_sleeve,
            "suggested_destination_tickers": destination,
            "migration_action": "USE_CASH_FIRST",
            "suggested_sell_percent": 0.0,
            "suggested_sell_dollars": 0.0,
            "entry_quality": _best_entry_quality(destination, order_by_ticker),
            "cash_impact": "funds_buys",
            "operator_note": f"{ticker} is cash or money market; use it before selling non-cash holdings.",
        }

    if sleeve != "outside_race_universe":
        destination = _destinations_for_sleeve(sleeve, destination_by_sleeve)
        action = "KEEP_RACE_ALIGNED" if normalized in destination else "HOLD_MANUALLY"
        note = (
            f"{ticker} is already in the RACE universe."
            if action == "KEEP_RACE_ALIGNED"
            else f"{ticker} is in the RACE universe but is not a current target; review manually before selling."
        )
        return {
            "current_ticker": ticker,
            "classification": sleeve,
            "current_weight": current_weight,
            "estimated_value": current_value,
            "race_destination_sleeve": sleeve,
            "suggested_destination_tickers": destination,
            "migration_action": action,
            "suggested_sell_percent": 0.0,
            "suggested_sell_dollars": 0.0,
            "entry_quality": _best_entry_quality(destination, order_by_ticker),
            "cash_impact": "no_sale_suggested",
            "operator_note": note,
        }

    destination_sleeve = _largest_underweight_sleeve(destination_by_sleeve, order_by_ticker)
    destination = _destinations_for_sleeve(destination_sleeve, destination_by_sleeve)
    entry_quality = _best_entry_quality(destination, order_by_ticker)
    action = _outside_position_action(entry_quality)
    sell_percent = round(tranche_fraction * 100.0, 2)
    return {
        "current_ticker": ticker,
        "classification": "outside_race_universe",
        "current_weight": current_weight,
        "estimated_value": current_value,
        "race_destination_sleeve": destination_sleeve,
        "suggested_destination_tickers": destination,
        "migration_action": action,
        "suggested_sell_percent": sell_percent,
        "suggested_sell_dollars": round(current_value * tranche_fraction, 2),
        "entry_quality": entry_quality,
        "cash_impact": "raises_cash_for_race_targets",
        "operator_note": f"{ticker} is outside the RACE universe; consider migrating one tranche after manual review.",
    }


def _destination_by_sleeve(selected_etfs: dict[str, list[str]], target_positions: dict[str, float]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for sleeve, tickers in selected_etfs.items():
        output[sleeve] = [ticker for ticker in tickers if ticker in target_positions]
    for ticker in target_positions:
        sleeve = _classification(ticker)
        output.setdefault(sleeve, [])
        if ticker not in output[sleeve]:
            output[sleeve].append(ticker)
    return output


def _destinations_for_sleeve(sleeve: str, destination_by_sleeve: dict[str, list[str]]) -> list[str]:
    return sorted(destination_by_sleeve.get(sleeve, []))


def _classification(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if normalized in CASH_EQUIVALENT_TICKERS:
        return "cash"
    return SLEEVE_BY_TICKER.get(normalized, "outside_race_universe")


def _best_entry_quality(destination: list[str], order_by_ticker: dict[str, dict[str, Any]]) -> str:
    qualities = [
        str(order_by_ticker[ticker].get("entry_quality_status", "EXECUTE"))
        for ticker in destination
        if ticker in order_by_ticker
    ]
    if "DEFER_OVERBOUGHT" in qualities:
        return "DEFER_OVERBOUGHT"
    if "STAGE_ENTRY" in qualities:
        return "STAGE_ENTRY"
    if "ENTRY_CAUTION" in qualities:
        return "ENTRY_CAUTION"
    return "EXECUTE"


def _outside_position_action(entry_quality: str) -> str:
    if entry_quality == "DEFER_OVERBOUGHT":
        return "DEFER_MIGRATION"
    if entry_quality in {"ENTRY_CAUTION", "STAGE_ENTRY"}:
        return "STAGE_MIGRATION"
    return "MIGRATE_IN_TRANCHES"


def _largest_underweight_sleeve(destination_by_sleeve: dict[str, list[str]], order_by_ticker: dict[str, dict[str, Any]]) -> str:
    demand_by_sleeve: dict[str, float] = {}
    for ticker, order in order_by_ticker.items():
        if order.get("side") != "BUY":
            continue
        sleeve = _classification(ticker)
        demand_by_sleeve[sleeve] = demand_by_sleeve.get(sleeve, 0.0) + float(order.get("uncapped_dollar_change", order.get("dollar_change", 0.0)))
    if demand_by_sleeve:
        return max(demand_by_sleeve.items(), key=lambda item: item[1])[0]
    if destination_by_sleeve:
        return sorted(destination_by_sleeve)[0]
    return "manual_review"
