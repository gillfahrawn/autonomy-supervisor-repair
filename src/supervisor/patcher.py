from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.supervisor.schemas import dump_yaml, load_yaml


@dataclass(frozen=True)
class CandidatePatch:
    patch_id: str
    description: str
    mutation_type: str
    config: dict[str, Any]


def _with_metadata(base: dict[str, Any], patch_id: str, description: str, mutation_type: str) -> dict[str, Any]:
    mutated = copy.deepcopy(base)
    metadata = dict(mutated.get("metadata") or {})
    metadata.update(
        {
            "patch_id": patch_id,
            "description": description,
            "mutation_type": mutation_type,
        }
    )
    mutated["metadata"] = metadata
    return mutated


def _set_transition_condition(config: dict[str, Any], name: str, condition: str) -> None:
    for transition in config.get("transitions", []):
        if transition.get("name") == name:
            transition["when"] = condition
            return
    raise ValueError(f"Transition {name!r} not found")


def _remove_transition(config: dict[str, Any], source: str, target: str) -> None:
    config["transitions"] = [
        t for t in config.get("transitions", [])
        if not (t.get("from") == source and t.get("to") == target)
    ]


def _append_transition(config: dict[str, Any], name: str, source: str, target: str, condition: str) -> None:
    if any(t.get("name") == name for t in config.get("transitions", [])):
        return
    config.setdefault("transitions", []).append(
        {
            "name": name,
            "from": source,
            "to": target,
            "when": condition,
        }
    )


def _add_hysteresis(config: dict[str, Any], low: float = 0.40, high: float = 0.55, hold_s: float = 0.8) -> None:
    _append_transition(
        config,
        "following_to_degraded_hysteresis_enter",
        "FOLLOWING",
        "DEGRADED_PERCEPTION",
        f"sensor_confidence < {low:.2f}",
    )
    _append_transition(
        config,
        "degraded_to_following_hysteresis_exit",
        "DEGRADED_PERCEPTION",
        "FOLLOWING",
        f"sensor_confidence > {high:.2f} and duration_s > {hold_s:.2f}",
    )
    _set_transition_condition(
        config,
        "degraded_to_takeover",
        f"sensor_confidence < {low:.2f} and duration_s > 1.00",
    )


def _add_recovery_constraints(config: dict[str, Any], takeover_ttc_threshold: float = 1.50) -> None:
    _remove_transition(config, "EMERGENCY_BRAKE", "CRUISE")
    _append_transition(
        config,
        "mrm_to_safe_stop",
        "MIN_RISK_MANEUVER",
        "SAFE_STOP",
        "ego_speed_mps < 0.20",
    )
    _append_transition(
        config,
        "emergency_to_safe_stop",
        "EMERGENCY_BRAKE",
        "SAFE_STOP",
        "ego_speed_mps < 0.20",
    )
    _append_transition(
        config,
        "takeover_to_mrm_if_ttc_critical",
        "TAKEOVER_REQUESTED",
        "MIN_RISK_MANEUVER",
        f"ttc_s < {takeover_ttc_threshold:.2f}",
    )


def _split_following(config: dict[str, Any]) -> None:
    states = list(config["states"])
    states = ["FOLLOWING_STABLE" if state == "FOLLOWING" else state for state in states]
    if "FOLLOWING_UNCERTAIN" not in states:
        insert_at = states.index("FOLLOWING_STABLE") + 1
        states.insert(insert_at, "FOLLOWING_UNCERTAIN")
    config["states"] = states

    actions = config["actions"]
    actions["FOLLOWING_STABLE"] = copy.deepcopy(actions.pop("FOLLOWING"))
    actions["FOLLOWING_UNCERTAIN"] = {
        "brake_cmd": 0.3,
        "target_accel_mps2": -0.8,
    }

    for transition in config["transitions"]:
        if transition.get("from") == "FOLLOWING":
            transition["from"] = "FOLLOWING_UNCERTAIN"
        if transition.get("to") == "FOLLOWING":
            transition["to"] = "FOLLOWING_STABLE"
        if transition.get("name") == "cruise_to_following":
            transition["name"] = "cruise_to_following_stable"
            transition["to"] = "FOLLOWING_STABLE"

    _append_transition(
        config,
        "following_stable_to_uncertain",
        "FOLLOWING_STABLE",
        "FOLLOWING_UNCERTAIN",
        "lead_distance_m < 30 or sensor_confidence < 0.50",
    )
    _append_transition(
        config,
        "following_uncertain_to_stable",
        "FOLLOWING_UNCERTAIN",
        "FOLLOWING_STABLE",
        "lead_distance_m >= 30 and sensor_confidence > 0.65 and duration_s > 1.00",
    )


def generate_candidate_patches(supervisor: dict[str, Any]) -> list[CandidatePatch]:
    candidates: list[CandidatePatch] = []

    def add(patch_id: str, description: str, mutation_type: str, config: dict[str, Any]) -> None:
        candidates.append(
            CandidatePatch(
                patch_id=patch_id,
                description=description,
                mutation_type=mutation_type,
                config=config,
            )
        )

    for threshold in (1.50, 1.80, 2.10, 2.50):
        cfg = _with_metadata(
            supervisor,
            f"candidate_ttc_{str(threshold).replace('.', '_')}",
            f"Raise FOLLOWING->MIN_RISK_MANEUVER TTC threshold to {threshold:.2f}s.",
            "threshold_adjustment",
        )
        _set_transition_condition(cfg, "following_to_mrm", f"ttc_s < {threshold:.2f}")
        add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "threshold_adjustment", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_sensor_0_40",
        "Raise FOLLOWING->TAKEOVER_REQUESTED sensor-confidence threshold to 0.40.",
        "threshold_adjustment",
    )
    _set_transition_condition(cfg, "following_to_takeover", "sensor_confidence < 0.40")
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "threshold_adjustment", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_combined_ttc_sensor",
        "Raise TTC response to 2.50s and request takeover below 0.40 confidence.",
        "threshold_adjustment",
    )
    _set_transition_condition(cfg, "following_to_mrm", "ttc_s < 2.50")
    _set_transition_condition(cfg, "following_to_takeover", "sensor_confidence < 0.40")
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "threshold_adjustment", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_degraded_hysteresis",
        "Add degraded-perception hysteresis to avoid noisy FOLLOWING/DEGRADED oscillation.",
        "hysteresis",
    )
    _add_hysteresis(cfg)
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "hysteresis", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_guarded_mrm",
        "Raise TTC response to 1.80s but require the ego vehicle to be closing.",
        "transition_guard_addition",
    )
    _set_transition_condition(cfg, "following_to_mrm", "ttc_s < 1.80 and relative_velocity_mps > 0.10")
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "transition_guard_addition", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_recovery_constraints",
        "Add explicit paths from minimum-risk and emergency states to SAFE_STOP.",
        "recovery_constraint",
    )
    _add_recovery_constraints(cfg, takeover_ttc_threshold=2.50)
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "recovery_constraint", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_following_split",
        "Split FOLLOWING into stable and uncertain substates with earlier uncertain handling.",
        "state_splitting",
    )
    _split_following(cfg)
    _set_transition_condition(cfg, "following_to_mrm", "ttc_s < 1.80")
    _set_transition_condition(cfg, "following_to_takeover", "sensor_confidence < 0.40")
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "state_splitting", cfg)

    cfg = _with_metadata(
        supervisor,
        "candidate_full_mvp_repair",
        "Combine 2.50s TTC response, sensor takeover threshold, degraded hysteresis, and safe-stop recovery.",
        "combined",
    )
    _set_transition_condition(cfg, "following_to_mrm", "ttc_s < 2.50")
    _set_transition_condition(cfg, "following_to_takeover", "sensor_confidence < 0.40")
    _add_hysteresis(cfg)
    _add_recovery_constraints(cfg)
    add(cfg["metadata"]["patch_id"], cfg["metadata"]["description"], "combined", cfg)

    return candidates


def write_candidate_patches(
    supervisor_path: str | Path,
    out_dir: str | Path,
    baseline_trace_path: str | Path | None = None,
) -> list[CandidatePatch]:
    supervisor = load_yaml(supervisor_path)
    candidates = generate_candidate_patches(supervisor)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "source_supervisor": str(supervisor_path),
        "baseline_traces": str(baseline_trace_path) if baseline_trace_path else None,
        "candidates": [],
    }
    for candidate in candidates:
        filename = f"{candidate.patch_id}.yaml"
        path = out / filename
        dump_yaml(candidate.config, path)
        manifest["candidates"].append(
            {
                "patch_id": candidate.patch_id,
                "description": candidate.description,
                "mutation_type": candidate.mutation_type,
                "path": filename,
            }
        )

    with (out / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return candidates
