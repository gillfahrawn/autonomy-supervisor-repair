MVP:
Implement an internal graph invariant checker in Python.

Check:
- every state is reachable from initial_state
- no dead-end states except SAFE_STOP
- no forbidden direct transition EMERGENCY_BRAKE → CRUISE
- every degraded/failure state has a path to TAKEOVER_REQUESTED, MIN_RISK_MANEUVER, or SAFE_STOP

Optional:
Export equivalent nuXmv .smv model for future external model checking.