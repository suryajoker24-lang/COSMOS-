import pytest
from src.candidates.candidate import TransitCandidate
from src.calibration.calibrator import aggregate_star_candidates

def test_aggregate_empty_candidates():
    res = aggregate_star_candidates([])
    assert res["prediction"] == 0
    assert res["confidence"] < 0.1
    assert res["period"] is None

def test_aggregate_strong_candidate():
    c = TransitCandidate(star_id="test", kepid=1, period=20.0, epoch_t0=1.0, duration_hours=5.0, depth_ppm=1000.0, sde=15.0, bls_power=0.1, transit_count=6, calibrated_confidence=0.92)
    res = aggregate_star_candidates([c], threshold=0.5)
    assert res["prediction"] == 1
    assert res["confidence"] == 0.92
    assert res["period"] == 20.0
