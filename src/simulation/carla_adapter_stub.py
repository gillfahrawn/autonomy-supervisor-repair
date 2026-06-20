from __future__ import annotations

from src.scenarios.scenario_schema import Scenario
from src.simulation.adapter import SimulatorAdapter


class CarlaAdapterStub(SimulatorAdapter):
    def run_scenario(
        self,
        scenario: Scenario,
        supervisor_config: dict,
        run_id: str | None = None,
    ) -> list[dict]:
        raise NotImplementedError(
            "CARLA/ScenarioRunner support is intentionally optional for the MVP. "
            "Use PythonKinematicSimulator for local deterministic runs."
        )

