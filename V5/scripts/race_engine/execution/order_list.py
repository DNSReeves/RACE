"""Proposed order-list records. No broker transmission is implemented."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderListItem:
    ticker: str
    side: str
    target_weight: float
    current_weight: float
    dollar_change: float
    estimated_shares: int
    reason_code: str
    priority: str
    trade_quality_status: str
    entry_quality_status: str
    entry_quality_reasons: tuple[str, ...]
    recommended_action: str
    audit_event_ids: tuple[str, ...]


def proposed_order(
    ticker: str,
    target_weight: float,
    current_weight: float,
    portfolio_value: float,
    price: float,
    reason_code: str,
    priority: str,
    trade_quality_status: str,
    entry_quality_status: str = "EXECUTE",
    entry_quality_reasons: tuple[str, ...] = (),
    audit_event_ids: tuple[str, ...] = (),
) -> OrderListItem:
    dollar_change = portfolio_value * (target_weight - current_weight) / 100.0
    side = "BUY" if dollar_change > 0 else "SELL" if dollar_change < 0 else "HOLD"
    estimated_shares = 0 if price <= 0 else int(abs(dollar_change) / price)
    recommended_action = _recommended_action(side, trade_quality_status, entry_quality_status)
    return OrderListItem(
        ticker=ticker,
        side=side,
        target_weight=target_weight,
        current_weight=current_weight,
        dollar_change=round(dollar_change, 2),
        estimated_shares=estimated_shares,
        reason_code=reason_code,
        priority=priority,
        trade_quality_status=trade_quality_status,
        entry_quality_status=entry_quality_status,
        entry_quality_reasons=entry_quality_reasons,
        recommended_action=recommended_action,
        audit_event_ids=audit_event_ids,
    )


def _recommended_action(side: str, trade_quality_status: str, entry_quality_status: str) -> str:
    if trade_quality_status != "EXECUTE":
        return "REVIEW_MANUALLY"
    if side != "BUY":
        return "REVIEW_MANUALLY"
    if entry_quality_status == "EXECUTE":
        return "BUY_NOW"
    if entry_quality_status in {"ENTRY_CAUTION", "STAGE_ENTRY"}:
        return "STAGE_ENTRY"
    if entry_quality_status == "DEFER_OVERBOUGHT":
        return "DEFER_OVERBOUGHT"
    return "REVIEW_MANUALLY"
