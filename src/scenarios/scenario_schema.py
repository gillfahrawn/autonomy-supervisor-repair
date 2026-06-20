from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    family: str
    ego_speed_mps: float
    initial_gap_m: float
    lead_decel_mps2: float
    sensor_confidence_profile: str
    driver_takeover_delay_s: float
    cut_in_gap_m: float | None = None
    cut_in_relative_speed_mps: float | None = None
    road_friction: str = "dry"
    duration_s: float = 12.0
    dt_s: float = 0.1
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        return cls(
            scenario_id=str(data["scenario_id"]),
            family=str(data["family"]),
            ego_speed_mps=float(data["ego_speed_mps"]),
            initial_gap_m=float(data["initial_gap_m"]),
            lead_decel_mps2=float(data["lead_decel_mps2"]),
            sensor_confidence_profile=str(data["sensor_confidence_profile"]),
            driver_takeover_delay_s=float(data.get("driver_takeover_delay_s", 1.5)),
            cut_in_gap_m=(
                None if data.get("cut_in_gap_m") is None else float(data["cut_in_gap_m"])
            ),
            cut_in_relative_speed_mps=(
                None
                if data.get("cut_in_relative_speed_mps") is None
                else float(data["cut_in_relative_speed_mps"])
            ),
            road_friction=str(data.get("road_friction", "dry")),
            duration_s=float(data.get("duration_s", 12.0)),
            dt_s=float(data.get("dt_s", 0.1)),
            seed=int(data.get("seed", 0)),
        )

