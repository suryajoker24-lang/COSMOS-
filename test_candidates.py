import pytest
from src.candidates.candidate import TransitCandidate

def test_transit_candidate_to_dict():
    cand = TransitCandidate(
        star_id="STAR_0001",
        kepid=12345,
        period=15.5,
        epoch_t0=2.3,
        duration_hours=4.2,
        depth_ppm=1200.0,
        sde=12.5,
        bls_power=0.08,
        transit_count=10,
        odd_even_consistency=0.95,
        secondary_eclipse_score=0.2,
        quarter_recurrence_fraction=0.88,
        calibrated_confidence=0.89
    )
    d = cand.to_dict()
    assert d["star_id"] == "STAR_0001"
    assert d["period"] == 15.5
    assert d["calibrated_confidence"] == 0.89
