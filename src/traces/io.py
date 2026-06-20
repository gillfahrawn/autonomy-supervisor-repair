from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

from src.traces.trace_schema import TRACE_FIELDS, normalize_trace_row


def write_jsonl(rows: Iterable[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(normalize_trace_row(row), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(normalize_trace_row(json.loads(line)))
    return rows


def write_csv(rows: Iterable[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
        writer.writeheader()
        for row in rows:
            normalized = normalize_trace_row(row)
            serialized = dict(normalized)
            serialized["violation_labels"] = "|".join(normalized["violation_labels"])
            writer.writerow(serialized)


def write_trace_pair(rows: list[dict], jsonl_path: str | Path) -> None:
    jsonl_path = Path(jsonl_path)
    write_jsonl(rows, jsonl_path)
    write_csv(rows, jsonl_path.with_suffix(".csv"))


def group_by_run(rows: Iterable[dict]) -> dict[str, list[dict]]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for row in rows:
        grouped.setdefault(str(row["run_id"]), []).append(row)
    return dict(grouped)

