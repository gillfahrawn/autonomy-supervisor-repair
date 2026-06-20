from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.supervisor.schemas import dump_yaml
from src.traces.io import group_by_run, write_csv
from src.verification.stl_properties import PROPERTY_DESCRIPTIONS


def write_report(
    out_dir: str | Path,
    baseline_result: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    baseline_rows: list[dict],
    best_patch_config: dict[str, Any],
) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "failure_examples").mkdir(exist_ok=True)
    (out / "trace_plots").mkdir(exist_ok=True)

    ranked = sorted(candidate_results, key=lambda item: item["score"]["score"])
    best = ranked[0] if ranked else None
    baseline_score = baseline_result["score"]["score"]
    best_score = best["score"]["score"] if best else baseline_score
    improvement_pct = 0.0
    if baseline_score > 0:
        improvement_pct = round(100.0 * (baseline_score - best_score) / baseline_score, 2)

    dump_yaml(best_patch_config, out / "best_patch.yaml")
    _write_before_after(out / "before_after.csv", baseline_result, ranked)
    top_failures = _write_failure_examples(out, baseline_result, baseline_rows)

    summary = {
        "baseline_failure_rate": baseline_result["failure_rate"],
        "baseline_score": baseline_score,
        "best_patch_id": best["patch_id"] if best else None,
        "best_score": best_score,
        "best_improvement_pct": improvement_pct,
        "candidate_rankings": [
            {
                "rank": index + 1,
                "patch_id": candidate["patch_id"],
                "score": candidate["score"]["score"],
                "improvement_pct": candidate["improvement_pct"],
                "violation_counts": candidate["violation_counts"],
                "invariant_passed": candidate["invariant_check"]["passed"],
            }
            for index, candidate in enumerate(ranked)
        ],
        "baseline_violation_counts": baseline_result["violation_counts"],
        "invariant_check_result": best["invariant_check"] if best else None,
        "top_counterexamples": top_failures,
    }
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    _write_index(
        out / "index.md",
        baseline_result=baseline_result,
        ranked=ranked,
        best=best,
        improvement_pct=improvement_pct,
        top_failures=top_failures,
    )


def _write_before_after(path: Path, baseline_result: dict[str, Any], ranked: list[dict[str, Any]]) -> None:
    fieldnames = [
        "rank",
        "patch_id",
        "baseline_score",
        "candidate_score",
        "improvement_pct",
        "baseline_collisions",
        "candidate_collisions",
        "baseline_critical_ttc_violations",
        "candidate_critical_ttc_violations",
        "baseline_takeover_latency_violations",
        "candidate_takeover_latency_violations",
        "baseline_oscillation_violations",
        "candidate_oscillation_violations",
        "baseline_unnecessary_emergency_brakes",
        "candidate_unnecessary_emergency_brakes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, candidate in enumerate(ranked):
            row = {
                "rank": index + 1,
                "patch_id": candidate["patch_id"],
                "baseline_score": baseline_result["score"]["score"],
                "candidate_score": candidate["score"]["score"],
                "improvement_pct": candidate["improvement_pct"],
            }
            for key in (
                "collisions",
                "critical_ttc_violations",
                "takeover_latency_violations",
                "oscillation_violations",
                "unnecessary_emergency_brakes",
            ):
                row[f"baseline_{key}"] = baseline_result["score"][key]
                row[f"candidate_{key}"] = candidate["score"][key]
            writer.writerow(row)


def _write_failure_examples(
    out: Path,
    baseline_result: dict[str, Any],
    baseline_rows: list[dict],
) -> list[dict[str, Any]]:
    grouped = group_by_run(baseline_rows)
    top_events = sorted(
        baseline_result["events"],
        key=lambda event: (_severity(event["property_id"]), event["time_s"]),
    )[:5]
    examples: list[dict[str, Any]] = []
    for index, event in enumerate(top_events, start=1):
        run_rows = grouped.get(event["run_id"], [])
        stem = f"{index}_{event['run_id']}"
        csv_name = f"failure_examples/{stem}.csv"
        json_name = f"failure_examples/{stem}.json"
        svg_name = f"trace_plots/{stem}.svg"
        write_csv(run_rows, out / csv_name)
        with (out / json_name).open("w", encoding="utf-8") as handle:
            json.dump({"event": event, "rows": run_rows}, handle, indent=2)
        _write_svg_plot(run_rows, out / svg_name, title=event["run_id"])
        examples.append(
            {
                "property_id": event["property_id"],
                "run_id": event["run_id"],
                "scenario_id": event["scenario_id"],
                "time_s": event["time_s"],
                "row_index": event["row_index"],
                "csv": csv_name,
                "json": json_name,
                "plot": svg_name,
            }
        )
    return examples


def _write_svg_plot(rows: list[dict], path: Path, title: str) -> None:
    width = 760
    height = 260
    margin = 36
    if not rows:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>\n", encoding="utf-8")
        return
    max_time = max(row["time_s"] for row in rows) or 1.0
    bounded_ttc_values = [row["ttc_s"] for row in rows if row["ttc_s"] < 999.0] or [5.0]
    max_ttc = max(5.0, min(20.0, max(bounded_ttc_values)))
    max_speed = max(1.0, max(row["ego_speed_mps"] for row in rows))

    def xy(row: dict, key: str, max_y: float) -> tuple[float, float]:
        x = margin + (row["time_s"] / max_time) * (width - 2 * margin)
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
    baseline_result: dict[str, Any],
    ranked: list[dict[str, Any]],
    best: dict[str, Any] | None,
    improvement_pct: float,
    top_failures: list[dict[str, Any]],
) -> None:
    lines = [
        "# Counterexample-Guided Supervisor Repair Report",
        "",
        "## Baseline",
        "",
        f"- Scenario runs: {baseline_result['run_count']}",
        f"- Failing runs: {baseline_result['failing_run_count']}",
        f"- Failure rate: {baseline_result['failure_rate']:.2%}",
        f"- Score: {baseline_result['score']['score']}",
        f"- Violations: {baseline_result['violation_counts']}",
        "",
        "## Candidate Patch Rankings",
        "",
        "| Rank | Patch | Score | Improvement | Invariants |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for index, candidate in enumerate(ranked, start=1):
        invariant_status = "pass" if candidate["invariant_check"]["passed"] else "fail"
        lines.append(
            f"| {index} | `{candidate['patch_id']}` | {candidate['score']['score']} | "
            f"{candidate['improvement_pct']:.2f}% | {invariant_status} |"
        )

    if best:
        lines.extend(
            [
                "",
                "## Best Patch",
                "",
                f"- Patch: `{best['patch_id']}`",
                f"- Score improvement: {improvement_pct:.2f}%",
                f"- Diff summary: {best['description']}",
                f"- Invariant check passed: {best['invariant_check']['passed']}",
            ]
        )
        if best["invariant_check"]["failures"]:
            lines.append(f"- Invariant failures: {best['invariant_check']['failures']}")

    lines.extend(
        [
            "",
            "## Before/After Violation Counts",
            "",
            "See `before_after.csv` for the full ranking table.",
            "",
            "## Top Counterexample Traces",
            "",
        ]
    )
    for failure in top_failures:
        lines.append(
            f"- `{failure['property_id']}` in `{failure['run_id']}` at t={failure['time_s']}s "
            f"(row {failure['row_index']}): [{failure['csv']}]({failure['csv']}), "
            f"[plot]({failure['plot']})"
        )

    lines.extend(
        [
            "",
            "## Runtime Properties",
            "",
        ]
    )
    for property_id, description in PROPERTY_DESCRIPTIONS.items():
        lines.append(f"- `{property_id}`: {description}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The MVP uses a deterministic 1D Python kinematic simulator, not CARLA.",
            "- Perception, controls, HIL traces, RTAMT, and external nuXmv execution are future adapter paths.",
            "- Patch generation is bounded to explicit threshold, hysteresis, guard, state-splitting, and recovery mutations.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
