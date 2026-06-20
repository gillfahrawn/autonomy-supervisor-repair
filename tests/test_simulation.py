from __future__ import annotations

from src.scenarios.scenario_schema import Scenario
from src.simulation.python_kinematic_sim import PythonKinematicSimulator
from src.traces.trace_schema import TRACE_FIELDS


def test_trace_generation_has_required_schema(baseline_config):
    scenario = Scenario(
        scenario_id="unit_lead_brake",
        family="lead_brake",
        ego_speed_mps=25.0,
        initial_gap_m=25.0,
        lead_decel_mps2=-5.0,
        sensor_confidence_profile="stable",
        driver_takeover_delay_s=1.5,
        duration_s=2.0,
        dt_s=0.1,
    )
    rows = PythonKinematicSimulator().run_scenario(
        scenario,
        baseline_config,
        run_id="unit_run",
    )
    assert len(rows) == 21
    assert set(TRACE_FIELDS) == set(rows[0])
    assert rows[0]["run_id"] == "unit_run"
    assert rows[0]["state"] == "FOLLOWING"

