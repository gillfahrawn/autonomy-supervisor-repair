from __future__ import annotations

TRACE_FIELDS = [
    "time_s",
    "scenario_id",
    "run_id",
    "ego_speed_mps",
    "lead_speed_mps",
    "lead_distance_m",
    "relative_velocity_mps",
    "ttc_s",
    "lane_clear",
    "cut_in_active",
    "sensor_confidence",
    "takeover_requested",
    "state",
    "brake_cmd",
    "collision",
    "violation_labels",
]


def compute_ttc(lead_distance_m: float, ego_speed_mps: float, lead_speed_mps: float) -> float:
    relative_velocity = ego_speed_mps - lead_speed_mps
    denominator = max(relative_velocity, 1.0e-3)
    return min(999.0, max(0.0, lead_distance_m) / denominator)


def normalize_trace_row(row: dict) -> dict:
    normalized = {field: row.get(field) for field in TRACE_FIELDS}
    normalized["time_s"] = round(float(normalized["time_s"]), 3)
    normalized["ego_speed_mps"] = round(float(normalized["ego_speed_mps"]), 4)
    normalized["lead_speed_mps"] = round(float(normalized["lead_speed_mps"]), 4)
    normalized["lead_distance_m"] = round(float(normalized["lead_distance_m"]), 4)
    normalized["relative_velocity_mps"] = round(float(normalized["relative_velocity_mps"]), 4)
    normalized["ttc_s"] = round(float(normalized["ttc_s"]), 4)
    normalized["sensor_confidence"] = round(float(normalized["sensor_confidence"]), 4)
    normalized["brake_cmd"] = round(float(normalized["brake_cmd"]), 4)
    normalized["lane_clear"] = bool(normalized["lane_clear"])
    normalized["cut_in_active"] = bool(normalized["cut_in_active"])
    normalized["takeover_requested"] = bool(normalized["takeover_requested"])
    normalized["collision"] = bool(normalized["collision"])
    labels = normalized["violation_labels"] or []
    normalized["violation_labels"] = list(labels)
    return normalized

