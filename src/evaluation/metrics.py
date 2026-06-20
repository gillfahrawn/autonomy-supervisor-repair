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
        return {
            "unnecessary_emergency_brakes": 0,
            "unnecessary_mrm_activations": 0,
            "false_takeover_requests": 0,
            "average_speed_loss_mps": 0.0,
            "mission_completion_rate": 0.0,
            "incomplete_missions": 0,
            "average_abs_jerk_mps3": 0.0,
            "max_abs_jerk_mps3": 0.0,
            "run_count": 0,
            "total_speed_loss_mps": 0.0,
        }

    unnecessary_emergency = 0
    unnecessary_mrm = 0
    false_takeovers = 0
    completed = 0
    speed_loss_total = 0.0
    jerk_values: list[float] = []

    for run_rows in grouped.values():
        previous_state = run_rows[0]["state"]
        for row in run_rows:
            state = row["state"]
            if state != previous_state and _safe_context(row):
                if state == "EMERGENCY_BRAKE":
                    unnecessary_emergency += 1
                elif state == "MIN_RISK_MANEUVER":
                    unnecessary_mrm += 1
                elif state == "TAKEOVER_REQUESTED":
                    false_takeovers += 1
            previous_state = state

        initial_speed = float(run_rows[0]["ego_speed_mps"])
        average_speed = sum(float(row["ego_speed_mps"]) for row in run_rows) / len(run_rows)
        speed_loss_total += max(0.0, initial_speed - average_speed)

        final = run_rows[-1]
        collided = any(row["collision"] for row in run_rows)
        if (
            not collided
            and float(final["ego_speed_mps"]) > 2.0
            and final["state"] not in {"SAFE_STOP", "EMERGENCY_BRAKE", "MIN_RISK_MANEUVER"}
        ):
            completed += 1

        jerk_values.extend(_jerk_values(run_rows))

    run_count = len(grouped)
    average_speed_loss = speed_loss_total / run_count
    incomplete = run_count - completed
    return {
        "unnecessary_emergency_brakes": unnecessary_emergency,
        "unnecessary_mrm_activations": unnecessary_mrm,
        "false_takeover_requests": false_takeovers,
        "average_speed_loss_mps": average_speed_loss,
        "mission_completion_rate": completed / run_count,
        "incomplete_missions": incomplete,
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
        )
    )


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
