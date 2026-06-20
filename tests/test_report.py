from __future__ import annotations

import json

from src.evaluation.report import write_report


def _row(index: int):
    return {
        "time_s": index * 0.1,
        "scenario_id": "scenario",
        "run_id": "baseline__scenario",
        "ego_speed_mps": 20.0,
        "lead_speed_mps": 10.0,
        "lead_distance_m": 10.0 - index,
        "relative_velocity_mps": 10.0,
        "ttc_s": 1.0,
        "lane_clear": False,
        "cut_in_active": True,
        "sensor_confidence": 0.95,
        "takeover_requested": False,
        "state": "FOLLOWING",
        "brake_cmd": 0.2,
        "collision": index == 3,
        "violation_labels": ["P5_COLLISION"] if index == 3 else [],
    }


def test_report_generation_outputs_required_artifacts(tmp_path, baseline_config):
    baseline_result = {
        "failure_rate": 1.0,
        "run_count": 1,
        "failing_run_count": 1,
        "violation_counts": {"P5_COLLISION": 1},
        "score": {
            "collisions": 1,
            "critical_ttc_violations": 0,
            "takeover_latency_violations": 0,
            "oscillation_violations": 0,
            "unnecessary_emergency_brakes": 0,
            "score": 1000,
        },
        "events": [
            {
                "property_id": "P5_COLLISION",
                "run_id": "baseline__scenario",
                "scenario_id": "scenario",
                "time_s": 0.3,
                "row_index": 3,
                "message": "Collision occurred.",
                "details": {"lead_distance_m": 0.0},
            }
        ],
    }
    candidate_results = [
        {
            "patch_id": "candidate",
            "description": "Test candidate.",
            "score": {
                "collisions": 0,
                "critical_ttc_violations": 0,
                "takeover_latency_violations": 0,
                "oscillation_violations": 0,
                "unnecessary_emergency_brakes": 0,
                "score": 0,
            },
            "violation_counts": {},
            "invariant_check": {"passed": True, "failures": [], "reachable_states": []},
            "improvement_pct": 100.0,
        }
    ]
    write_report(
        tmp_path,
        baseline_result,
        candidate_results,
        [_row(index) for index in range(4)],
        baseline_config,
    )

    assert (tmp_path / "index.md").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "before_after.csv").exists()
    assert (tmp_path / "best_patch.yaml").exists()
    assert any((tmp_path / "failure_examples").iterdir())
    assert any((tmp_path / "trace_plots").iterdir())
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["best_patch_id"] == "candidate"

