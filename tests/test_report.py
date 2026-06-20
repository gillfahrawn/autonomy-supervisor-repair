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


def _score(collisions: int, safety: int, utility: int = 0):
    total = safety + utility
    return {
        "collisions": collisions,
        "critical_ttc_violations": 0,
        "takeover_latency_violations": 0,
        "oscillation_violations": 0,
        "fake_safety_violations": 0,
        "unnecessary_emergency_brakes": 0,
        "unnecessary_mrm_activations": 0,
        "false_takeover_requests": 0,
        "average_speed_loss_mps": 0.0,
        "mission_completion_rate": 1.0,
        "incomplete_missions": 0,
        "average_abs_jerk_mps3": 0.0,
        "max_abs_jerk_mps3": 0.0,
        "safety_score": safety,
        "utility_penalty": utility,
        "total_score": total,
        "score": total,
    }


def _result(score: dict, events: list[dict] | None = None):
    events = events or []
    return {
        "failure_rate": 1.0 if events else 0.0,
        "run_count": 1,
        "failing_run_count": 1 if events else 0,
        "violation_counts": {"P5_COLLISION": 1} if events else {},
        "score": score,
        "events": events,
    }


def test_report_generation_outputs_required_v02_artifacts(tmp_path, baseline_config):
    event = {
        "property_id": "P5_COLLISION",
        "run_id": "baseline__scenario",
        "scenario_id": "scenario",
        "time_s": 0.3,
        "row_index": 3,
        "message": "Collision occurred.",
        "details": {"lead_distance_m": 0.0},
    }
    baseline_results = {
        "train": _result(_score(0, 0)),
        "holdout": _result(_score(1, 1000), [event]),
        "all": _result(_score(1, 1000), [event]),
    }
    split_results = {
        "train": _result(_score(0, 0, 5)),
        "holdout": _result(_score(0, 0, 7)),
        "all": _result(_score(0, 0, 12)),
    }
    candidate_results = [
        {
            "patch_id": "candidate",
            "description": "Test candidate.",
            "split_results": split_results,
            "score": split_results["train"]["score"],
            "violation_counts": {},
            "invariant_check": {"passed": True, "failures": [], "reachable_states": []},
            "improvement_pct": 100.0,
        }
    ]
    write_report(
        tmp_path,
        baseline_results,
        candidate_results,
        {
            "train": [],
            "holdout": [_row(index) for index in range(6)],
        },
        baseline_config,
    )

    assert (tmp_path / "index.md").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "before_after.csv").exists()
    assert (tmp_path / "pareto.csv").exists()
    assert (tmp_path / "best_patch.yaml").exists()
    assert any((tmp_path / "failure_examples").iterdir())
    assert any((tmp_path / "minimized_counterexamples").iterdir())
    assert any((tmp_path / "trace_plots").iterdir())
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["best_candidate"]["patch_id"] == "candidate"
    assert summary["top_minimized_counterexamples"][0]["window_start_time_s"] == 0.0
