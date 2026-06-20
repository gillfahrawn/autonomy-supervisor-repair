from __future__ import annotations

from src.evaluation.metrics import score_events


def test_scoring_uses_specified_weights():
    score = score_events(
        [
            {"property_id": "P5_COLLISION"},
            {"property_id": "P1_CRITICAL_TTC_RESPONSE"},
            {"property_id": "P2_SENSOR_DEGRADATION"},
            {"property_id": "P3_NO_OSCILLATION"},
            {"property_id": "P4_FAKE_SAFETY"},
        ]
    )
    assert score.score == 1175
    assert score.safety_score == 1175
    assert score.utility_penalty == 0
    assert score.total_score == 1175
    assert score.collisions == 1
    assert score.critical_ttc_violations == 1
    assert score.takeover_latency_violations == 1


def test_utility_metrics_are_reported_from_trace_rows():
    rows = []
    for index, state in enumerate(["CRUISE", "FOLLOWING", "MIN_RISK_MANEUVER", "MIN_RISK_MANEUVER"]):
        rows.append(
            {
                "time_s": index * 0.1,
                "scenario_id": "scenario",
                "run_id": "run",
                "ego_speed_mps": 20.0 - index,
                "lead_speed_mps": 20.0,
                "lead_distance_m": 100.0,
                "relative_velocity_mps": 0.0,
                "ttc_s": 999.0,
                "lane_clear": True,
                "cut_in_active": False,
                "sensor_confidence": 0.95,
                "takeover_requested": False,
                "state": state,
                "brake_cmd": 0.7 if state == "MIN_RISK_MANEUVER" else 0.0,
                "collision": False,
                "violation_labels": [],
            }
        )
    score = score_events([], rows)
    assert score.safety_score == 0
    assert score.unnecessary_mrm_activations == 1
    assert score.average_speed_loss_mps > 0
    assert score.utility_penalty > 0
