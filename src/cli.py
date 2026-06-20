from __future__ import annotations

import argparse

from src.evaluation.runner import evaluate_candidates, run_supervisor_on_scenarios
from src.scenarios.generator import (
    generate_scenarios_from_yaml,
    read_scenarios_jsonl,
    write_scenarios_jsonl,
)
from src.supervisor.patcher import write_candidate_patches
from src.supervisor.schemas import load_yaml
from src.traces.io import write_trace_pair, read_jsonl
from src.verification.runtime_monitor import write_verification_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Counterexample-guided ADAS supervisor repair MVP"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate-scenarios")
    generate.add_argument("--config", required=True)
    generate.add_argument("--out", required=True)
    generate.set_defaults(func=_generate_scenarios)

    run = subparsers.add_parser("run-baseline")
    run.add_argument("--supervisor", required=True)
    run.add_argument("--scenarios", required=True)
    run.add_argument("--out", required=True)
    run.set_defaults(func=_run_baseline)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--traces", required=True)
    verify.add_argument("--out", required=True)
    verify.set_defaults(func=_verify)

    repair = subparsers.add_parser("repair")
    repair.add_argument("--supervisor", required=True)
    repair.add_argument("--traces", required=True)
    repair.add_argument("--out", required=True)
    repair.set_defaults(func=_repair)

    evaluate = subparsers.add_parser("evaluate-candidates")
    evaluate.add_argument("--candidates", required=True)
    evaluate.add_argument("--scenarios", required=True)
    evaluate.add_argument("--out", required=True)
    evaluate.set_defaults(func=_evaluate_candidates)

    args = parser.parse_args()
    args.func(args)


def _generate_scenarios(args: argparse.Namespace) -> None:
    scenarios = generate_scenarios_from_yaml(args.config)
    write_scenarios_jsonl(scenarios, args.out)
    print(f"generated_scenarios={len(scenarios)} out={args.out}")


def _run_baseline(args: argparse.Namespace) -> None:
    supervisor = load_yaml(args.supervisor)
    scenarios = read_scenarios_jsonl(args.scenarios)
    rows = run_supervisor_on_scenarios(supervisor, scenarios, "baseline")
    write_trace_pair(rows, args.out)
    print(f"trace_rows={len(rows)} runs={len(scenarios)} out={args.out}")


def _verify(args: argparse.Namespace) -> None:
    rows = read_jsonl(args.traces)
    summary = write_verification_artifacts(rows, args.out)
    print(
        f"violations={summary['total_violations']} "
        f"counts={summary['violation_counts']} out={args.out}"
    )


def _repair(args: argparse.Namespace) -> None:
    candidates = write_candidate_patches(args.supervisor, args.out, args.traces)
    print(f"candidate_patches={len(candidates)} out={args.out}")


def _evaluate_candidates(args: argparse.Namespace) -> None:
    scenarios = read_scenarios_jsonl(args.scenarios)
    result = evaluate_candidates(args.candidates, scenarios, args.out)
    best = sorted(result["candidates"], key=lambda item: item["score"]["score"])[0]
    print(
        f"baseline_score={result['baseline']['score']['score']} "
        f"best_patch={best['patch_id']} best_score={best['score']['score']} "
        f"improvement_pct={best['improvement_pct']} out={args.out}"
    )


if __name__ == "__main__":
    main()
