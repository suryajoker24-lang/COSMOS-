import pytest
import numpy as np
from src.data.lightcurve import LightCurve
from src.preprocessing.quarter import normalize_quarters, robust_quarter_location

def test_robust_quarter_location():
    data = np.array([100.0, 101.0, 99.5, 100.2, 500.0, 100.1])
    loc = robust_quarter_location(data)
    assert 99.0 <= loc <= 102.0

def test_normalize_quarters():
    t = np.linspace(0, 100, 1000)
    f = np.concatenate([np.ones(500) * 10000.0, np.ones(500) * 20000.0])
    q = np.concatenate([np.ones(500, dtype=int), np.ones(500, dtype=int) * 2])
    lc = LightCurve(star_id="test", kepid=123, time=t, flux=f, flux_err=np.ones_like(f), quality=np.zeros_like(f, dtype=int), quarter=q)
    
    norm_lc, stats = normalize_quarters(lc)
    assert 1 in stats and 2 in stats
    assert np.isclose(np.median(norm_lc.flux), 1.0, atol=1e-3)
