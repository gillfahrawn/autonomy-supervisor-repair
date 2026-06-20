from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evaluation.metrics import score_events
from src.evaluation.report import write_report
from src.scenarios.scenario_schema import Scenario
from src.simulation.python_kinematic_sim import PythonKinematicSimulator
from src.supervisor.schemas import load_yaml
from src.traces.io import read_jsonl
from src.verification.model_check_stub import check_graph_invariants
from src.verification.runtime_monitor import RuntimeMonitor, summarize_events


def run_supervisor_on_scenarios(
    supervisor_config: dict[str, Any],
    scenarios: list[Scenario],
    run_label: str,
) -> list[dict]:
    simulator = PythonKinematicSimulator()
    rows: list[dict] = []
    for scenario in scenarios:
        run_id = f"{run_label}__{scenario.scenario_id}"
        rows.extend(simulator.run_scenario(scenario, supervisor_config, run_id=run_id))
    return rows


def evaluate_trace_rows(rows: list[dict], supervisor_config: dict[str, Any] | None = None) -> dict[str, Any]:
    monitor = RuntimeMonitor()
    events, annotated = monitor.evaluate(rows)
    grouped_runs = {row["run_id"] for row in annotated}
    failing_runs = {event.run_id for event in events}
    score = score_events(events)
    invariant = (
        check_graph_invariants(supervisor_config).to_dict()
        if supervisor_config is not None
        else None
    )
    return {
        "events": [event.to_dict() for event in events],
        "annotated_rows": annotated,
        "violation_counts": summarize_events(events),
        "score": score.to_dict(),
        "run_count": len(grouped_runs),
        "failing_run_count": len(failing_runs),
        "failure_rate": (len(failing_runs) / len(grouped_runs)) if grouped_runs else 0.0,
        "invariant_check": invariant,
    }


def evaluate_candidates(
    candidates_dir: str | Path,
    scenarios: list[Scenario],
    out_dir: str | Path,
) -> dict[str, Any]:
    candidates_path = Path(candidates_dir)
    manifest_path = candidates_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Candidate manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    baseline_trace_path = Path(manifest.get("baseline_traces") or "data/baseline_traces.jsonl")
    baseline_supervisor_path = Path(manifest.get("source_supervisor") or "configs/baseline_supervisor.yaml")
    baseline_rows = read_jsonl(baseline_trace_path)
    baseline_config = load_yaml(baseline_supervisor_path)
    baseline_result = evaluate_trace_rows(baseline_rows, baseline_config)
    baseline_score = baseline_result["score"]["score"]

    candidate_results: list[dict[str, Any]] = []
    best_config: dict[str, Any] | None = None
    best_score: int | None = None
    for candidate in manifest["candidates"]:
        path = candidates_path / candidate["path"]
        config = load_yaml(path)
        rows = run_supervisor_on_scenarios(config, scenarios, candidate["patch_id"])
        result = evaluate_trace_rows(rows, config)
        score = result["score"]["score"]
        improvement_pct = 0.0
        if baseline_score > 0:
            improvement_pct = round(100.0 * (baseline_score - score) / baseline_score, 2)
        candidate_result = {
            "patch_id": candidate["patch_id"],
            "description": candidate["description"],
            "mutation_type": candidate["mutation_type"],
            "path": str(path),
            "score": result["score"],
            "violation_counts": result["violation_counts"],
            "events": result["events"],
            "failure_rate": result["failure_rate"],
            "failing_run_count": result["failing_run_count"],
            "run_count": result["run_count"],
            "invariant_check": result["invariant_check"],
            "improvement_pct": improvement_pct,
        }
        candidate_results.append(candidate_result)
        if best_score is None or score < best_score:
            best_score = score
            best_config = config

    if best_config is None:
        best_config = baseline_config
    write_report(out_dir, baseline_result, candidate_results, baseline_result["annotated_rows"], best_config)
    return {
        "baseline": {
            key: value
            for key, value in baseline_result.items()
            if key != "annotated_rows"
        },
        "candidates": candidate_results,
    }

