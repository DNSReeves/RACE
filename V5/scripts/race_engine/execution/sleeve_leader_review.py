"""Diagnostic sleeve leader review for dry-run artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from race_engine.allocation.sleeves import BASELINE_UNIVERSE
from race_engine.construction.selector import RankedETF


@dataclass(frozen=True)
class SleeveLeaderReviewInputs:
    ranked: tuple[RankedETF, ...]
    current_positions: dict[str, float]
    target_positions: dict[str, float]
    sleeve_targets: dict[str, float]
    leader_gate2_reasons: dict[str, tuple[str, ...]]
    gate_failures: dict[str, dict[str, tuple[str, ...]]]
    minimum_trade_weight: float
    leader_persistence_by_sleeve: dict[str, str] | None = None


def build_sleeve_leader_review(inputs: SleeveLeaderReviewInputs) -> dict[str, dict[str, Any]]:
    leaders = _leaders_by_sleeve(inputs.ranked)
    scores = {item.ticker: item.score for item in inputs.ranked}
    sleeve_by_ticker = _sleeve_by_ticker(inputs.ranked)
    persistence_by_sleeve = inputs.leader_persistence_by_sleeve or {}
    review: dict[str, dict[str, Any]] = {}

    for sleeve, leader in sorted(leaders.items()):
        held_tickers = tuple(
            sorted(
                ticker
                for ticker, weight in inputs.current_positions.items()
                if weight > 0 and sleeve_by_ticker.get(ticker) == sleeve
            )
        )
        leader_entry_quality = _entry_quality_from_gate2(inputs.leader_gate2_reasons.get(leader.ticker, ()))
        persistence = persistence_by_sleeve.get(sleeve, "UNKNOWN")
        sleeve_underweight = _sleeve_underweight(sleeve, inputs.current_positions, inputs.sleeve_targets, sleeve_by_ticker)
        leader_held = leader.ticker in held_tickers
        comparisons = [
            _comparison(
                sleeve=sleeve,
                leader=leader,
                held_ticker=held_ticker,
                held_score=scores.get(held_ticker),
                leader_entry_quality=leader_entry_quality,
                persistence=persistence,
                held_weight=inputs.current_positions.get(held_ticker, 0.0),
                minimum_trade_weight=inputs.minimum_trade_weight,
                held_has_gate_failure=bool(inputs.gate_failures.get(held_ticker)),
                add_to_leader=not leader_held and sleeve_underweight,
            )
            for held_ticker in held_tickers
        ]
        if not held_tickers and sleeve_underweight:
            comparisons.append(
                _new_allocation_comparison(
                    leader=leader,
                    leader_entry_quality=leader_entry_quality,
                    persistence=persistence,
                )
            )

        review[sleeve] = {
            "leader": leader.ticker,
            "leader_score": round(leader.score, 6),
            "held_tickers": list(held_tickers),
            "comparisons": comparisons,
        }
    return review


def score_gap_tier(score_gap: float) -> str:
    """Classify the raw RACE composite-score gap using diagnostic review bands."""
    if score_gap < 0.05:
        return "NO_ADVANTAGE"
    if score_gap < 0.10:
        return "SMALL_ADVANTAGE"
    if score_gap < 0.15:
        return "MODERATE_ADVANTAGE"
    return "STRONG_ADVANTAGE"


def _leaders_by_sleeve(ranked: tuple[RankedETF, ...]) -> dict[str, RankedETF]:
    leaders: dict[str, RankedETF] = {}
    for item in ranked:
        current = leaders.get(item.sleeve)
        if current is None or item.score > current.score:
            leaders[item.sleeve] = item
    return leaders


def _sleeve_by_ticker(ranked: tuple[RankedETF, ...]) -> dict[str, str]:
    sleeves = {entry.ticker: entry.sleeve for entry in BASELINE_UNIVERSE}
    sleeves.update({item.ticker: item.sleeve for item in ranked})
    return sleeves


def _comparison(
    sleeve: str,
    leader: RankedETF,
    held_ticker: str,
    held_score: float | None,
    leader_entry_quality: str,
    persistence: str,
    held_weight: float,
    minimum_trade_weight: float,
    held_has_gate_failure: bool,
    add_to_leader: bool,
) -> dict[str, Any]:
    if held_ticker == leader.ticker:
        return {
            "held_ticker": held_ticker,
            "held_score": _round_or_none(held_score),
            "score_gap": 0.0,
            "score_gap_tier": "NO_ADVANTAGE",
            "leader_entry_quality_status": leader_entry_quality,
            "leader_persistence_status": persistence,
            "replacement_action": "HOLD_EXISTING",
            "replacement_allowed": False,
            "blockers": ["leader_already_held", "diagnostic_only_phase"],
            "operator_note": f"{leader.ticker} is already held in {sleeve}; no replacement is indicated.",
        }

    gap = leader.score - (held_score if held_score is not None else 0.0)
    tier = score_gap_tier(gap)
    if add_to_leader:
        action = _add_to_leader_action(leader_entry_quality)
        blockers = _add_to_leader_blockers(leader_entry_quality, persistence)
    else:
        action, blockers = _replacement_action(
            tier=tier,
            leader_entry_quality=leader_entry_quality,
            persistence=persistence,
            held_weight=held_weight,
            minimum_trade_weight=minimum_trade_weight,
            held_has_gate_failure=held_has_gate_failure,
            held_score=held_score,
        )
    return {
        "held_ticker": held_ticker,
        "held_score": _round_or_none(held_score),
        "score_gap": round(gap, 6),
        "score_gap_tier": tier,
        "leader_entry_quality_status": leader_entry_quality,
        "leader_persistence_status": persistence,
        "replacement_action": action,
        "replacement_allowed": False,
        "blockers": blockers,
        "operator_note": _operator_note(leader.ticker, held_ticker, tier, action),
    }


def _new_allocation_comparison(
    leader: RankedETF,
    leader_entry_quality: str,
    persistence: str,
) -> dict[str, Any]:
    action = _add_to_leader_action(leader_entry_quality)
    blockers = _add_to_leader_blockers(leader_entry_quality, persistence)
    return {
        "held_ticker": "",
        "held_score": None,
        "score_gap": None,
        "score_gap_tier": "NO_HELD_POSITION",
        "leader_entry_quality_status": leader_entry_quality,
        "leader_persistence_status": persistence,
        "replacement_action": action,
        "replacement_allowed": False,
        "blockers": blockers,
        "operator_note": f"{leader.ticker} is the sleeve leader for new allocation review; no existing holding is being replaced.",
    }


def _replacement_action(
    tier: str,
    leader_entry_quality: str,
    persistence: str,
    held_weight: float,
    minimum_trade_weight: float,
    held_has_gate_failure: bool,
    held_score: float | None,
) -> tuple[str, list[str]]:
    blockers = ["diagnostic_only_phase"]
    if held_weight < minimum_trade_weight:
        blockers.append("below_minimum_trade_weight")
    if persistence == "UNKNOWN":
        blockers.append("leader_persistence_unknown")
    if leader_entry_quality == "DEFER_OVERBOUGHT":
        return "DEFER_REPLACEMENT_OVERBOUGHT", [*blockers, "leader_overbought"]
    if leader_entry_quality in {"ENTRY_CAUTION", "STAGE_ENTRY"}:
        return "STAGE_ENTRY", [*blockers, "entry_quality_not_execute"]
    if tier in {"NO_ADVANTAGE", "SMALL_ADVANTAGE"}:
        return "HOLD_EXISTING", [*blockers, "score_advantage_not_material"]
    if persistence == "UNKNOWN":
        return "BLOCK_REPLACEMENT", blockers
    if tier == "STRONG_ADVANTAGE" and persistence == "PERSISTENT" and (held_has_gate_failure or _weak_score(held_score)):
        return "REPLACE_REVIEW", blockers
    return "BLOCK_REPLACEMENT", [*blockers, "replacement_safety_requirements_not_met"]


def _add_to_leader_action(leader_entry_quality: str) -> str:
    if leader_entry_quality == "DEFER_OVERBOUGHT":
        return "DEFER_REPLACEMENT_OVERBOUGHT"
    if leader_entry_quality in {"ENTRY_CAUTION", "STAGE_ENTRY"}:
        return "STAGE_ENTRY"
    if leader_entry_quality == "EXECUTE":
        return "ADD_TO_LEADER"
    return "REVIEW_MANUALLY"


def _add_to_leader_blockers(leader_entry_quality: str, persistence: str) -> list[str]:
    blockers = ["diagnostic_only_phase"]
    if persistence == "UNKNOWN":
        blockers.append("leader_persistence_unknown")
    if leader_entry_quality != "EXECUTE":
        blockers.append("entry_quality_not_execute")
    return blockers


def _entry_quality_from_gate2(gate2_reasons: tuple[str, ...]) -> str:
    reason_count = len(gate2_reasons)
    if reason_count == 0:
        return "EXECUTE"
    if reason_count == 1:
        return "ENTRY_CAUTION"
    if reason_count == 2:
        return "STAGE_ENTRY"
    return "DEFER_OVERBOUGHT"


def _sleeve_underweight(
    sleeve: str,
    current_positions: dict[str, float],
    sleeve_targets: dict[str, float],
    sleeve_by_ticker: dict[str, str],
) -> bool:
    current = sum(weight for ticker, weight in current_positions.items() if sleeve_by_ticker.get(ticker) == sleeve)
    return current < sleeve_targets.get(sleeve, 0.0)


def _weak_score(score: float | None) -> bool:
    return score is None or score < 0.0


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _operator_note(leader: str, held_ticker: str, tier: str, action: str) -> str:
    if action == "HOLD_EXISTING":
        return f"{leader} does not have enough advantage over {held_ticker} to justify replacement review."
    if action == "STAGE_ENTRY":
        return f"{leader} leads {held_ticker}, but entry quality calls for staging rather than replacement."
    if action == "DEFER_REPLACEMENT_OVERBOUGHT":
        return f"{leader} leads {held_ticker}, but replacement is deferred because the leader is overbought."
    if action == "REPLACE_REVIEW":
        return f"{leader} has a {tier.lower()} over {held_ticker}; replacement remains manual-review only."
    if action == "ADD_TO_LEADER":
        return f"{leader} leads {held_ticker} and the sleeve is underweight; review adding to the leader without automatic replacement."
    return f"{leader} currently leads {held_ticker}, but replacement is blocked by diagnostic safeguards."
