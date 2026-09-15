# Known Signal Recovery Test
import numpy as np
import pytest
import os
import tempfile
import pandas as pd

from pipeline.io import load_raw_lightcurve
from pipeline.preprocess import preprocess_lightcurve
from pipeline.detrend import detrend_lightcurve
from pipeline.gp import gp_detrend_lightcurve
from pipeline.search import search_candidates_bls
from pipeline.refine import refine_candidate_tls
from pipeline.vetting import vet_candidate
from pipeline.features import extract_candidate_features
from pipeline.model import process_star_end_to_end

def create_synthetic_transit_lightcurve(
    period_days: float = 3.524,
    t0_days: float = 1.2,
    duration_hours: float = 2.5,
    depth_ppm: float = 2000.0,
    total_days: float = 60.0,
    cadence_min: float = 29.4,
    noise_ppm: float = 150.0
):
    """Generates synthetic Kepler light curve with injected trapezoidal transit + stellar variability."""
    cadence_days = cadence_min / (24.0 * 60.0)
    time = np.arange(0.0, total_days, cadence_days)
    n_pts = len(time)
    
    # 1. Stellar variability (low frequency sinusoids)
    variability = 0.005 * np.sin(2.0 * np.pi * time / 12.0) + 0.002 * np.cos(2.0 * np.pi * time / 5.5)
    
    # 2. Injected Box/Trapezoid transit signal
    dur_days = duration_hours / 24.0
    phase = ((time - t0_days + 0.5 * period_days) % period_days) - 0.5 * period_days
    in_transit = np.abs(phase) < (dur_days / 2.0)
    transit_signal = np.zeros(n_pts)
    transit_signal[in_transit] = - (depth_ppm * 1e-6)
    
    # 3. Gaussian White Noise
    noise = np.random.normal(0, noise_ppm * 1e-6, n_pts)
    
    flux = 1.0 + variability + transit_signal + noise
    flux_err = np.full(n_pts, noise_ppm * 1e-6)
    quality = np.zeros(n_pts, dtype=int)
    quarter = np.zeros(n_pts, dtype=int)
    
    return time, flux, flux_err, quality, quarter

def test_known_signal_bls_recovery():
    np.random.seed(42)
    known_period = 3.524
    known_depth = 2000.0
    time, flux, flux_err, quality, quarter = create_synthetic_transit_lightcurve(
        period_days=known_period,
        depth_ppm=known_depth,
        total_days=50.0
    )
    
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df = pd.DataFrame({
            "time": time,
            "flux": flux,
            "flux_err": flux_err,
            "quality": quality,
            "quarter": quarter
        })
        df.to_csv(f.name, index=False)
        temp_path = f.name
        
    try:
        raw = load_raw_lightcurve(temp_path)
        pre = preprocess_lightcurve(raw)
        det = detrend_lightcurve(pre, method="biweight", window_length=0.75)
        
        candidates = search_candidates_bls(det, min_period=1.0, max_period=10.0, top_k=2)
        assert len(candidates) >= 1
        best = candidates[0]
        
        # Period should match within 0.5%
        rel_period_err = abs(best.period - known_period) / known_period
        assert rel_period_err < 0.01, f"Expected period ~{known_period}, got {best.period}"
        assert best.sde > 5.0
        assert best.depth_ppm > 500.0
        
        # Test TLS refinement
        refined = refine_candidate_tls(det, best)
        assert refined.period > 0
        
        # Test Vetting
        vetted = vet_candidate(det, refined)
        assert vetted.vetting_flags["pass_odd_even"] is True
        
        # Test Features
        feats = extract_candidate_features(vetted, det, pre)
        assert "sde" in feats
        assert "depth_to_cdpp_ratio" in feats
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_end_to_end_star_processing():
    np.random.seed(42)
    time, flux, flux_err, quality, quarter = create_synthetic_transit_lightcurve(
        period_days=4.25,
        depth_ppm=2500.0,
        total_days=40.0
    )
    
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df = pd.DataFrame({
            "time": time,
            "flux": flux,
            "flux_err": flux_err,
            "quality": quality,
            "quarter": quarter
        })
        df.to_csv(f.name, index=False)
        temp_path = f.name
        
    try:
        res = process_star_end_to_end(temp_path, use_tls=True)
        assert res.star_id is not None
        assert res.status == "SUCCESS"
        assert res.prediction == 1
        assert res.confidence > 0.5
        assert abs(res.period - 4.25) / 4.25 < 0.01
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
