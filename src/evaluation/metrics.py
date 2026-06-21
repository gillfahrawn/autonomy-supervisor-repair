from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

from src.traces.io import group_by_run
from src.verification.stl_properties import (
    P1_CRITICAL_TTC_RESPONSE,
    P2_SENSOR_DEGRADATION,
    P3_NO_OSCILLATION,
    P4_FAKE_SAFETY,
    P5_COLLISION,
    ViolationEvent,
)


INTERVENTION_STATES = {
    "DEGRADED_PERCEPTION",
    "TAKEOVER_REQUESTED",
    "MIN_RISK_MANEUVER",
    "EMERGENCY_BRAKE",
    "SAFE_STOP",
}


@dataclass(frozen=True)
class ScoreBreakdown:
    collisions: int
    critical_ttc_violations: int
    takeover_latency_violations: int
    oscillation_violations: int
    fake_safety_violations: int
    unnecessary_emergency_brakes: int
    unnecessary_mrm_activations: int
    false_takeover_requests: int
    average_speed_loss_mps: float
    mission_completion_rate: float
    incomplete_missions: int
    intervention_runs: int
    intervention_rate: float
    benign_unnecessary_emergency_brakes: int
    benign_unnecessary_mrm_activations: int
    benign_false_takeover_requests: int
    benign_avoidable_speed_loss_mps: float
    benign_mission_completion_rate: float
    benign_incomplete_missions: int
    benign_intervention_runs: int
    benign_intervention_rate: float
    benign_run_count: int
    average_abs_jerk_mps3: float
    max_abs_jerk_mps3: float
    safety_score: int
    utility_penalty: int
    total_score: int
    score: int

    def to_dict(self) -> dict:
        return asdict(self)


def score_events(events: Iterable[ViolationEvent | dict], rows: list[dict] | None = None) -> ScoreBreakdown:
    counter: Counter[str] = Counter()
    for event in events:
        property_id = str(event["property_id"]) if isinstance(event, dict) else event.property_id
        counter[property_id] += 1

    collisions = counter[P5_COLLISION]
    critical = counter[P1_CRITICAL_TTC_RESPONSE]
    takeover = counter[P2_SENSOR_DEGRADATION]
    oscillation = counter[P3_NO_OSCILLATION]
    fake_safety = counter[P4_FAKE_SAFETY]
    safety_score = (
        1000 * collisions
        + 100 * critical
        + 50 * takeover
        + 20 * oscillation
        + 5 * fake_safety
    )

    utility = compute_utility_metrics(rows or [])
    if rows is None:
        utility["unnecessary_emergency_brakes"] = fake_safety
        utility_penalty = 0
    else:
        utility_penalty = compute_utility_penalty(utility)

    total_score = safety_score + utility_penalty
    return ScoreBreakdown(
        collisions=collisions,
        critical_ttc_violations=critical,
        takeover_latency_violations=takeover,
        oscillation_violations=oscillation,
        fake_safety_violations=fake_safety,
        unnecessary_emergency_brakes=int(utility["unnecessary_emergency_brakes"]),
        unnecessary_mrm_activations=int(utility["unnecessary_mrm_activations"]),
        false_takeover_requests=int(utility["false_takeover_requests"]),
        average_speed_loss_mps=round(float(utility["average_speed_loss_mps"]), 4),
        mission_completion_rate=round(float(utility["mission_completion_rate"]), 4),
        incomplete_missions=int(utility["incomplete_missions"]),
        intervention_runs=int(utility["intervention_runs"]),
        intervention_rate=round(float(utility["intervention_rate"]), 4),
        benign_unnecessary_emergency_brakes=int(utility["benign_unnecessary_emergency_brakes"]),
        benign_unnecessary_mrm_activations=int(utility["benign_unnecessary_mrm_activations"]),
        benign_false_takeover_requests=int(utility["benign_false_takeover_requests"]),
        benign_avoidable_speed_loss_mps=round(float(utility["benign_avoidable_speed_loss_mps"]), 4),
        benign_mission_completion_rate=round(float(utility["benign_mission_completion_rate"]), 4),
        benign_incomplete_missions=int(utility["benign_incomplete_missions"]),
        benign_intervention_runs=int(utility["benign_intervention_runs"]),
        benign_intervention_rate=round(float(utility["benign_intervention_rate"]), 4),
        benign_run_count=int(utility["benign_run_count"]),
        average_abs_jerk_mps3=round(float(utility["average_abs_jerk_mps3"]), 4),
        max_abs_jerk_mps3=round(float(utility["max_abs_jerk_mps3"]), 4),
        safety_score=int(round(safety_score)),
        utility_penalty=int(round(utility_penalty)),
        total_score=int(round(total_score)),
        score=int(round(total_score)),
    )


def compute_utility_metrics(rows: list[dict]) -> dict[str, float | int]:
    grouped = group_by_run(rows)
    if not grouped:
        return _empty_utility_metrics()

    unnecessary_emergency = 0
    unnecessary_mrm = 0
    false_takeovers = 0
    completed = 0
    intervention_runs = 0
    speed_loss_total = 0.0
    benign_unnecessary_emergency = 0
    benign_unnecessary_mrm = 0
    benign_false_takeovers = 0
    benign_completed = 0
    benign_incomplete = 0
    benign_intervention_runs = 0
    benign_run_count = 0
    benign_speed_loss_total = 0.0
    jerk_values: list[float] = []

    for run_rows in grouped.values():
        is_benign = _is_benign_run(run_rows)
        if is_benign:
            benign_run_count += 1

        previous_state = run_rows[0]["state"]
        run_had_intervention = False
        for row in run_rows:
            state = row["state"]
            if state in INTERVENTION_STATES or bool(row.get("takeover_requested")):
                run_had_intervention = True
            if state != previous_state and _false_positive_context(row):
                if state == "EMERGENCY_BRAKE":
                    unnecessary_emergency += 1
                    if is_benign:
                        benign_unnecessary_emergency += 1
                elif state == "MIN_RISK_MANEUVER":
                    unnecessary_mrm += 1
                    if is_benign:
                        benign_unnecessary_mrm += 1
                elif state == "TAKEOVER_REQUESTED":
                    false_takeovers += 1
                    if is_benign:
                        benign_false_takeovers += 1
            previous_state = state

        initial_speed = float(run_rows[0]["ego_speed_mps"])
        average_speed = sum(float(row["ego_speed_mps"]) for row in run_rows) / len(run_rows)
        speed_loss = max(0.0, initial_speed - average_speed)
        speed_loss_total += speed_loss
        if is_benign:
            benign_speed_loss_total += speed_loss

        final = run_rows[-1]
        collided = any(row["collision"] for row in run_rows)
        complete = (
            not collided
            and float(final["ego_speed_mps"]) > 2.0
            and final["state"] not in {"SAFE_STOP", "EMERGENCY_BRAKE", "MIN_RISK_MANEUVER"}
        )
        if complete:
            completed += 1
            if is_benign:
                benign_completed += 1
        elif is_benign:
            benign_incomplete += 1

        if run_had_intervention:
            intervention_runs += 1
            if is_benign:
                benign_intervention_runs += 1

        jerk_values.extend(_jerk_values(run_rows))

    run_count = len(grouped)
    incomplete = run_count - completed
    return {
        "unnecessary_emergency_brakes": unnecessary_emergency,
        "unnecessary_mrm_activations": unnecessary_mrm,
        "false_takeover_requests": false_takeovers,
        "average_speed_loss_mps": speed_loss_total / run_count,
        "mission_completion_rate": completed / run_count,
        "incomplete_missions": incomplete,
        "intervention_runs": intervention_runs,
        "intervention_rate": intervention_runs / run_count,
        "benign_unnecessary_emergency_brakes": benign_unnecessary_emergency,
        "benign_unnecessary_mrm_activations": benign_unnecessary_mrm,
        "benign_false_takeover_requests": benign_false_takeovers,
        "benign_avoidable_speed_loss_mps": (
            benign_speed_loss_total / benign_run_count
            if benign_run_count
            else 0.0
        ),
        "benign_mission_completion_rate": (
            benign_completed / benign_run_count
            if benign_run_count
            else 0.0
        ),
        "benign_incomplete_missions": benign_incomplete,
        "benign_intervention_runs": benign_intervention_runs,
        "benign_intervention_rate": (
            benign_intervention_runs / benign_run_count
            if benign_run_count
            else 0.0
        ),
        "benign_run_count": benign_run_count,
        "benign_total_speed_loss_mps": benign_speed_loss_total,
        "average_abs_jerk_mps3": (
            sum(abs(value) for value in jerk_values) / len(jerk_values)
            if jerk_values
            else 0.0
        ),
        "max_abs_jerk_mps3": max((abs(value) for value in jerk_values), default=0.0),
        "run_count": run_count,
        "total_speed_loss_mps": speed_loss_total,
    }


def compute_utility_penalty(utility: dict[str, float | int]) -> int:
    return int(
        round(
            10 * int(utility["unnecessary_emergency_brakes"])
            + 5 * int(utility["unnecessary_mrm_activations"])
            + 3 * int(utility["false_takeover_requests"])
            + 2.0 * float(utility["total_speed_loss_mps"])
            + 25 * int(utility["incomplete_missions"])
            + 0.1 * float(utility["average_abs_jerk_mps3"]) * int(utility["run_count"])
            + 100 * int(utility["benign_unnecessary_emergency_brakes"])
            + 60 * int(utility["benign_unnecessary_mrm_activations"])
            + 40 * int(utility["benign_false_takeover_requests"])
            + 30 * int(utility["benign_intervention_runs"])
            + 5.0 * float(utility["benign_total_speed_loss_mps"])
            + 30 * int(utility["benign_incomplete_missions"])
        )
    )


def _empty_utility_metrics() -> dict[str, float | int]:
    return {
        "unnecessary_emergency_brakes": 0,
        "unnecessary_mrm_activations": 0,
        "false_takeover_requests": 0,
        "average_speed_loss_mps": 0.0,
        "mission_completion_rate": 0.0,
        "incomplete_missions": 0,
        "intervention_runs": 0,
        "intervention_rate": 0.0,
        "benign_unnecessary_emergency_brakes": 0,
        "benign_unnecessary_mrm_activations": 0,
        "benign_false_takeover_requests": 0,
        "benign_avoidable_speed_loss_mps": 0.0,
        "benign_mission_completion_rate": 0.0,
        "benign_incomplete_missions": 0,
        "benign_intervention_runs": 0,
        "benign_intervention_rate": 0.0,
        "benign_run_count": 0,
        "benign_total_speed_loss_mps": 0.0,
        "average_abs_jerk_mps3": 0.0,
        "max_abs_jerk_mps3": 0.0,
        "run_count": 0,
        "total_speed_loss_mps": 0.0,
    }


def _false_positive_context(row: dict) -> bool:
    return _is_benign_row(row) or _safe_context(row)


def _is_benign_run(rows: list[dict]) -> bool:
    return any(_is_benign_row(row) for row in rows)


def _is_benign_row(row: dict) -> bool:
    return row.get("risk_label") == "benign" or row.get("split") == "benign_challenge"


def _safe_context(row: dict) -> bool:
    return (
        float(row["ttc_s"]) > 4.0
        and bool(row["lane_clear"])
        and not bool(row["cut_in_active"])
        and float(row["sensor_confidence"]) >= 0.4
    )


def _jerk_values(rows: list[dict]) -> list[float]:
    if len(rows) < 3:
        return []
    accelerations: list[float] = []
    for previous, current in zip(rows, rows[1:]):
        dt = max(1.0e-3, float(current["time_s"]) - float(previous["time_s"]))
        accelerations.append(
            (float(current["ego_speed_mps"]) - float(previous["ego_speed_mps"])) / dt
        )
    jerk_values: list[float] = []
    for previous_accel, current_accel, previous_row, current_row in zip(
        accelerations,
        accelerations[1:],
        rows[1:],
        rows[2:],
    ):
        dt = max(1.0e-3, float(current_row["time_s"]) - float(previous_row["time_s"]))
        jerk_values.append((current_accel - previous_accel) / dt)
    return jerk_values
