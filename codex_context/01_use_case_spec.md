use case defined as:

L2+/L3 highway ADAS supervisor for lead-vehicle hard braking and cut-in events.

The ego vehicle has a simple low-level controller. The startup prototype only controls the high-level supervisor state machine:
- CRUISE
- FOLLOWING
- DEGRADED_PERCEPTION
- TAKEOVER_REQUESTED
- MIN_RISK_MANEUVER
- EMERGENCY_BRAKE
- SAFE_STOP

failure modes defined as:

1. Late minimum-risk maneuver when TTC becomes critical.
2. No takeover request during sustained low sensor confidence.
3. Oscillation between FOLLOWING and DEGRADED_PERCEPTION.
4. Overconservative emergency braking when TTC is safe.
5. Unsafe recovery from EMERGENCY_BRAKE to CRUISE.