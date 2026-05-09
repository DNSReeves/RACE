"""Transaction-cost model for RACE backtests."""

from __future__ import annotations


def one_way_transaction_cost(trade_value: float, aum: float) -> float:
    if aum > 1_000_000_000:
        slippage = 0.0010
    elif aum >= 100_000_000:
        slippage = 0.0020
    else:
        slippage = 0.0020
    impact = 0.0005 if trade_value > 500_000 else 0.0
    return trade_value * (slippage + impact)


def apply_transaction_costs(gross_return: float, trade_value: float, portfolio_value: float, aum: float) -> float:
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be positive")
    return gross_return - one_way_transaction_cost(trade_value, aum) / portfolio_value

