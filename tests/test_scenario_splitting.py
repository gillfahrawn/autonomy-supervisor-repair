from __future__ import annotations

from src.scenarios.generator import generate_scenarios


def test_scenario_generation_assigns_train_holdout_splits():
    scenarios = generate_scenarios(
        {
            "split": {"holdout_every": 2, "holdout_offset": 0},
            "scenario_families": {
                "lead_brake": {
                    "ego_speed_mps": [18, 25],
                    "initial_gap_m": [25],
                    "lead_decel_mps2": [-5.0],
                    "sensor_confidence_profile": ["stable"],
                    "driver_takeover_delay_s": [1.5],
                }
            },
        }
    )
    assert [scenario.split for scenario in scenarios] == ["holdout", "train"]

