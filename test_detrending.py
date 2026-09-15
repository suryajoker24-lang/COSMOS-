import pytest
import numpy as np
from src.detrending.adaptive import fast_robust_detrend, adaptive_detrend
from src.data.lightcurve import LightCurve

def test_fast_robust_detrend():
    t = np.linspace(0, 30, 1500)
    # Stellar trend + injected box transit
    trend_true = 1.0 + 0.01 * np.sin(2 * np.pi * t / 10.0)
    f = trend_true.copy()
    # Injected transit at day 15, depth 0.005 (5000 ppm)
    in_transit = np.abs(t - 15.0) < 0.2
    f[in_transit] -= 0.005
    
    det, trend = fast_robust_detrend(t, f, window_length_days=2.0)
    assert np.all(np.isfinite(det))
    # Transit must be preserved in detrended flux
    assert np.min(det[in_transit]) < 0.997
