import pytest
import numpy as np
from src.data.lightcurve import LightCurve
from src.candidates.candidate import TransitCandidate
from src.features.extractor import extract_candidate_features, FEATURE_NAMES

def test_extract_candidate_features():
    t = np.linspace(0, 100, 1000)
    f = np.ones_like(t)
    q = np.zeros_like(t, dtype=int)
    lc = LightCurve(star_id="test", kepid=1, time=t, flux=f, flux_err=np.ones_like(f)*1e-4, quality=q, quarter=q)
    cand = TransitCandidate(star_id="test", kepid=1, period=10.0, epoch_t0=1.0, duration_hours=3.0, depth_ppm=500.0, sde=11.0, bls_power=0.05, transit_count=10)
    
    feats = extract_candidate_features(lc, cand, {"kepmag": 13.5, "teff": 5800})
    for name in FEATURE_NAMES:
        assert name in feats
        assert np.isfinite(feats[name])
