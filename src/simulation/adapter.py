from __future__ import annotations

from abc import ABC, abstractmethod

from src.scenarios.scenario_schema import Scenario


class SimulatorAdapter(ABC):
    @abstractmethod
    def run_scenario(
        self,
        scenario: Scenario,
        supervisor_config: dict,
        run_id: str | None = None,
    ) -> list[dict]:
        """Run one scenario and return trace rows."""

