# Technical Thesis

This project is a counterexample-guided repair loop for autonomy supervisor state machines. It treats failed driving traces as compiler feedback: run the current supervisor, find concrete property violations, generate bounded repair candidates, re-run verification-style checks, and report the patch that best balances dangerous-scenario improvement against benign-context overconservatism.

## Core Claim

The prototype demonstrates that a small supervisor state machine can be repaired with a tight loop:

```text
failed traces -> candidate repairs -> verifier/runtime checks -> ranked report
```

That is the intended claim. The project does not claim production ADAS validation or vehicle safety.

## Why Supervisor State Machines

Supervisor logic is a useful target for bounded repair because it is discrete, inspectable, and policy-heavy. The candidate patches in v0.3 do not rewrite the simulator or controller physics. They mutate supervisor-level behavior such as:

- splitting FOLLOWING into more specific following modes,
- adding confidence hysteresis,
- using relative velocity in TTC guards,
- adding cut-in-specific guard logic,
- constraining recovery from degraded or intervention states.

Those changes are small enough to compare with runtime properties and invariant checks, while still expressive enough to affect dangerous and benign scenario outcomes.

## Compile-Loop Compression

The workflow is similar to compressing a compile-debug loop:

| Compile Loop | Supervisor Repair Loop |
| --- | --- |
| Source program | Supervisor state machine |
| Compiler/test failure | Runtime property violation |
| Error location | Minimized trace window |
| Candidate edit | Bounded repair patch |
| Rebuild/test | Re-simulate and verify candidate |
| Build artifact | Selected patch plus report |

The value is not that any single generated patch is universally correct. The value is that the loop turns vague safety failures into concrete traces, bounded patches, comparable scores, and audit-friendly reports.

## Holdout and Benign Challenge

v0.3 adds a simple generalization and fake-safety pressure test:

- dangerous train scenarios provide the main repair pressure,
- dangerous holdout scenarios test whether the repair transfers beyond the training split,
- benign challenge scenarios test whether the repair creates false interventions in safe contexts.

The selected patch, `candidate_architectural_combo`, improved dangerous holdout performance by 27.61% while preserving a 0.00% benign intervention rate. More aggressive alternatives, such as `candidate_ttc_2_5`, `candidate_full_mvp_repair`, and `candidate_combined_ttc_sensor`, were rejected because they overfired in benign scenarios.

## Verification Boundary

The project currently uses runtime monitors and formal-tool-compatible invariant checks. CARLA, RTAMT, and nuXmv remain future adapter/export paths, not required dependencies. Passing these checks means the candidate satisfied this prototype's bounded checks; it does not mean the candidate is proven safe for production.

## Why This Is Useful Anyway

For supervisor repair research, a deterministic SIL-first prototype is enough to test the core loop:

- Can failures be reproduced?
- Can counterexamples be minimized?
- Can candidate patches be generated in bounded ways?
- Can dangerous improvement be separated from benign overconservatism?
- Can the final report explain why one patch won and others were rejected?

This repository answers those questions for the toy setting. It intentionally stops short of physical vehicle claims.
