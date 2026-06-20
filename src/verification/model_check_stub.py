from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from src.supervisor.schemas import load_yaml


DEGRADED_OR_FAILURE_STATES = {
    "DEGRADED_PERCEPTION",
    "TAKEOVER_REQUESTED",
    "MIN_RISK_MANEUVER",
    "EMERGENCY_BRAKE",
}
SAFE_TARGET_STATES = {"TAKEOVER_REQUESTED", "MIN_RISK_MANEUVER", "SAFE_STOP"}


@dataclass(frozen=True)
class InvariantCheckResult:
    passed: bool
    failures: list[str]
    reachable_states: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_graph_invariants(supervisor: dict[str, Any] | str | Path) -> InvariantCheckResult:
    data = load_yaml(supervisor) if isinstance(supervisor, (str, Path)) else supervisor
    states = list(data.get("states") or [])
    initial = data.get("initial_state")
    transitions = list(data.get("transitions") or [])
    adjacency = {state: [] for state in states}
    for transition in transitions:
        adjacency.setdefault(transition.get("from"), []).append(transition.get("to"))

    reachable = _reachable(adjacency, initial)
    failures: list[str] = []

    unreachable = sorted(set(states) - reachable)
    if unreachable:
        failures.append(f"Unreachable states from {initial}: {', '.join(unreachable)}")

    dead_ends = sorted(
        state for state in states
        if state != "SAFE_STOP" and len(adjacency.get(state, [])) == 0
    )
    if dead_ends:
        failures.append(f"Dead-end states other than SAFE_STOP: {', '.join(dead_ends)}")

    if any(t.get("from") == "EMERGENCY_BRAKE" and t.get("to") == "CRUISE" for t in transitions):
        failures.append("Forbidden direct transition EMERGENCY_BRAKE -> CRUISE exists")

    for state in states:
        if state in DEGRADED_OR_FAILURE_STATES or "DEGRADED" in state or "FAIL" in state:
            if state in SAFE_TARGET_STATES:
                continue
            if not (_reachable(adjacency, state) & SAFE_TARGET_STATES):
                failures.append(
                    f"Degraded/failure state {state} lacks path to TAKEOVER_REQUESTED, "
                    "MIN_RISK_MANEUVER, or SAFE_STOP"
                )

    return InvariantCheckResult(
        passed=not failures,
        failures=failures,
        reachable_states=sorted(reachable),
    )


def _reachable(adjacency: dict[str, list[str]], initial: str | None) -> set[str]:
    if initial is None:
        return set()
    seen: set[str] = set()
    queue: deque[str] = deque([initial])
    while queue:
        state = queue.popleft()
        if state in seen:
            continue
        seen.add(state)
        for target in adjacency.get(state, []):
            if target not in seen:
                queue.append(target)
    return seen

