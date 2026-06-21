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


def test_scenario_generation_adds_benign_challenge_split():
    scenarios = generate_scenarios(
        {
            "scenario_families": {
                "benign_challenge": {
                    "brief_sensor_blip": {
                        "ego_speed_mps": [25],
                        "initial_gap_m": [35],
                        "lead_relative_speed_mps": [0.0],
                        "sensor_confidence_profile": ["brief_blip"],
                    }
                }
            },
        }
    )
    assert len(scenarios) == 1
    assert scenarios[0].split == "benign_challenge"
    assert scenarios[0].risk_label == "benign"
    assert scenarios[0].scenario_type == "brief_sensor_blip"
