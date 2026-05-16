from race_engine.construction.selector import RankedETF
from race_engine.execution.sleeve_leader_review import (
    SleeveLeaderReviewInputs,
    build_sleeve_leader_review,
    leader_persistence_status_by_sleeve,
    sleeve_leaders_from_review,
)


def test_sleeve_leader_is_computed_from_ranked_eligible_etfs() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.68),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
        )
    )

    assert review["intl_equity"]["leader"] == "EEM"
    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["held_ticker"] == "AVEM"
    assert comparison["score_gap"] == 0.14
    assert comparison["score_gap_tier"] == "MODERATE_ADVANTAGE"


def test_leader_already_held_holds_existing() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(RankedETF("EEM", "intl_equity", 0.82),),
            current_positions={"EEM": 5.0},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["replacement_action"] == "HOLD_EXISTING"
    assert comparison["replacement_allowed"] is False


def test_small_score_gap_does_not_recommend_replacement() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.78),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 10.0},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["score_gap_tier"] == "NO_ADVANTAGE"
    assert comparison["replacement_action"] == "HOLD_EXISTING"


def test_moderate_score_gap_with_unknown_persistence_blocks_replacement() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.68),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 10.0},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["replacement_action"] == "BLOCK_REPLACEMENT"
    assert "leader_persistence_unknown" in comparison["blockers"]


def test_underweight_sleeve_adds_to_leader_when_leader_not_held() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.68),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["replacement_action"] == "ADD_TO_LEADER"
    assert comparison["replacement_allowed"] is False


def test_entry_caution_stages_replacement_review() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.60),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
            leader_gate2_reasons={"EEM": ("rsi14_gt_72",)},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["leader_entry_quality_status"] == "ENTRY_CAUTION"
    assert comparison["replacement_action"] == "STAGE_ENTRY"


def test_defer_overbought_defers_replacement() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.60),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
            leader_gate2_reasons={"EEM": ("rsi14_gt_72", "close_gt_20dma_plus_2std", "close_gt_50dma_1p12")},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert comparison["leader_entry_quality_status"] == "DEFER_OVERBOUGHT"
    assert comparison["replacement_action"] == "DEFER_REPLACEMENT_OVERBOUGHT"


def test_avem_eem_fixture_does_not_automatically_sell_avem() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.68),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
        )
    )

    comparison = review["intl_equity"]["comparisons"][0]
    assert review["intl_equity"]["leader"] == "EEM"
    assert comparison["held_ticker"] == "AVEM"
    assert comparison["replacement_allowed"] is False
    assert comparison["replacement_action"] != "REPLACE_REVIEW"


def test_leader_persistence_statuses_compare_current_leaders_to_prior_state() -> None:
    ranked = (
        RankedETF("AVEM", "intl_equity", 0.68),
        RankedETF("EEM", "intl_equity", 0.82),
        RankedETF("SPY", "us_equity_core", 0.50),
    )

    statuses = leader_persistence_status_by_sleeve(
        ranked,
        {"intl_equity": "EEM", "us_equity_core": "IVV"},
    )

    assert statuses["intl_equity"] == "PERSISTENT"
    assert statuses["us_equity_core"] == "NEW_SIGNAL"


def test_sleeve_leaders_can_be_extracted_for_state_persistence() -> None:
    review = build_sleeve_leader_review(
        _inputs(
            ranked=(
                RankedETF("AVEM", "intl_equity", 0.68),
                RankedETF("EEM", "intl_equity", 0.82),
            ),
            current_positions={"AVEM": 5.0},
        )
    )

    assert sleeve_leaders_from_review(review) == {"intl_equity": "EEM"}


def _inputs(
    ranked: tuple[RankedETF, ...],
    current_positions: dict[str, float],
    leader_gate2_reasons: dict[str, tuple[str, ...]] | None = None,
) -> SleeveLeaderReviewInputs:
    return SleeveLeaderReviewInputs(
        ranked=ranked,
        current_positions=current_positions,
        target_positions={},
        sleeve_targets={"intl_equity": 10.0},
        leader_gate2_reasons=leader_gate2_reasons or {},
        gate_failures={},
        minimum_trade_weight=0.5,
    )
