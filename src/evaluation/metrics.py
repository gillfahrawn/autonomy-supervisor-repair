from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Iterable

from src.verification.stl_properties import (
    P1_CRITICAL_TTC_RESPONSE,
    P2_SENSOR_DEGRADATION,
    P3_NO_OSCILLATION,
    P4_FAKE_SAFETY,
    P5_COLLISION,
    ViolationEvent,
)


@dataclass(frozen=True)
class ScoreBreakdown:
    collisions: int
    critical_ttc_violations: int
    takeover_latency_violations: int
    oscillation_violations: int
    unnecessary_emergency_brakes: int
    score: int

    def to_dict(self) -> dict:
        return asdict(self)


def score_events(events: Iterable[ViolationEvent | dict]) -> ScoreBreakdown:
    counter: Counter[str] = Counter()
    for event in events:
        if isinstance(event, dict):
            property_id = str(event["property_id"])
        else:
            property_id = event.property_id
        counter[property_id] += 1

    collisions = counter[P5_COLLISION]
    critical = counter[P1_CRITICAL_TTC_RESPONSE]
    takeover = counter[P2_SENSOR_DEGRADATION]
    oscillation = counter[P3_NO_OSCILLATION]
    emergency = counter[P4_FAKE_SAFETY]
    score = (
        1000 * collisions
        + 100 * critical
        + 50 * takeover
        + 20 * oscillation
        + 5 * emergency
    )
    return ScoreBreakdown(
        collisions=collisions,
        critical_ttc_violations=critical,
        takeover_latency_violations=takeover,
        oscillation_violations=oscillation,
        unnecessary_emergency_brakes=emergency,
        score=score,
    )

