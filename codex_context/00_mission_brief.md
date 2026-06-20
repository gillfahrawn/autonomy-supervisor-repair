Build a runnable prototype of counterexample-guided supervisor repair for L2+/L3 ADAS minimum-risk-maneuver logic.

Do not build full autonomous driving.
Do not build perception.
Do not depend on proprietary HIL traces.
Do not require CARLA to run the first demo.

The first demo uses a deterministic Python kinematic simulator to generate traces for cut-in and lead-braking scenarios. The architecture must expose a SimulatorAdapter so CARLA/ScenarioRunner can be added later.

Investor Framing: 
We compress embedded autonomy design review by generating candidate safety-supervisor repairs from failed scenario traces, then verifying them through simulator and formal/runtime checks.