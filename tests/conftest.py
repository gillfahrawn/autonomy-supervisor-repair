from __future__ import annotations

from pathlib import Path

import pytest

from src.supervisor.schemas import load_yaml


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def baseline_config() -> dict:
    return load_yaml(ROOT / "configs" / "baseline_supervisor.yaml")

