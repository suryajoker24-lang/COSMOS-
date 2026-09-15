import pytest
import numpy as np
from src.search.bls_search import coarse_to_fine_bls

def test_coarse_to_fine_bls():
    t = np.linspace(0, 200, 10000)
    f = np.ones_like(t) + np.random.normal(0, 1e-4, size=len(t))
    
    # Inject 10.0 day period transit, depth 2000 ppm (0.002), duration 0.2 days
    p_true = 10.0
    t0_true = 3.5
    phase = ((t - t0_true) / p_true) % 1.0
    phase = np.where(phase > 0.5, phase - 1.0, phase)
    f[np.abs(phase) < (0.2 / p_true / 2.0)] -= 0.002
    
    cands = coarse_to_fine_bls(t, f, period_min=3.0, period_max=50.0, n_coarse=2000, n_peaks=3, n_fine=100)
    assert len(cands) > 0
    best = cands[0]
    # Check period recovery within 2%
    err = abs(best.period - p_true) / p_true
    assert err < 0.02
