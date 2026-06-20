from __future__ import annotations

from typing import Any


SELECTION_CRITERION = (
    "Select the candidate with the lowest holdout total score; break ties by "
    "train total score, then holdout safety score, then patch id."
)


def candidate_selection_key(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    train = candidate["split_results"]["train"]["score"]
    holdout = candidate["split_results"]["holdout"]["score"]
    return (
        int(holdout["total_score"]),
        int(train["total_score"]),
        int(holdout["safety_score"]),
        str(candidate["patch_id"]),
    )


def rank_candidates_for_selection(candidate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(candidate_results, key=candidate_selection_key)

