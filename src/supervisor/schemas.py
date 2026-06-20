from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_STATES = [
    "CRUISE",
    "FOLLOWING",
    "DEGRADED_PERCEPTION",
    "TAKEOVER_REQUESTED",
    "MIN_RISK_MANEUVER",
    "EMERGENCY_BRAKE",
    "SAFE_STOP",
]


@dataclass(frozen=True)
class Transition:
    name: str
    source: str
    target: str
    condition: str


@dataclass(frozen=True)
class StateAction:
    brake_cmd: float
    target_accel_mps2: float


@dataclass(frozen=True)
class SupervisorSpec:
    states: list[str]
    initial_state: str
    transitions: list[Transition]
    actions: dict[str, StateAction]
    metadata: dict[str, Any]


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def dump_yaml(data: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def parse_supervisor_dict(data: dict[str, Any]) -> SupervisorSpec:
    states = list(data.get("states") or [])
    if not states:
        raise ValueError("Supervisor must define at least one state")

    initial_state = data.get("initial_state")
    if initial_state not in states:
        raise ValueError(f"initial_state {initial_state!r} is not in states")

    raw_actions = data.get("actions") or {}
    missing_actions = [state for state in states if state not in raw_actions]
    if missing_actions:
        raise ValueError(f"Missing actions for states: {', '.join(missing_actions)}")

    actions: dict[str, StateAction] = {}
    for state, action in raw_actions.items():
        if state not in states:
            raise ValueError(f"Action references unknown state {state!r}")
        actions[state] = StateAction(
            brake_cmd=float(action.get("brake_cmd", 0.0)),
            target_accel_mps2=float(action.get("target_accel_mps2", 0.0)),
        )

    transitions: list[Transition] = []
    for raw in data.get("transitions") or []:
        source = raw.get("from")
        target = raw.get("to")
        if source not in states:
            raise ValueError(f"Transition {raw.get('name')!r} has unknown source {source!r}")
        if target not in states:
            raise ValueError(f"Transition {raw.get('name')!r} has unknown target {target!r}")
        transitions.append(
            Transition(
                name=str(raw.get("name")),
                source=str(source),
                target=str(target),
                condition=str(raw.get("when", "True")),
            )
        )

    metadata = dict(data.get("metadata") or {})
    return SupervisorSpec(
        states=states,
        initial_state=str(initial_state),
        transitions=transitions,
        actions=actions,
        metadata=metadata,
    )


def supervisor_to_dict(spec: SupervisorSpec) -> dict[str, Any]:
    return {
        "metadata": dict(spec.metadata),
        "states": list(spec.states),
        "initial_state": spec.initial_state,
        "transitions": [
            {
                "name": transition.name,
                "from": transition.source,
                "to": transition.target,
                "when": transition.condition,
            }
            for transition in spec.transitions
        ],
        "actions": {
            state: {
                "brake_cmd": action.brake_cmd,
                "target_accel_mps2": action.target_accel_mps2,
            }
            for state, action in spec.actions.items()
        },
    }

