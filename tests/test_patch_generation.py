from __future__ import annotations

from src.supervisor.patcher import generate_candidate_patches
from src.supervisor.state_machine import StateMachine


def test_patch_generation_covers_bounded_mutation_types(baseline_config):
    candidates = generate_candidate_patches(baseline_config)
    mutation_types = {candidate.mutation_type for candidate in candidates}
    assert len(candidates) >= 5
    assert "threshold_adjustment" in mutation_types
    assert "state_splitting" in mutation_types
    assert "hysteresis" in mutation_types
    assert "relative_velocity_guard" in mutation_types
    assert "cut_in_specific_guard" in mutation_types
    assert "architectural_combo" in mutation_types
    assert "recovery_constraint" in mutation_types
    assert any("2.50" in transition["when"] for candidate in candidates for transition in candidate.config["transitions"])
    assert any(
        "cut_in_active" in transition["when"]
        for candidate in candidates
        for transition in candidate.config["transitions"]
    )

    for candidate in candidates:
        StateMachine.from_dict(candidate.config)
