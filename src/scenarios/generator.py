from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from src.scenarios.scenario_schema import Scenario
from src.supervisor.schemas import load_yaml


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def generate_scenarios(config: dict[str, Any]) -> list[Scenario]:
    families = config.get("scenario_families") or {}
    split_config = config.get("split") or {}
    holdout_every = int(split_config.get("holdout_every", 5))
    holdout_offset = int(split_config.get("holdout_offset", 0))
    scenarios: list[Scenario] = []
    index = 0

    lead = families.get("lead_brake")
    if lead:
        keys = [
            "ego_speed_mps",
            "initial_gap_m",
            "lead_decel_mps2",
            "sensor_confidence_profile",
            "driver_takeover_delay_s",
        ]
        for values in itertools.product(*[_as_list(lead[k]) for k in keys]):
            params = dict(zip(keys, values, strict=True))
            scenarios.append(
                Scenario(
                    scenario_id=f"lead_brake_{index:04d}",
                    family="lead_brake",
                    ego_speed_mps=float(params["ego_speed_mps"]),
                    initial_gap_m=float(params["initial_gap_m"]),
                    lead_decel_mps2=float(params["lead_decel_mps2"]),
                    sensor_confidence_profile=str(params["sensor_confidence_profile"]),
                    driver_takeover_delay_s=float(params["driver_takeover_delay_s"]),
                    road_friction="dry",
                    seed=index,
                    split=_split_for_index(index, holdout_every, holdout_offset),
                )
            )
            index += 1

    cut_in = families.get("cut_in")
    if cut_in:
        keys = [
            "ego_speed_mps",
            "cut_in_gap_m",
            "cut_in_relative_speed_mps",
            "road_friction",
            "sensor_confidence_profile",
        ]
        for values in itertools.product(*[_as_list(cut_in[k]) for k in keys]):
            params = dict(zip(keys, values, strict=True))
            gap = float(params["cut_in_gap_m"])
            rel_speed = float(params["cut_in_relative_speed_mps"])
            friction = str(params["road_friction"])
            lead_decel = -3.0 if friction == "dry" else -2.0
            scenarios.append(
                Scenario(
                    scenario_id=f"cut_in_{index:04d}",
                    family="cut_in",
                    ego_speed_mps=float(params["ego_speed_mps"]),
                    initial_gap_m=90.0,
                    lead_decel_mps2=lead_decel,
                    sensor_confidence_profile=str(params["sensor_confidence_profile"]),
                    driver_takeover_delay_s=1.5,
                    cut_in_gap_m=gap,
                    cut_in_relative_speed_mps=rel_speed,
                    road_friction=friction,
                    seed=index,
                    split=_split_for_index(index, holdout_every, holdout_offset),
                )
            )
            index += 1

    return scenarios


def _split_for_index(index: int, holdout_every: int, holdout_offset: int) -> str:
    if holdout_every <= 1:
        return "holdout"
    return "holdout" if index % holdout_every == holdout_offset else "train"


def generate_scenarios_from_yaml(path: str | Path) -> list[Scenario]:
    return generate_scenarios(load_yaml(path))


def write_scenarios_jsonl(scenarios: list[Scenario], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            handle.write(json.dumps(scenario.to_dict(), sort_keys=True) + "\n")


def read_scenarios_jsonl(path: str | Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            scenarios.append(Scenario.from_dict(json.loads(line)))
    return scenarios
