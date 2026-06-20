Generate candidate patches by applying bounded mutations:

1. Threshold adjustment:
   - ttc threshold: 1.0–2.5s
   - sensor_confidence threshold: 0.25–0.60
   - duration threshold: 0.3–2.0s

2. State splitting:
   - split FOLLOWING into FOLLOWING_STABLE and FOLLOWING_UNCERTAIN

3. Add hysteresis:
   - enter degraded if confidence < low threshold
   - exit degraded only if confidence > high threshold for N seconds

4. Transition guard addition:
   - add relative_velocity_mps condition
   - add ego_speed_mps condition
   - add cut_in_active condition

5. Recovery constraint:
   - block direct EMERGENCY_BRAKE → CRUISE
   - require SAFE_STOP or TAKEOVER_REQUESTED before CRUISE


The scoring function:

score = 1000 * collisions
      + 100 * critical_ttc_violations
      + 50 * takeover_latency_violations
      + 20 * oscillation_violations
      + 5 * unnecessary_emergency_brakes