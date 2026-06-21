from __future__ import annotations

from typing import Any


SELECTION_CRITERION = (
    "Prefer candidates that pass formal-tool-compatible invariant checks. Among "
    "passing candidates, select the lowest holdout-aware challenge score: "
    "dangerous holdout total score + 10 * benign challenge utility penalty "
    "+ 250 * benign intervention runs. Break ties by dangerous holdout total, "
    "dangerous train total, then patch id. If no candidate passes invariants, "
    "rank by the same score and report the selection as not invariant-checked."
)


def candidate_selection_score(candidate: dict[str, Any]) -> int:
    train = candidate["split_results"]["train"]["score"]
    holdout = candidate["split_results"]["holdout"]["score"]
    benign = candidate["split_results"].get("benign_challenge", {}).get("score", {})
    benign_utility = int(benign.get("utility_penalty", 0))
    benign_intervention_runs = int(benign.get("benign_intervention_runs", 0))
    return (
        int(holdout["total_score"])
        + 10 * benign_utility
        + 250 * benign_intervention_runs
    )


def candidate_selection_key(candidate: dict[str, Any]) -> tuple[int, int, int, int, str]:
    train = candidate["split_results"]["train"]["score"]
    holdout = candidate["split_results"]["holdout"]["score"]
    return (
        0 if candidate["invariant_check"]["passed"] else 1,
        candidate_selection_score(candidate),
        int(holdout["total_score"]),
        int(train["total_score"]),
        str(candidate["patch_id"]),
    )


def rank_candidates_for_selection(candidate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(candidate_results, key=candidate_selection_key)
