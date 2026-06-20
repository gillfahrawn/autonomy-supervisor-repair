P1 Critical TTC response:
If ttc_s < 1.5 for more than 0.2s, then within 0.5s state must be MIN_RISK_MANEUVER or EMERGENCY_BRAKE, or brake_cmd > 0.6.

P2 Sensor degradation:
If sensor_confidence < 0.4 for more than 1.0s while ego_speed_mps > 10, then within 2.0s takeover_requested must be true or state must be DEGRADED_PERCEPTION / MIN_RISK_MANEUVER.

P3 No oscillation:
State must not alternate FOLLOWING ↔ DEGRADED_PERCEPTION more than 3 times in any 10s window.

P4 Avoid fake safety:
If ttc_s > 4.0 and lane_clear = true and no cut_in_active, EMERGENCY_BRAKE should not activate.

P5 Collision:
collision must always be false.