from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.traces.io import group_by_run, write_trace_pair
from src.traces.trace_schema import normalize_trace_row
from src.verification.stl_properties import (
    P1_CRITICAL_TTC_RESPONSE,
    P2_SENSOR_DEGRADATION,
    P3_NO_OSCILLATION,
    P4_FAKE_SAFETY,
    P5_COLLISION,
    ViolationEvent,
)


RESPONSE_STATES = {"MIN_RISK_MANEUVER", "EMERGENCY_BRAKE"}
DEGRADED_RESPONSE_STATES = {"DEGRADED_PERCEPTION", "MIN_RISK_MANEUVER"}


class RuntimeMonitor:
    def evaluate(self, rows: list[dict]) -> tuple[list[ViolationEvent], list[dict]]:
        normalized = [normalize_trace_row(row) for row in rows]
        events: list[ViolationEvent] = []
        grouped = group_by_run(normalized)
        for run_rows in grouped.values():
            events.extend(self._check_run(run_rows))
        annotated = self._annotate(normalized, events)
        return events, annotated

    def _check_run(self, rows: list[dict]) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        events.extend(self._check_p1(rows))
        events.extend(self._check_p2(rows))
        events.extend(self._check_p3(rows))
        events.extend(self._check_p4(rows))
        events.extend(self._check_p5(rows))
        return events

    def _check_p1(self, rows: list[dict]) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        active_start_index: int | None = None
        emitted = False
        for index, row in enumerate(rows):
            if row["ttc_s"] < 1.5:
                if active_start_index is None:
                    active_start_index = index
                    emitted = False
                start = rows[active_start_index]
                if not emitted and row["time_s"] - start["time_s"] > 0.2:
                    deadline = row["time_s"] + 0.5
                    responded = any(
                        future["time_s"] <= deadline
                        and (
                            future["state"] in RESPONSE_STATES
                            or float(future["brake_cmd"]) > 0.6
                        )
                        for future in rows[index:]
                    )
                    if not responded:
                        events.append(
                            self._event(
                                P1_CRITICAL_TTC_RESPONSE,
                                row,
                                index,
                                "Critical TTC persisted without timely MRM/emergency response.",
                                {
                                    "ttc_s": row["ttc_s"],
                                    "deadline_s": round(deadline, 3),
                                },
                            )
                        )
                        emitted = True
            else:
                active_start_index = None
                emitted = False
        return events

    def _check_p2(self, rows: list[dict]) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        active_start_index: int | None = None
        emitted = False
        for index, row in enumerate(rows):
            low_conf = row["sensor_confidence"] < 0.4 and row["ego_speed_mps"] > 10.0
            if low_conf:
                if active_start_index is None:
                    active_start_index = index
                    emitted = False
                start = rows[active_start_index]
                if not emitted and row["time_s"] - start["time_s"] > 1.0:
                    deadline = row["time_s"] + 2.0
                    responded = any(
                        future["time_s"] <= deadline
                        and (
                            future["takeover_requested"]
                            or future["state"] in DEGRADED_RESPONSE_STATES
                        )
                        for future in rows[index:]
                    )
                    if not responded:
                        events.append(
                            self._event(
                                P2_SENSOR_DEGRADATION,
                                row,
                                index,
                                "Sustained low sensor confidence lacked takeover/degraded response.",
                                {
                                    "sensor_confidence": row["sensor_confidence"],
                                    "deadline_s": round(deadline, 3),
                                },
                            )
                        )
                        emitted = True
            else:
                active_start_index = None
                emitted = False
        return events

    def _check_p3(self, rows: list[dict]) -> list[ViolationEvent]:
        transitions: list[tuple[float, int]] = []
        previous = rows[0]["state"] if rows else None
        for index, row in enumerate(rows[1:], start=1):
            state = row["state"]
            if {previous, state} == {"FOLLOWING", "DEGRADED_PERCEPTION"} and previous != state:
                transitions.append((row["time_s"], index))
            previous = state

        for start_pos, (time_s, index) in enumerate(transitions):
            count = sum(1 for t, _ in transitions[start_pos:] if t <= time_s + 10.0)
            if count > 3:
                row = rows[index]
                return [
                    self._event(
                        P3_NO_OSCILLATION,
                        row,
                        index,
                        "FOLLOWING/DEGRADED_PERCEPTION oscillated more than 3 times in 10s.",
                        {"alternations_in_window": count},
                    )
                ]
        return []

    def _check_p4(self, rows: list[dict]) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        for index, row in enumerate(rows):
            if (
                row["ttc_s"] > 4.0
                and row["lane_clear"]
                and not row["cut_in_active"]
                and row["state"] == "EMERGENCY_BRAKE"
            ):
                events.append(
                    self._event(
                        P4_FAKE_SAFETY,
                        row,
                        index,
                        "EMERGENCY_BRAKE activated when TTC and lane context were safe.",
                        {"ttc_s": row["ttc_s"]},
                    )
                )
                break
        return events

    def _check_p5(self, rows: list[dict]) -> list[ViolationEvent]:
        for index, row in enumerate(rows):
            if row["collision"]:
                return [
                    self._event(
                        P5_COLLISION,
                        row,
                        index,
                        "Collision occurred.",
                        {"lead_distance_m": row["lead_distance_m"]},
                    )
                ]
        return []

    @staticmethod
    def _event(
        property_id: str,
        row: dict,
        row_index: int,
        message: str,
        details: dict,
    ) -> ViolationEvent:
        return ViolationEvent(
            property_id=property_id,
            run_id=str(row["run_id"]),
            scenario_id=str(row["scenario_id"]),
            time_s=float(row["time_s"]),
            row_index=row_index,
            message=message,
            details=details,
        )

    @staticmethod
    def _annotate(rows: list[dict], events: list[ViolationEvent]) -> list[dict]:
        labels_by_position: dict[tuple[str, int], list[str]] = {}
        for event in events:
            labels_by_position.setdefault((event.run_id, event.row_index), []).append(event.property_id)

        counters: dict[str, int] = {}
        annotated: list[dict] = []
        for row in rows:
            run_id = str(row["run_id"])
            local_index = counters.get(run_id, 0)
            counters[run_id] = local_index + 1
            updated = dict(row)
            labels = list(updated.get("violation_labels") or [])
            labels.extend(labels_by_position.get((run_id, local_index), []))
            updated["violation_labels"] = sorted(set(labels))
            annotated.append(normalize_trace_row(updated))
        return annotated


def summarize_events(events: list[ViolationEvent]) -> dict[str, int]:
    counts = Counter(event.property_id for event in events)
    return dict(sorted(counts.items()))


def write_verification_artifacts(rows: list[dict], out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    monitor = RuntimeMonitor()
    events, annotated = monitor.evaluate(rows)
    summary = {
        "total_violations": len(events),
        "violation_counts": summarize_events(events),
        "events": [event.to_dict() for event in events],
    }
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    write_trace_pair(annotated, out / "annotated_traces.jsonl")
    return summary
