from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from src.supervisor.schemas import dump_yaml
from src.traces.io import group_by_run, write_csv
from src.verification.stl_properties import PROPERTY_DESCRIPTIONS


def write_report(
    out_dir: str | Path,
    baseline_results: dict[str, dict[str, Any]],
    candidate_results: list[dict[str, Any]],
    baseline_rows_by_split: dict[str, list[dict]],
    best_patch_config: dict[str, Any],
) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for subdir in ("failure_examples", "minimized_counterexamples", "trace_plots"):
        path = out / subdir
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(exist_ok=True)

    ranked = _rank_candidates(candidate_results)
    pareto_rows = _pareto_rows(ranked)
    best = ranked[0] if ranked else None
    baseline_train = baseline_results["train"]
    baseline_holdout = baseline_results["holdout"]
    train_improvement_pct = _improvement_pct(
        baseline_train["score"]["total_score"],
        best["split_results"]["train"]["score"]["total_score"] if best else baseline_train["score"]["total_score"],
    )
    holdout_improvement_pct = _improvement_pct(
        baseline_holdout["score"]["total_score"],
        best["split_results"]["holdout"]["score"]["total_score"] if best else baseline_holdout["score"]["total_score"],
    )

    dump_yaml(best_patch_config, out / "best_patch.yaml")
    _write_before_after(out / "before_after.csv", baseline_results, ranked)
    _write_pareto_csv(out / "pareto.csv", pareto_rows)
    top_failures = _write_minimized_counterexamples(out, baseline_results, baseline_rows_by_split)

    summary = {
        "baseline": {
            "train": _summary_result(baseline_train),
            "holdout": _summary_result(baseline_holdout),
            "all": _summary_result(baseline_results["all"]),
        },
        "best_candidate": (
            {
                "patch_id": best["patch_id"],
                "description": best["description"],
                "train": _summary_result(best["split_results"]["train"]),
                "holdout": _summary_result(best["split_results"]["holdout"]),
                "train_improvement_pct": train_improvement_pct,
                "holdout_improvement_pct": holdout_improvement_pct,
                "invariant_check": best["invariant_check"],
            }
            if best
            else None
        ),
        "candidate_rankings": [
            {
                "rank": index + 1,
                "patch_id": candidate["patch_id"],
                "train_safety_score": candidate["split_results"]["train"]["score"]["safety_score"],
                "train_utility_penalty": candidate["split_results"]["train"]["score"]["utility_penalty"],
                "train_total_score": candidate["split_results"]["train"]["score"]["total_score"],
                "holdout_safety_score": candidate["split_results"]["holdout"]["score"]["safety_score"],
                "holdout_utility_penalty": candidate["split_results"]["holdout"]["score"]["utility_penalty"],
                "holdout_total_score": candidate["split_results"]["holdout"]["score"]["total_score"],
                "improvement_pct": candidate["improvement_pct"],
                "violation_counts": candidate["violation_counts"],
                "invariant_passed": candidate["invariant_check"]["passed"],
            }
            for index, candidate in enumerate(ranked)
        ],
        "pareto_table": pareto_rows,
        "top_minimized_counterexamples": top_failures,
    }
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    _write_index(
        out / "index.md",
        baseline_results=baseline_results,
        ranked=ranked,
        pareto_rows=pareto_rows,
        best=best,
        train_improvement_pct=train_improvement_pct,
        holdout_improvement_pct=holdout_improvement_pct,
        top_failures=top_failures,
    )


def _rank_candidates(candidate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        candidate_results,
        key=lambda item: (
            item["split_results"]["train"]["score"]["total_score"],
            item["split_results"]["holdout"]["score"]["total_score"],
            item["patch_id"],
        ),
    )


def _summary_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_count": result["run_count"],
        "failing_run_count": result["failing_run_count"],
        "failure_rate": result["failure_rate"],
        "violation_counts": result["violation_counts"],
        "score": result["score"],
    }


def _improvement_pct(baseline_score: int, candidate_score: int) -> float:
    if baseline_score <= 0:
        return 0.0
    return round(100.0 * (baseline_score - candidate_score) / baseline_score, 2)


def _write_before_after(
    path: Path,
    baseline_results: dict[str, dict[str, Any]],
    ranked: list[dict[str, Any]],
) -> None:
    fieldnames = [
        "rank",
        "patch_id",
        "train_safety_score",
        "train_utility_penalty",
        "train_total_score",
        "holdout_safety_score",
        "holdout_utility_penalty",
        "holdout_total_score",
        "train_improvement_pct",
        "holdout_improvement_pct",
        "train_collisions",
        "holdout_collisions",
        "train_unnecessary_mrm_activations",
        "holdout_unnecessary_mrm_activations",
        "train_false_takeover_requests",
        "holdout_false_takeover_requests",
        "train_average_speed_loss_mps",
        "holdout_average_speed_loss_mps",
        "train_mission_completion_rate",
        "holdout_mission_completion_rate",
    ]
    baseline_train_total = baseline_results["train"]["score"]["total_score"]
    baseline_holdout_total = baseline_results["holdout"]["score"]["total_score"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, candidate in enumerate(ranked, start=1):
            train_score = candidate["split_results"]["train"]["score"]
            holdout_score = candidate["split_results"]["holdout"]["score"]
            writer.writerow(
                {
                    "rank": index,
                    "patch_id": candidate["patch_id"],
                    "train_safety_score": train_score["safety_score"],
                    "train_utility_penalty": train_score["utility_penalty"],
                    "train_total_score": train_score["total_score"],
                    "holdout_safety_score": holdout_score["safety_score"],
                    "holdout_utility_penalty": holdout_score["utility_penalty"],
                    "holdout_total_score": holdout_score["total_score"],
                    "train_improvement_pct": _improvement_pct(baseline_train_total, train_score["total_score"]),
                    "holdout_improvement_pct": _improvement_pct(baseline_holdout_total, holdout_score["total_score"]),
                    "train_collisions": train_score["collisions"],
                    "holdout_collisions": holdout_score["collisions"],
                    "train_unnecessary_mrm_activations": train_score["unnecessary_mrm_activations"],
                    "holdout_unnecessary_mrm_activations": holdout_score["unnecessary_mrm_activations"],
                    "train_false_takeover_requests": train_score["false_takeover_requests"],
                    "holdout_false_takeover_requests": holdout_score["false_takeover_requests"],
                    "train_average_speed_loss_mps": train_score["average_speed_loss_mps"],
                    "holdout_average_speed_loss_mps": holdout_score["average_speed_loss_mps"],
                    "train_mission_completion_rate": train_score["mission_completion_rate"],
                    "holdout_mission_completion_rate": holdout_score["mission_completion_rate"],
                }
            )


def _pareto_rows(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in ranked:
        train = candidate["split_results"]["train"]["score"]
        dominated_by: list[str] = []
        for other in ranked:
            if other["patch_id"] == candidate["patch_id"]:
                continue
            other_train = other["split_results"]["train"]["score"]
            safety_no_worse = other_train["safety_score"] <= train["safety_score"]
            utility_no_worse = other_train["utility_penalty"] <= train["utility_penalty"]
            strictly_better = (
                other_train["safety_score"] < train["safety_score"]
                or other_train["utility_penalty"] < train["utility_penalty"]
            )
            if safety_no_worse and utility_no_worse and strictly_better:
                dominated_by.append(other["patch_id"])
        rows.append(
            {
                "patch_id": candidate["patch_id"],
                "train_safety_score": train["safety_score"],
                "train_utility_penalty": train["utility_penalty"],
                "train_total_score": train["total_score"],
                "holdout_safety_score": candidate["split_results"]["holdout"]["score"]["safety_score"],
                "holdout_utility_penalty": candidate["split_results"]["holdout"]["score"]["utility_penalty"],
                "holdout_total_score": candidate["split_results"]["holdout"]["score"]["total_score"],
                "pareto_front": not dominated_by,
                "dominated_by": dominated_by[:3],
            }
        )
    rows.sort(
        key=lambda row: (
            not row["pareto_front"],
            row["train_safety_score"],
            row["train_utility_penalty"],
            row["patch_id"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["pareto_rank"] = index
    return rows


def _write_pareto_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "pareto_rank",
        "patch_id",
        "train_safety_score",
        "train_utility_penalty",
        "train_total_score",
        "holdout_safety_score",
        "holdout_utility_penalty",
        "holdout_total_score",
        "pareto_front",
        "dominated_by",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            serialized["dominated_by"] = "|".join(serialized["dominated_by"])
            writer.writerow(serialized)


def _write_minimized_counterexamples(
    out: Path,
    baseline_results: dict[str, dict[str, Any]],
    baseline_rows_by_split: dict[str, list[dict]],
) -> list[dict[str, Any]]:
    source_split = "holdout" if baseline_results["holdout"]["events"] else "train"
    events = sorted(
        baseline_results[source_split]["events"],
        key=lambda event: (_severity(event["property_id"]), event["time_s"]),
    )[:5]
    grouped = group_by_run(baseline_rows_by_split[source_split])
    examples: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        run_rows = grouped.get(event["run_id"], [])
        window = minimize_counterexample_window(run_rows, event)
        stem = f"{index}_{event['run_id']}"
        csv_name = f"minimized_counterexamples/{stem}.csv"
        json_name = f"minimized_counterexamples/{stem}.json"
        legacy_csv_name = f"failure_examples/{stem}.csv"
        svg_name = f"trace_plots/{stem}.svg"
        write_csv(window, out / csv_name)
        write_csv(window, out / legacy_csv_name)
        with (out / json_name).open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "event": event,
                    "split": source_split,
                    "window_start_time_s": window[0]["time_s"] if window else None,
                    "window_end_time_s": window[-1]["time_s"] if window else None,
                    "rows": window,
                },
                handle,
                indent=2,
            )
        _write_svg_plot(window, out / svg_name, title=event["run_id"])
        examples.append(
            {
                "property_id": event["property_id"],
                "split": source_split,
                "run_id": event["run_id"],
                "scenario_id": event["scenario_id"],
                "time_s": event["time_s"],
                "row_index": event["row_index"],
                "window_start_time_s": window[0]["time_s"] if window else None,
                "window_end_time_s": window[-1]["time_s"] if window else None,
                "csv": csv_name,
                "json": json_name,
                "plot": svg_name,
            }
        )
    return examples


def minimize_counterexample_window(
    run_rows: list[dict],
    event: dict[str, Any],
    pre_s: float = 0.5,
    post_s: float = 0.5,
) -> list[dict]:
    if not run_rows:
        return []
    event_time = float(event["time_s"])
    start_time = event_time - pre_s
    end_time = event_time + post_s
    window = [
        row for row in run_rows
        if start_time <= float(row["time_s"]) <= end_time
    ]
    if window:
        return window
    row_index = max(0, min(int(event["row_index"]), len(run_rows) - 1))
    return [run_rows[row_index]]


def _write_svg_plot(rows: list[dict], path: Path, title: str) -> None:
    width = 760
    height = 260
    margin = 36
    if not rows:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>\n", encoding="utf-8")
        return
    min_time = min(row["time_s"] for row in rows)
    max_time = max(row["time_s"] for row in rows)
    time_span = max(1.0e-6, max_time - min_time)
    bounded_ttc_values = [row["ttc_s"] for row in rows if row["ttc_s"] < 999.0] or [5.0]
    max_ttc = max(5.0, min(20.0, max(bounded_ttc_values)))
    max_speed = max(1.0, max(row["ego_speed_mps"] for row in rows))

    def xy(row: dict, key: str, max_y: float) -> tuple[float, float]:
        x = margin + ((row["time_s"] - min_time) / time_span) * (width - 2 * margin)
        y = height - margin - (min(float(row[key]), max_y) / max_y) * (height - 2 * margin)
        return x, y

    def polyline(key: str, max_y: float, color: str) -> str:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(row, key, max_y) for row in rows))
        return f"<polyline fill='none' stroke='{color}' stroke-width='2' points='{points}' />"

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white' />",
        f"<text x='{margin}' y='22' font-family='Arial' font-size='14'>{_escape(title)}</text>",
        f"<line x1='{margin}' y1='{height - margin}' x2='{width - margin}' y2='{height - margin}' stroke='#444' />",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height - margin}' stroke='#444' />",
        polyline("ttc_s", max_ttc, "#1f77b4"),
        polyline("ego_speed_mps", max_speed, "#d62728"),
        f"<text x='{width - 210}' y='22' font-family='Arial' font-size='12' fill='#1f77b4'>TTC</text>",
        f"<text x='{width - 160}' y='22' font-family='Arial' font-size='12' fill='#d62728'>ego speed</text>",
        "</svg>",
    ]
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def _write_index(
    path: Path,
    baseline_results: dict[str, dict[str, Any]],
    ranked: list[dict[str, Any]],
    pareto_rows: list[dict[str, Any]],
    best: dict[str, Any] | None,
    train_improvement_pct: float,
    holdout_improvement_pct: float,
    top_failures: list[dict[str, Any]],
) -> None:
    baseline_train = baseline_results["train"]
    baseline_holdout = baseline_results["holdout"]
    lines = [
        "# Counterexample-Guided Supervisor Repair Report",
        "",
        "## Baseline Train/Holdout",
        "",
        "| Split | Runs | Failing Runs | Failure Rate | Safety Score | Utility Penalty | Total Score |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        _score_row("train", baseline_train),
        _score_row("holdout", baseline_holdout),
        "",
        "## Candidate Rankings",
        "",
        "| Rank | Patch | Train Total | Holdout Total | Train Safety | Train Utility | Holdout Safety | Holdout Utility |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for index, candidate in enumerate(ranked, start=1):
        train = candidate["split_results"]["train"]["score"]
        holdout = candidate["split_results"]["holdout"]["score"]
        lines.append(
            f"| {index} | `{candidate['patch_id']}` | {train['total_score']} | {holdout['total_score']} | "
            f"{train['safety_score']} | {train['utility_penalty']} | "
            f"{holdout['safety_score']} | {holdout['utility_penalty']} |"
        )

    lines.extend(["", "## Pareto Table", ""])
    lines.extend(
        [
            "| Pareto Rank | Patch | Front | Train Safety | Train Utility | Holdout Safety | Holdout Utility |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in pareto_rows:
        front = "yes" if row["pareto_front"] else "no"
        lines.append(
            f"| {row['pareto_rank']} | `{row['patch_id']}` | {front} | "
            f"{row['train_safety_score']} | {row['train_utility_penalty']} | "
            f"{row['holdout_safety_score']} | {row['holdout_utility_penalty']} |"
        )

    if best:
        train = best["split_results"]["train"]["score"]
        holdout = best["split_results"]["holdout"]["score"]
        lines.extend(
            [
                "",
                "## Best Patch",
                "",
                f"- Patch: `{best['patch_id']}`",
                f"- Explanation: {best['description']}",
                f"- Train improvement: {train_improvement_pct:.2f}%",
                f"- Holdout improvement: {holdout_improvement_pct:.2f}%",
                f"- Train safety/utility/total: {train['safety_score']} / {train['utility_penalty']} / {train['total_score']}",
                f"- Holdout safety/utility/total: {holdout['safety_score']} / {holdout['utility_penalty']} / {holdout['total_score']}",
                f"- Invariant check passed: {best['invariant_check']['passed']}",
            ]
        )
        if best["invariant_check"]["failures"]:
            lines.append(f"- Invariant failures: {best['invariant_check']['failures']}")

    lines.extend(
        [
            "",
            "## Safety Vs Utility Breakdown",
            "",
            "- Safety score uses collision, critical TTC, sensor degradation, oscillation, and fake-safety property violations.",
            "- Utility penalty uses unnecessary emergency braking, unnecessary MRM activation, false takeover requests, average speed loss, mission completion, and average jerk proxy.",
            "- See `before_after.csv` and `pareto.csv` for complete candidate-level metrics.",
            "",
            "## Top 5 Minimized Counterexamples",
            "",
        ]
    )
    for failure in top_failures:
        lines.append(
            f"- `{failure['property_id']}` on `{failure['split']}` in `{failure['run_id']}` at "
            f"t={failure['time_s']}s, minimized to {failure['window_start_time_s']}s-"
            f"{failure['window_end_time_s']}s: [{failure['csv']}]({failure['csv']}), "
            f"[plot]({failure['plot']})"
        )

    lines.extend(["", "## Runtime Properties", ""])
    for property_id, description in PROPERTY_DESCRIPTIONS.items():
        lines.append(f"- `{property_id}`: {description}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The MVP remains a deterministic 1D Python kinematic simulator, not CARLA.",
            "- CARLA, RTAMT, and nuXmv remain optional future adapter/export paths, not required dependencies.",
            "- Utility metrics are proxy measures intended for repair ranking, not validated vehicle comfort or mission KPIs.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _score_row(split: str, result: dict[str, Any]) -> str:
    score = result["score"]
    return (
        f"| {split} | {result['run_count']} | {result['failing_run_count']} | "
        f"{result['failure_rate']:.2%} | {score['safety_score']} | "
        f"{score['utility_penalty']} | {score['total_score']} |"
    )


def _severity(property_id: str) -> int:
    order = {
        "P5_COLLISION": 0,
        "P1_CRITICAL_TTC_RESPONSE": 1,
        "P2_SENSOR_DEGRADATION": 2,
        "P3_NO_OSCILLATION": 3,
        "P4_FAKE_SAFETY": 4,
    }
    return order.get(property_id, 99)


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
