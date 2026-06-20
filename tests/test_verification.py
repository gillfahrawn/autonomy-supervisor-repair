from __future__ import annotations

from src.verification.runtime_monitor import RuntimeMonitor
from src.verification.stl_properties import (
    P1_CRITICAL_TTC_RESPONSE,
    P2_SENSOR_DEGRADATION,
    P5_COLLISION,
)


def _row(index: int, **overrides):
    row = {
        "time_s": index * 0.1,
        "scenario_id": "scenario",
        "run_id": "run",
        "ego_speed_mps": 20.0,
        "lead_speed_mps": 10.0,
        "lead_distance_m": 10.0,
        "relative_velocity_mps": 10.0,
        "ttc_s": 1.0,
        "lane_clear": False,
        "cut_in_active": True,
        "sensor_confidence": 0.95,
        "takeover_requested": False,
        "state": "FOLLOWING",
        "brake_cmd": 0.2,
        "collision": False,
        "violation_labels": [],
    }
    row.update(overrides)
    return row


def test_property_checking_labels_counterexamples():
    rows = [_row(index) for index in range(35)]
    rows[-1]["collision"] = True
    events, annotated = RuntimeMonitor().evaluate(rows)
    labels = {event.property_id for event in events}
    assert P1_CRITICAL_TTC_RESPONSE in labels
    assert P5_COLLISION in labels
    assert any(P1_CRITICAL_TTC_RESPONSE in row["violation_labels"] for row in annotated)


def test_sensor_degradation_property():
    rows = [
        _row(index, ttc_s=999.0, sensor_confidence=0.35, cut_in_active=False)
        for index in range(45)
    ]
    events, _ = RuntimeMonitor().evaluate(rows)
    assert {event.property_id for event in events} == {P2_SENSOR_DEGRADATION}

