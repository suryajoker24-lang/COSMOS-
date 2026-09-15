# Working transit detection for COSMOS
# Uses src/search coarse-to-fine BLS with adaptive detrending + phase-folded depth
import os
import sys
import time as _time_mod
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from astropy.timeseries import BoxLeastSquares

sys.path.insert(0, os.path.abspath("."))

from src.search.bls_search import coarse_to_fine_bls
from src.data.lightcurve import load_lightcurve
from src.preprocessing.quarter import normalize_quarters
from src.detrending.adaptive import adaptive_detrend
from src.candidates.candidate import TransitCandidate

DEFAULT_DURATIONS = np.array([0.04, 0.08, 0.15, 0.25, 0.45, 0.70])


def measure_transit_depth(time, flux, period, t0, duration_hours):
    """Phase-fold and measure actual transit depth + SNR."""
    phase = ((time - t0 + 0.5 * period) % period) / period - 0.5
    dur_half_phase = (duration_hours / 24.0) / period / 2.0

    in_mask = np.abs(phase) <= dur_half_phase
    out_mask = np.abs(phase) > 5.0 * dur_half_phase

    n_in = int(np.sum(in_mask))
    n_out = int(np.sum(out_mask))

    if n_in < 3 or n_out < 20:
        return 0.0, 0.0, n_in

    in_med = float(np.median(flux[in_mask]))
    out_med = float(np.median(flux[out_mask]))

    if out_med <= 0:
        return 0.0, 0.0, n_in

    depth_ppm = max(0.0, (out_med - in_med) / out_med * 1e6)

    out_mad = float(np.median(np.abs(flux[out_mask] - out_med)))
    noise = 1.4826 * out_mad / np.sqrt(max(1, n_in))
    snr = (out_med - in_med) / out_med / noise if noise > 0 else 0.0

    return depth_ppm, snr, n_in


def detect_single_star(filepath: str) -> Dict[str, Any]:
    """
    Full transit detection for one star.
    Adaptive detrending -> coarse-to-fine BLS -> phase-folded depth measurement.
    """
    t_start = _time_mod.time()
    star_id = os.path.splitext(os.path.basename(filepath))[0]

    try:
        lc = load_lightcurve(filepath)
        norm_lc, _ = normalize_quarters(lc)
        det_lc, trend = adaptive_detrend(norm_lc, window_length_days=2.0)

        time = det_lc.time
        flux = det_lc.flux

        if len(time) < 100:
            return _empty_result(star_id)

        # Coarse-to-fine BLS up to 400 days
        # Filter durations to be less than min_period
        valid_durations = DEFAULT_DURATIONS[DEFAULT_DURATIONS < min(0.5 * min_period, 0.4)]
        if len(valid_durations) == 0:
            valid_durations = np.array([0.04, 0.08, 0.15])
        candidates = coarse_to_fine_bls(
            time, flux, det_lc.flux_err,
            period_min=0.5, period_max=400.0,
            n_coarse=10000, n_peaks=10, n_fine=500,
            durations=valid_durations,
            star_id=star_id, kepid=0,
        )

        if not candidates:
            return _empty_result(star_id)

        # Measure depth via phase folding
        for c in candidates:
            depth_ppm, snr, n_in = measure_transit_depth(
                time, flux, c.period, c.epoch_t0, c.duration_hours
            )
            c.depth_ppm = round(depth_ppm, 2)
            c.transit_snr = round(snr, 2)
            c.in_transit_points = n_in

        # Sort by SNR, pick best
        candidates.sort(key=lambda c: c.transit_snr, reverse=True)
        best = candidates[0]

        if best.transit_snr > 0:
            confidence = float(1.0 / (1.0 + np.exp(-0.25 * (best.transit_snr - 7.0))))
        else:
            confidence = 0.01
        confidence = round(np.clip(confidence, 0.01, 0.99), 4)

        # Penalize systematic periods
        if best.period and any(abs(best.period - p) < 0.05 for p in [2.5, 3.0, 4.0, 0.5, 1.0]):
            confidence *= 0.2

        threshold = 0.30
        prediction = 1 if confidence >= threshold else 0

        return {
            "star_id": star_id,
            "prediction": prediction,
            "confidence": confidence,
            "period": round(best.period, 6) if prediction == 1 else None,
            "depth_ppm": round(best.depth_ppm, 2) if prediction == 1 and best.depth_ppm > 1 else None,
            "duration_hours": round(best.duration_hours, 4) if prediction == 1 else None,
            "epoch_t0": round(best.epoch_t0, 5) if prediction == 1 else None,
            "candidates": [
                {"period": round(c.period, 6), "depth_ppm": round(c.depth_ppm, 2),
                 "duration_hours": round(c.duration_hours, 4),
                 "snr": round(c.transit_snr, 2), "bls_power": round(c.bls_power, 6),
                 "in_transit_points": c.in_transit_points}
                for c in candidates[:5]
            ],
            "runtime_sec": round(_time_mod.time() - t_start, 2),
            "status": "SUCCESS",
        }

    except Exception as e:
        return {
            "star_id": star_id, "prediction": 0, "confidence": 0.01,
            "period": None, "depth_ppm": None, "duration_hours": None,
            "candidates": [],
            "runtime_sec": round(_time_mod.time() - t_start, 2),
            "status": f"ERROR: {str(e)}",
        }


def _empty_result(star_id: str) -> Dict[str, Any]:
    return {
        "star_id": star_id, "prediction": 0, "confidence": 0.01,
        "period": None, "depth_ppm": None, "duration_hours": None, "epoch_t0": None,
        "candidates": [], "runtime_sec": 0.0, "status": "NO_CANDIDATES",
    }
