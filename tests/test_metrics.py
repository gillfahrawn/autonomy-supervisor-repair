from __future__ import annotations

from src.evaluation.metrics import score_events


def test_scoring_uses_specified_weights():
    score = score_events(
        [
            {"property_id": "P5_COLLISION"},
            {"property_id": "P1_CRITICAL_TTC_RESPONSE"},
            {"property_id": "P2_SENSOR_DEGRADATION"},
            {"property_id": "P3_NO_OSCILLATION"},
            {"property_id": "P4_FAKE_SAFETY"},
        ]
    )
    assert score.score == 1175
    assert score.collisions == 1
    assert score.critical_ttc_violations == 1
    assert score.takeover_latency_violations == 1

