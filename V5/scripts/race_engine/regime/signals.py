"""Directional regime signal calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from statistics import fmean, pstdev
from typing import Sequence


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class SignalResult:
    name: str
    value: int
    raw_inputs: dict[str, float | int | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.value not in (-1, 0, 1):
            raise ValueError("signal value must be -1, 0, or 1")


def spy_ols_trend_signal(spy_closes: Sequence[float]) -> SignalResult:
    values = _last(spy_closes, 200, "spy_closes")
    slope = normalized_ols_slope(values)
    return SignalResult("spy_200d_normalized_ols_slope", _sign(slope), {"normalized_slope": slope})


def spy_ma_buffer_signal(spy_closes: Sequence[float]) -> SignalResult:
    values = _last(spy_closes, 150, "spy_closes")
    close = values[-1]
    ma150 = fmean(values)
    ratio = close / ma150
    return SignalResult("spy_close_vs_150d_ma", _threshold(ratio, 1.02, 0.98), {"ratio": ratio})


def qqq_spy_relative_strength_signal(qqq_closes: Sequence[float], spy_closes: Sequence[float]) -> SignalResult:
    qqq = _last(qqq_closes, 64, "qqq_closes")
    spy = _last(spy_closes, 64, "spy_closes")
    rel = (qqq[-1] / qqq[0] - 1.0) - (spy[-1] / spy[0] - 1.0)
    return SignalResult("qqq_spy_63d_relative_strength", _threshold(rel, 0.03, -0.03), {"relative_strength": rel})


def breadth_signal(
    percent_above_50dma: float | None = None,
    rsp_closes: Sequence[float] | None = None,
    spy_closes: Sequence[float] | None = None,
) -> SignalResult:
    if percent_above_50dma is not None:
        value = _threshold(percent_above_50dma, 0.60, 0.40)
        return SignalResult("spy_constituent_breadth", value, {"percent_above_50dma": percent_above_50dma})
    if rsp_closes is None or spy_closes is None:
        raise ValueError("breadth fallback requires rsp_closes and spy_closes")
    rsp = _last(rsp_closes, 21, "rsp_closes")
    spy = _last(spy_closes, 21, "spy_closes")
    rel_series = [r / s for r, s in zip(rsp, spy)]
    slope = normalized_ols_slope(rel_series)
    return SignalResult("rsp_spy_21d_breadth_fallback", _threshold(slope, 0.0003, -0.0003), {"normalized_slope": slope})


def vix_level_signal(vix_value: float) -> SignalResult:
    if vix_value < 15:
        value = 1
    elif vix_value < 25:
        value = 0
    else:
        value = -1
    return SignalResult("vix_level", value, {"vix": vix_value})


def vix_change_signal(vix_values: Sequence[float]) -> SignalResult:
    values = _last(vix_values, 21, "vix_values")
    change = values[-1] / values[0] - 1.0
    return SignalResult("vix_20d_change", _threshold(change, -0.15, 0.20, inverted=True), {"change": change})


def spy_realized_vol_signal(spy_closes: Sequence[float]) -> SignalResult:
    values = _last(spy_closes, 22, "spy_closes")
    returns = [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]
    realized_vol = pstdev(returns) * sqrt(TRADING_DAYS_PER_YEAR) if len(returns) > 1 else 0.0
    return SignalResult("spy_21d_realized_vol", _threshold(realized_vol, 0.12, 0.22, inverted=True), {"realized_vol": realized_vol})


def hy_oas_signal(oas_bps: float) -> SignalResult:
    return SignalResult("hy_oas", _threshold(oas_bps, 350.0, 600.0, inverted=True), {"oas_bps": oas_bps})


def hyg_lqd_relative_trend_signal(hyg_closes: Sequence[float], lqd_closes: Sequence[float]) -> SignalResult:
    hyg = _last(hyg_closes, 22, "hyg_closes")
    lqd = _last(lqd_closes, 22, "lqd_closes")
    rel = (hyg[-1] / hyg[0] - 1.0) - (lqd[-1] / lqd[0] - 1.0)
    return SignalResult("hyg_lqd_21d_relative_trend", _threshold(rel, 0.01, -0.02), {"relative_trend": rel})


def t10y2y_signal(spread: float) -> SignalResult:
    return SignalResult("t10y2y", _threshold(spread, 0.50, -0.10), {"spread": spread})


def inflation_stress_flags(
    t10yie_values: Sequence[float],
    dbc_closes: Sequence[float],
    spy_closes: Sequence[float],
) -> tuple[bool, bool, dict[str, float]]:
    t10yie = _last(t10yie_values, 21, "t10yie_values")
    dbc = _last(dbc_closes, 64, "dbc_closes")
    spy = _last(spy_closes, 64, "spy_closes")
    breakeven_change = t10yie[-1] - t10yie[0]
    commodity_rs = (dbc[-1] / dbc[0] - 1.0) - (spy[-1] / spy[0] - 1.0)
    return (
        breakeven_change > 0.0,
        commodity_rs > 0.0,
        {"t10yie_4w_change": breakeven_change, "dbc_spy_63d_relative_strength": commodity_rs},
    )


def normalized_ols_slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise ValueError("at least two values are required")
    x_mean = (len(values) - 1) / 2
    y_mean = fmean(values)
    numerator = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(len(values)))
    slope = numerator / denominator
    return slope / values[-1] if values[-1] else 0.0


def _last(values: Sequence[float], count: int, name: str) -> tuple[float, ...]:
    if len(values) < count:
        raise ValueError(f"{name} requires at least {count} observations")
    return tuple(float(value) for value in values[-count:])


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _threshold(value: float, upper: float, lower: float, inverted: bool = False) -> int:
    if not inverted:
        return 1 if value >= upper else -1 if value <= lower else 0
    return 1 if value <= upper else -1 if value >= lower else 0

