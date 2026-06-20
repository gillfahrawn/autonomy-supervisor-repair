from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


P1_CRITICAL_TTC_RESPONSE = "P1_CRITICAL_TTC_RESPONSE"
P2_SENSOR_DEGRADATION = "P2_SENSOR_DEGRADATION"
P3_NO_OSCILLATION = "P3_NO_OSCILLATION"
P4_FAKE_SAFETY = "P4_FAKE_SAFETY"
P5_COLLISION = "P5_COLLISION"


PROPERTY_DESCRIPTIONS = {
    P1_CRITICAL_TTC_RESPONSE: (
        "If TTC remains below 1.5s for more than 0.2s, respond within 0.5s "
        "with MIN_RISK_MANEUVER, EMERGENCY_BRAKE, or brake_cmd > 0.6."
    ),
    P2_SENSOR_DEGRADATION: (
        "If sensor confidence remains below 0.4 for more than 1.0s while "
        "ego speed is above 10 m/s, request takeover or enter DEGRADED_PERCEPTION/MRM within 2.0s."
    ),
    P3_NO_OSCILLATION: (
        "Do not alternate FOLLOWING and DEGRADED_PERCEPTION more than 3 times in any 10s window."
    ),
    P4_FAKE_SAFETY: (
        "Do not activate EMERGENCY_BRAKE when TTC is above 4.0, lane is clear, and no cut-in is active."
    ),
    P5_COLLISION: "Collision must always be false.",
}


@dataclass(frozen=True)
class ViolationEvent:
    property_id: str
    run_id: str
    scenario_id: str
    time_s: float
    row_index: int
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

