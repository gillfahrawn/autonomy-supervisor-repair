from __future__ import annotations

from src.evaluation.selection import rank_candidates_for_selection


def _candidate(
    patch_id: str,
    invariant_passed: bool,
    holdout_total: int,
    train_total: int,
    benign_penalty: int,
    benign_intervention_runs: int = 0,
):
    return {
        "patch_id": patch_id,
        "invariant_check": {"passed": invariant_passed},
        "split_results": {
            "train": {"score": {"total_score": train_total}},
            "holdout": {
                "score": {
                    "total_score": holdout_total,
                    "safety_score": holdout_total,
                }
            },
            "benign_challenge": {
                "score": {
                    "utility_penalty": benign_penalty,
                    "benign_intervention_runs": benign_intervention_runs,
                }
            },
        },
    }


def test_selection_prefers_invariant_passing_and_benign_penalty():
    ranked = rank_candidates_for_selection(
        [
            _candidate("unsafe_low_score", False, 10, 10, 0),
            _candidate("overconservative", True, 20, 20, 100, 3),
            _candidate("balanced", True, 30, 30, 0),
        ]
    )
    assert [candidate["patch_id"] for candidate in ranked] == [
        "balanced",
        "overconservative",
        "unsafe_low_score",
    ]

