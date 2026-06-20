from __future__ import annotations

from src.supervisor.schemas import parse_supervisor_dict
from src.supervisor.state_machine import StateMachine


def _observation(**overrides):
    data = {
        "time_s": 0.0,
        "lead_distance_m": 30.0,
        "ego_speed_mps": 25.0,
        "lead_speed_mps": 20.0,
        "relative_velocity_mps": 5.0,
        "ttc_s": 6.0,
        "sensor_confidence": 0.95,
        "lane_clear": False,
        "cut_in_active": False,
    }
    data.update(overrides)
    return data


def test_state_machine_parsing(baseline_config):
    spec = parse_supervisor_dict(baseline_config)
    assert spec.initial_state == "CRUISE"
    assert "MIN_RISK_MANEUVER" in spec.states
    assert len(spec.transitions) == 4
    assert spec.actions["EMERGENCY_BRAKE"].brake_cmd == 1.0


def test_transition_evaluation_prioritizes_critical_ttc(baseline_config):
    machine = StateMachine.from_dict(baseline_config)
    decision = machine.step(_observation(time_s=0.0, lead_distance_m=30.0))
    assert decision.state == "FOLLOWING"

    decision = machine.step(_observation(time_s=0.1, ttc_s=1.0, sensor_confidence=0.2))
    assert decision.state == "MIN_RISK_MANEUVER"
    assert decision.transition_name == "following_to_mrm"

