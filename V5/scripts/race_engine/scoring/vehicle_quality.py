"""Vehicle quality scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleMetrics:
    adv_usd: float
    expense_ratio: float
    issuer_score: float
    tracking_score: float


def vehicle_quality_score(metrics: VehicleMetrics) -> float:
    liquidity = min(1.0, metrics.adv_usd / 100_000_000.0)
    cost = max(0.0, 1.0 - metrics.expense_ratio / 1.00)
    issuer = min(max(metrics.issuer_score, 0.0), 1.0)
    tracking = min(max(metrics.tracking_score, 0.0), 1.0)
    return 0.35 * liquidity + 0.25 * cost + 0.20 * issuer + 0.20 * tracking

