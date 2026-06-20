from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evaluation.metrics import score_events
from src.evaluation.report import write_report
from src.evaluation.selection import rank_candidates_for_selection
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
    score = score_events(events, annotated)
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
    baseline_rows_by_split = split_trace_rows(baseline_rows, scenarios)
    baseline_results = {
        split: evaluate_trace_rows(rows, baseline_config)
        for split, rows in baseline_rows_by_split.items()
    }
    baseline_results["all"] = evaluate_trace_rows(baseline_rows, baseline_config)
    baseline_train_score = baseline_results["train"]["score"]["total_score"]

    candidate_results: list[dict[str, Any]] = []
    best_config: dict[str, Any] | None = None
    for candidate in manifest["candidates"]:
        path = candidates_path / candidate["path"]
        config = load_yaml(path)
        rows = run_supervisor_on_scenarios(config, scenarios, candidate["patch_id"])
        rows_by_split = split_trace_rows(rows, scenarios)
        split_results = {
            split: _without_annotated_rows(evaluate_trace_rows(split_rows, config))
            for split, split_rows in rows_by_split.items()
        }
        split_results["all"] = _without_annotated_rows(evaluate_trace_rows(rows, config))
        train_score = split_results["train"]["score"]["total_score"]
        improvement_pct = 0.0
        if baseline_train_score > 0:
            improvement_pct = round(100.0 * (baseline_train_score - train_score) / baseline_train_score, 2)

        candidate_result = {
            "patch_id": candidate["patch_id"],
            "description": candidate["description"],
            "mutation_type": candidate["mutation_type"],
            "path": str(path),
            "split_results": split_results,
            "score": split_results["train"]["score"],
            "violation_counts": split_results["train"]["violation_counts"],
            "events": split_results["train"]["events"],
            "failure_rate": split_results["train"]["failure_rate"],
            "failing_run_count": split_results["train"]["failing_run_count"],
            "run_count": split_results["train"]["run_count"],
            "invariant_check": split_results["train"]["invariant_check"],
            "improvement_pct": improvement_pct,
        }
        candidate_results.append(candidate_result)

    if candidate_results:
        selected = rank_candidates_for_selection(candidate_results)[0]
        best_config = load_yaml(selected["path"])

    if best_config is None:
        best_config = baseline_config
    baseline_annotated_rows_by_split = {
        split: result["annotated_rows"]
        for split, result in baseline_results.items()
        if split in {"train", "holdout"}
    }
    write_report(out_dir, baseline_results, candidate_results, baseline_annotated_rows_by_split, best_config)
    return {
        "baseline": {
            split: _without_annotated_rows(result)
            for split, result in baseline_results.items()
        },
        "candidates": candidate_results,
    }


def split_scenarios(scenarios: list[Scenario]) -> dict[str, list[Scenario]]:
    splits: dict[str, list[Scenario]] = {"train": [], "holdout": []}
    for scenario in scenarios:
        splits.setdefault(scenario.split, []).append(scenario)
    return splits


def split_trace_rows(rows: list[dict], scenarios: list[Scenario]) -> dict[str, list[dict]]:
    split_by_scenario = {scenario.scenario_id: scenario.split for scenario in scenarios}
    splits: dict[str, list[dict]] = {"train": [], "holdout": []}
    for row in rows:
        split = split_by_scenario.get(row["scenario_id"], "train")
        splits.setdefault(split, []).append(row)
    return splits


def _without_annotated_rows(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key != "annotated_rows"
    }
