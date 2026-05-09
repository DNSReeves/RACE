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
    audit_event_ids: tuple[str, ...] = (),
) -> OrderListItem:
    dollar_change = portfolio_value * (target_weight - current_weight) / 100.0
    side = "BUY" if dollar_change > 0 else "SELL" if dollar_change < 0 else "HOLD"
    estimated_shares = 0 if price <= 0 else int(abs(dollar_change) / price)
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
        audit_event_ids=audit_event_ids,
    )

