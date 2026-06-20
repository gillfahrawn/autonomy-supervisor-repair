from __future__ import annotations

from pathlib import Path


def export_smv_placeholder(supervisor: dict, path: str | Path) -> None:
    """Write a simple future-facing nuXmv model skeleton without requiring nuXmv."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    states = ", ".join(supervisor.get("states", []))
    initial = supervisor.get("initial_state")
    lines = [
        "MODULE main",
        f"VAR state : {{{states}}};",
        "ASSIGN",
        f"  init(state) := {initial};",
        "  next(state) := case",
    ]
    for transition in supervisor.get("transitions", []):
        lines.append(
            f"    state = {transition.get('from')} : {transition.get('to')}; -- {transition.get('name')}"
        )
    lines.extend(["    TRUE : state;", "  esac;"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

