# Counterexample-Guided Supervisor Repair Report

**This demo validates the repair loop, not vehicle safety.**

This is a SIL-first toy simulator report with formal-tool-compatible invariant checks.

Some dangerous collisions persist even after MRM because the toy low-level braking model cannot avoid all severe cut-ins. This demo evaluates supervisor repair selection, not physical controller feasibility.

## Dangerous Scenario Performance

| Split | Runs | Failing Runs | Failure Rate | Safety Score | Utility Penalty | Total Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dangerous train baseline | 324 | 291 | 89.81% | 289650 | 14694 | 304344 |
| dangerous holdout baseline | 81 | 72 | 88.89% | 71250 | 3662 | 74912 |

## Benign Challenge Performance

| Suite | Runs | Intervention Rate | Benign MRM | False Takeover | Emergency Brakes | Completion Rate | Utility Penalty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 78 | 0.00% | 0 | 0 | 0 | 100.00% | 0 |
| selected patch | 78 | 0.00% | 0 | 0 | 0 | 100.00% | 1009 |

## Selection Criterion

Prefer candidates that pass formal-tool-compatible invariant checks. Among passing candidates, select the lowest holdout-aware challenge score: dangerous holdout total score + 10 * benign challenge utility penalty + 250 * benign intervention runs. Break ties by dangerous holdout total, dangerous train total, then patch id. If no candidate passes invariants, rank by the same score and report the selection as not invariant-checked.

## Candidate Rankings

| Selection Rank | Patch | Invariants | Selection Score | Holdout Total | Benign Penalty | Benign Intervention Rate | Train Total |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `candidate_architectural_combo` | pass | 64317 | 54227 | 1009 | 0.00% | 224265 |
| 2 | `candidate_full_mvp_repair` | pass | 199612 | 56802 | 12931 | 69.23% | 217266 |
| 3 | `candidate_cut_in_specific_guard` | fail | 57966 | 57966 | 0 | 0.00% | 231763 |
| 4 | `candidate_guarded_mrm` | fail | 63975 | 63975 | 0 | 0.00% | 252698 |
| 5 | `candidate_ttc_1_8` | fail | 63975 | 63975 | 0 | 0.00% | 252698 |
| 6 | `candidate_ttc_1_5` | fail | 68972 | 68972 | 0 | 0.00% | 274582 |
| 7 | `candidate_following_split` | fail | 72822 | 62732 | 1009 | 0.00% | 249113 |
| 8 | `candidate_recovery_constraints` | fail | 74910 | 74910 | 0 | 0.00% | 304338 |
| 9 | `candidate_degraded_hysteresis` | fail | 77337 | 77337 | 0 | 0.00% | 312259 |
| 10 | `candidate_sensor_0_40` | fail | 85266 | 77366 | 640 | 7.69% | 317190 |
| 11 | `candidate_ttc_2_1` | fail | 131896 | 59876 | 6527 | 34.62% | 238450 |
| 12 | `candidate_ttc_2_5` | fail | 195788 | 52928 | 12936 | 69.23% | 209656 |
| 13 | `candidate_combined_ttc_sensor` | fail | 215699 | 64939 | 13576 | 76.92% | 254701 |

## Pareto Table

| Pareto Rank | Patch | Front | Train Safety | Train Utility | Holdout Safety | Holdout Utility | Benign Penalty |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `candidate_ttc_2_5` | yes | 194100 | 15556 | 49050 | 3878 | 12936 |
| 2 | `candidate_full_mvp_repair` | yes | 202000 | 15266 | 53000 | 3802 | 12931 |
| 3 | `candidate_architectural_combo` | yes | 209300 | 14965 | 50500 | 3727 | 1009 |
| 4 | `candidate_following_split` | yes | 234600 | 14513 | 59100 | 3632 | 1009 |
| 5 | `candidate_combined_ttc_sensor` | yes | 241100 | 13601 | 61600 | 3339 | 13576 |
| 6 | `candidate_sensor_0_40` | yes | 304400 | 12790 | 74200 | 3166 | 640 |
| 7 | `candidate_cut_in_specific_guard` | no | 216450 | 15313 | 54150 | 3816 | 0 |
| 8 | `candidate_ttc_2_1` | no | 223100 | 15350 | 56050 | 3826 | 6527 |
| 9 | `candidate_guarded_mrm` | no | 237550 | 15148 | 60200 | 3775 | 0 |
| 10 | `candidate_ttc_1_8` | no | 237550 | 15148 | 60200 | 3775 | 0 |
| 11 | `candidate_ttc_1_5` | no | 259650 | 14932 | 65250 | 3722 | 0 |
| 12 | `candidate_recovery_constraints` | no | 289650 | 14688 | 71250 | 3660 | 0 |
| 13 | `candidate_degraded_hysteresis` | no | 298400 | 13859 | 73900 | 3437 | 0 |

## Best Patch Explanation

- Patch: `candidate_architectural_combo`
- Explanation: Combine FOLLOWING split, confidence hysteresis, relative/cut-in TTC guard, and recovery constraints.
- Selection score: 64317
- Train improvement: 26.31%
- Holdout improvement: 27.61%
- Train safety/utility/total: 209300 / 14965 / 224265
- Holdout safety/utility/total: 50500 / 3727 / 54227
- Benign utility penalty/intervention rate/completion: 1009 / 0.00% / 100.00%
- Formal-tool-compatible invariant checks passed: True
- Invariant warnings: ['Unused optional states with no incoming transitions: EMERGENCY_BRAKE']
- Unused optional states: ['EMERGENCY_BRAKE']

## Why the Selected Patch Won

- `candidate_architectural_combo` is not the most aggressive dangerous-scenario patch.
- It won because it preserved a 0.00% benign intervention rate while retaining a 27.61% dangerous holdout improvement.
- The selection criterion penalizes benign false positives, so lower dangerous holdout score alone is not sufficient.
- `candidate_ttc_2_5` improved dangerous holdout by 29.35% (total 52928) but produced 69.23% benign interventions (54 runs), so it was rejected as overconservative.
- `candidate_full_mvp_repair` improved dangerous holdout by 24.18% (total 56802) but produced 69.23% benign interventions (54 runs), so it was rejected as overconservative.
- `candidate_combined_ttc_sensor` improved dangerous holdout by 13.31% (total 64939) but produced 76.92% benign interventions (60 runs), so it was rejected as overconservative.

## Safety vs Utility/Fake-Safety Breakdown

- Safety score uses collision, critical TTC, sensor degradation, oscillation, and fake-safety property violations.
- Benign challenge utility penalty focuses on unnecessary emergency braking, unnecessary MRM activation, false takeover requests, avoidable speed loss, benign completion, and benign intervention rate.
- Dangerous performance and benign challenge performance are intentionally both part of selection, so a patch cannot win solely by braking earlier in dangerous cases.
- See `before_after.csv` and `pareto.csv` for complete candidate-level metrics.

## Utility Interpretation

- In v0.3, benign challenge utility differentiation is driven by both intervention counts and avoidable speed loss/completion effects.
- If the selected patch has zero benign MRM/takeover/emergency counts, fake-safety coverage should be read as passing these challenge cases, not as broad production evidence.

## Top Minimized Dangerous Counterexamples

- `P5_COLLISION` on `holdout` in `baseline__cut_in_0245` at t=2.2s, minimized to 1.8s-2.7s: [minimized_counterexamples/1_baseline__cut_in_0245.csv](minimized_counterexamples/1_baseline__cut_in_0245.csv), [plot](trace_plots/1_baseline__cut_in_0245.svg)
- `P5_COLLISION` on `holdout` in `baseline__cut_in_0300` at t=2.2s, minimized to 1.8s-2.7s: [minimized_counterexamples/2_baseline__cut_in_0300.csv](minimized_counterexamples/2_baseline__cut_in_0300.csv), [plot](trace_plots/2_baseline__cut_in_0300.svg)
- `P5_COLLISION` on `holdout` in `baseline__cut_in_0355` at t=2.2s, minimized to 1.8s-2.7s: [minimized_counterexamples/3_baseline__cut_in_0355.csv](minimized_counterexamples/3_baseline__cut_in_0355.csv), [plot](trace_plots/3_baseline__cut_in_0355.svg)
- `P5_COLLISION` on `holdout` in `baseline__cut_in_0315` at t=3.0s, minimized to 2.5s-3.5s: [minimized_counterexamples/4_baseline__cut_in_0315.csv](minimized_counterexamples/4_baseline__cut_in_0315.csv), [plot](trace_plots/4_baseline__cut_in_0315.svg)
- `P5_COLLISION` on `holdout` in `baseline__cut_in_0370` at t=3.0s, minimized to 2.5s-3.5s: [minimized_counterexamples/5_baseline__cut_in_0370.csv](minimized_counterexamples/5_baseline__cut_in_0370.csv), [plot](trace_plots/5_baseline__cut_in_0370.svg)

## Top Selected-Patch Benign False-Positive Examples

- None for the selected patch. The export directory is `selected_patch_benign_false_positives/` and is intentionally empty when no selected-patch benign false positives are found.

## Rejected Fake-Safety Examples

These are benign-challenge interventions from non-selected candidates that looked safer on some dangerous cases but overfired in safe contexts.

- `candidate_ttc_2_5`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 69.23%): [rejected_candidate_false_positives/candidate_ttc_2_5_1_candidate_ttc_2_5__benign_close_following_0000.csv](rejected_candidate_false_positives/candidate_ttc_2_5_1_candidate_ttc_2_5__benign_close_following_0000.csv), [plot](trace_plots/rejected_candidate_ttc_2_5_1_candidate_ttc_2_5__benign_close_following_0000.svg)
- `candidate_ttc_2_5`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 69.23%): [rejected_candidate_false_positives/candidate_ttc_2_5_2_candidate_ttc_2_5__benign_close_following_0001.csv](rejected_candidate_false_positives/candidate_ttc_2_5_2_candidate_ttc_2_5__benign_close_following_0001.csv), [plot](trace_plots/rejected_candidate_ttc_2_5_2_candidate_ttc_2_5__benign_close_following_0001.svg)
- `candidate_full_mvp_repair`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 69.23%): [rejected_candidate_false_positives/candidate_full_mvp_repair_1_candidate_full_mvp_repair__benign_close_following_0000.csv](rejected_candidate_false_positives/candidate_full_mvp_repair_1_candidate_full_mvp_repair__benign_close_following_0000.csv), [plot](trace_plots/rejected_candidate_full_mvp_repair_1_candidate_full_mvp_repair__benign_close_following_0000.svg)
- `candidate_full_mvp_repair`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 69.23%): [rejected_candidate_false_positives/candidate_full_mvp_repair_2_candidate_full_mvp_repair__benign_close_following_0001.csv](rejected_candidate_false_positives/candidate_full_mvp_repair_2_candidate_full_mvp_repair__benign_close_following_0001.csv), [plot](trace_plots/rejected_candidate_full_mvp_repair_2_candidate_full_mvp_repair__benign_close_following_0001.svg)
- `candidate_combined_ttc_sensor`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 76.92%): [rejected_candidate_false_positives/candidate_combined_ttc_sensor_1_candidate_combined_ttc_sensor__benign_close_following_0000.csv](rejected_candidate_false_positives/candidate_combined_ttc_sensor_1_candidate_combined_ttc_sensor__benign_close_following_0000.csv), [plot](trace_plots/rejected_candidate_combined_ttc_sensor_1_candidate_combined_ttc_sensor__benign_close_following_0000.svg)
- `candidate_combined_ttc_sensor`: `BENIGN_FALSE_POSITIVE_MIN_RISK_MANEUVER` in `benign_close_following` at t=1.0s (benign intervention rate 76.92%): [rejected_candidate_false_positives/candidate_combined_ttc_sensor_2_candidate_combined_ttc_sensor__benign_close_following_0001.csv](rejected_candidate_false_positives/candidate_combined_ttc_sensor_2_candidate_combined_ttc_sensor__benign_close_following_0001.csv), [plot](trace_plots/rejected_candidate_combined_ttc_sensor_2_candidate_combined_ttc_sensor__benign_close_following_0001.svg)

## Runtime Properties

- `P1_CRITICAL_TTC_RESPONSE`: If TTC remains below 1.5s for more than 0.2s, respond within 0.5s with MIN_RISK_MANEUVER, EMERGENCY_BRAKE, or brake_cmd > 0.6.
- `P2_SENSOR_DEGRADATION`: If sensor confidence remains below 0.4 for more than 1.0s while ego speed is above 10 m/s, request takeover or enter DEGRADED_PERCEPTION/MRM within 2.0s.
- `P3_NO_OSCILLATION`: Do not alternate FOLLOWING and DEGRADED_PERCEPTION more than 3 times in any 10s window.
- `P4_FAKE_SAFETY`: Do not activate EMERGENCY_BRAKE when TTC is above 4.0, lane is clear, and no cut-in is active.
- `P5_COLLISION`: Collision must always be false.

## Limitations

- The MVP remains a deterministic SIL-first toy simulator, not CARLA.
- Some dangerous collisions persist after MRM because the toy low-level braking model cannot avoid all severe cut-ins; this is not evidence about physical controller feasibility.
- CARLA, RTAMT, and nuXmv remain optional future adapter/export paths, not required dependencies.
- Utility metrics are proxy measures intended for repair ranking, not validated vehicle comfort or mission KPIs.
