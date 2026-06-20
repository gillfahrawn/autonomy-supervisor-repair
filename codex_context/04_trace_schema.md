Each simulation step emits a row with:

time_s: float
scenario_id: string
run_id: string
ego_speed_mps: float
lead_speed_mps: float
lead_distance_m: float
relative_velocity_mps: float
ttc_s: float
lane_clear: bool
cut_in_active: bool
sensor_confidence: float
takeover_requested: bool
state: string
brake_cmd: float
collision: bool
violation_labels: list[string]