# Limitations

This prototype validates the mechanics of a counterexample-guided supervisor repair loop. It does not validate vehicle safety.

## Simulator Scope

- The simulator is deterministic, SIL-first, and pure Python.
- It is not CARLA.
- It does not model production vehicle dynamics, perception pipelines, sensor fusion, tire limits, actuator delay, road geometry, or controller feasibility.
- Some dangerous collisions persist even after MRM because the toy low-level braking model cannot avoid all severe cut-ins.

## Verification Scope

- Runtime properties are checked over generated traces.
- Invariant checks are formal-tool-compatible, but the demo does not require RTAMT or nuXmv.
- Passing invariant checks is not a production proof.
- `EMERGENCY_BRAKE` is currently reported as an unused optional state warning when applicable, not as a required-state failure.

## Scenario Scope

- The scenario suite is generated from synthetic families.
- v0.3 includes dangerous train, dangerous holdout, and benign challenge splits, but those splits are still toy distributions.
- Benign challenge scenarios are designed to expose false-positive safety behavior, not to represent the full space of safe real-world driving.

## Scoring Scope

- Safety and utility scores are proxy metrics for candidate ranking.
- Utility metrics such as speed loss, mission completion, MRM activation, takeover requests, and benign intervention rate are not validated comfort or operational KPIs.
- The selected patch wins under the current scoring and scenario families; changing the simulator, scenarios, properties, or weights can change the ranking.

## Dependency Scope

- CARLA, RTAMT, and nuXmv are intentionally not required dependencies.
- Existing adapter/export stubs mark future integration paths only.

## Correct Reading of v0.3

The correct conclusion is: this repository implements a bounded verification/repair loop that can find and reject overconservative supervisor patches in a deterministic toy setting. The incorrect conclusion is: this repository solves autonomous vehicle safety.
