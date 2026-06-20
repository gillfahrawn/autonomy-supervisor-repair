from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.supervisor.schemas import (
    StateAction,
    SupervisorSpec,
    Transition,
    load_yaml,
    parse_supervisor_dict,
)


class SafeCondition:
    """Small boolean-expression evaluator for transition guards."""

    _ALLOWED_NODES = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.USub,
    )

    def __init__(self, expression: str) -> None:
        self.expression = expression or "True"
        parsed = ast.parse(self.expression, mode="eval")
        for node in ast.walk(parsed):
            if not isinstance(node, self._ALLOWED_NODES):
                raise ValueError(f"Unsupported expression node in guard {expression!r}: {type(node).__name__}")
        self._code = compile(parsed, "<transition_guard>", "eval")

    def evaluate(self, variables: dict[str, Any]) -> bool:
        allowed_names = dict(variables)
        allowed_names.setdefault("True", True)
        allowed_names.setdefault("False", False)
        return bool(eval(self._code, {"__builtins__": {}}, allowed_names))


@dataclass(frozen=True)
class StepDecision:
    state: str
    action: StateAction
    transition_name: str | None


@dataclass(frozen=True)
class _CompiledTransition:
    transition: Transition
    guard: SafeCondition


class StateMachine:
    def __init__(self, spec: SupervisorSpec) -> None:
        self.spec = spec
        self._compiled = [
            _CompiledTransition(transition=t, guard=SafeCondition(t.condition))
            for t in spec.transitions
        ]
        self.reset()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateMachine":
        return cls(parse_supervisor_dict(data))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "StateMachine":
        return cls.from_dict(load_yaml(path))

    def reset(self) -> None:
        self.state = self.spec.initial_state
        self.state_entered_time_s = 0.0

    def step(self, observation: dict[str, Any]) -> StepDecision:
        time_s = float(observation.get("time_s", 0.0))
        variables = dict(observation)
        variables["duration_s"] = max(0.0, time_s - self.state_entered_time_s)

        transition_name: str | None = None
        for compiled in self._compiled:
            transition = compiled.transition
            if transition.source != self.state:
                continue
            if compiled.guard.evaluate(variables):
                self.state = transition.target
                self.state_entered_time_s = time_s
                transition_name = transition.name
                break

        return StepDecision(
            state=self.state,
            action=self.spec.actions[self.state],
            transition_name=transition_name,
        )

