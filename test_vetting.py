import pytest
import numpy as np
from src.data.lightcurve import LightCurve
from src.candidates.candidate import TransitCandidate
from src.vetting.vetting import vet_candidate, phase_fold

def test_vet_candidate():
    t = np.linspace(0, 100, 5000)
    f = np.ones_like(t)
    q = np.zeros_like(t, dtype=int)
    
    p = 12.0
    t0 = 2.0
    phase = ((t - t0) / p) % 1.0
    phase = np.where(phase > 0.5, phase - 1.0, phase)
    f[np.abs(phase) < 0.01] -= 0.003
    
    lc = LightCurve(star_id="test", kepid=999, time=t, flux=f, flux_err=np.ones_like(f)*1e-4, quality=q, quarter=q)
    cand = TransitCandidate(star_id="test", kepid=999, period=p, epoch_t0=t0, duration_hours=4.0, depth_ppm=3000.0, sde=15.0, bls_power=0.1, transit_count=8)
    
    vet_candidate(lc, cand)
    assert cand.depth_ppm > 2000.0
    assert cand.odd_even_consistency > 0.5
