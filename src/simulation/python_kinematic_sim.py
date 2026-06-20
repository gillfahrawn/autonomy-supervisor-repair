from __future__ import annotations

import math

from src.scenarios.scenario_schema import Scenario
from src.simulation.adapter import SimulatorAdapter
from src.supervisor.state_machine import StateMachine
from src.traces.trace_schema import compute_ttc, normalize_trace_row


class PythonKinematicSimulator(SimulatorAdapter):
    """Deterministic 1D lead-vehicle simulator for ADAS supervisor review."""

    def run_scenario(
        self,
        scenario: Scenario,
        supervisor_config: dict,
        run_id: str | None = None,
    ) -> list[dict]:
        machine = StateMachine.from_dict(supervisor_config)
        dt = scenario.dt_s
        steps = int(round(scenario.duration_s / dt)) + 1
        run = run_id or scenario.scenario_id

        ego_speed = scenario.ego_speed_mps
        lead_speed = scenario.ego_speed_mps
        lead_distance = scenario.initial_gap_m
        takeover_latched = False
        rows: list[dict] = []

        for step in range(steps):
            time_s = round(step * dt, 10)
            cut_in_active = self._cut_in_active(scenario, time_s)
            lane_clear = not cut_in_active
            if scenario.family == "cut_in" and not cut_in_active:
                lead_distance = max(lead_distance, 90.0)
                lead_speed = ego_speed
            elif scenario.family == "cut_in" and abs(time_s - 1.0) < (dt / 2.0):
                lead_distance = float(scenario.cut_in_gap_m or scenario.initial_gap_m)
                lead_speed = max(
                    0.0,
                    ego_speed + float(scenario.cut_in_relative_speed_mps or 0.0),
                )

            sensor_confidence = self._sensor_confidence(scenario.sensor_confidence_profile, time_s)
            relative_velocity = ego_speed - lead_speed
            ttc = compute_ttc(lead_distance, ego_speed, lead_speed)

            observation = {
                "time_s": time_s,
                "ego_speed_mps": ego_speed,
                "lead_speed_mps": lead_speed,
                "lead_distance_m": lead_distance,
                "relative_velocity_mps": relative_velocity,
                "ttc_s": ttc,
                "lane_clear": lane_clear,
                "cut_in_active": cut_in_active,
                "sensor_confidence": sensor_confidence,
            }
            decision = machine.step(observation)
            if decision.state == "TAKEOVER_REQUESTED":
                takeover_latched = True

            collision = lead_distance <= 0.0
            row = normalize_trace_row(
                {
                    "time_s": time_s,
                    "scenario_id": scenario.scenario_id,
                    "run_id": run,
                    "ego_speed_mps": ego_speed,
                    "lead_speed_mps": lead_speed,
                    "lead_distance_m": lead_distance,
                    "relative_velocity_mps": relative_velocity,
                    "ttc_s": ttc,
                    "lane_clear": lane_clear,
                    "cut_in_active": cut_in_active,
                    "sensor_confidence": sensor_confidence,
                    "takeover_requested": takeover_latched,
                    "state": decision.state,
                    "brake_cmd": decision.action.brake_cmd,
                    "collision": collision,
                    "violation_labels": [],
                }
            )
            rows.append(row)

            lead_accel = self._lead_accel(scenario, time_s)
            ego_accel = self._ego_accel(decision.action.target_accel_mps2, scenario.road_friction)
            next_ego_speed = max(0.0, ego_speed + ego_accel * dt)
            next_lead_speed = max(0.0, lead_speed + lead_accel * dt)
            avg_ego_speed = 0.5 * (ego_speed + next_ego_speed)
            avg_lead_speed = 0.5 * (lead_speed + next_lead_speed)
            lead_distance += (avg_lead_speed - avg_ego_speed) * dt
            ego_speed = next_ego_speed
            lead_speed = next_lead_speed

        return rows

    @staticmethod
    def _cut_in_active(scenario: Scenario, time_s: float) -> bool:
        return scenario.family == "cut_in" and time_s >= 1.0

    @staticmethod
    def _sensor_confidence(profile: str, time_s: float) -> float:
        if profile == "stable":
            return 0.95
        if profile == "dropout":
            return 0.35 if 2.0 <= time_s <= 6.0 else 0.95
        if profile == "noisy":
            if time_s < 1.5 or time_s > 7.0:
                return 0.90
            phase = int(math.floor((time_s - 1.5) / 0.4))
            return 0.34 if phase % 2 == 0 else 0.52
        return 0.95

    @staticmethod
    def _lead_accel(scenario: Scenario, time_s: float) -> float:
        if scenario.family == "lead_brake":
            return scenario.lead_decel_mps2 if time_s >= 1.0 else 0.0
        if scenario.family == "cut_in":
            if time_s < 1.0:
                return 0.0
            return 0.5 * scenario.lead_decel_mps2
        return 0.0

    @staticmethod
    def _ego_accel(target_accel_mps2: float, road_friction: str) -> float:
        min_accel = -7.0 if road_friction == "dry" else -5.0
        return max(min_accel, min(2.0, target_accel_mps2))

