# Physics-Vetting and Automated Triage Pipeline
# Executes live target analysis via TLS / BLS, Wotan detrending, and odd-even eclipsing binary vetting
import os
import glob
import logging
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

try:
    import lightkurve as lk
except ImportError:
    lk = None

try:
    from transitleastsquares import transitleastsquares
except ImportError:
    transitleastsquares = None

from src.data.lightcurve import load_lightcurve, LightCurve
from src.detrending.adaptive import adaptive_detrend, wotan_highpass_detrend
from src.search.bls_search import coarse_to_fine_bls
from src.validation.nasa_cross_validator import cross_validate_star_with_nasa

logger = logging.getLogger("cosmos.target_analyzer")

def find_local_lightcurve(target_str: str) -> Optional[str]:
    """
    Finds a local light curve file matching the target string.
    """
    clean = str(target_str).strip()
    digits = "".join(filter(str.isdigit, clean))
    patterns = [
        f"data/dev/*{clean}*.parquet",
        f"data/dev/*{clean}*.csv",
        f"data/private_test/*{clean}*.parquet",
        f"data/uploads/*{clean}*.*"
    ]
    if digits:
        patterns.extend([
            f"data/dev/*{digits}*.parquet",
            f"data/private_test/*{digits}*.parquet"
        ])
    for p in patterns:
        matches = glob.glob(p)
        if matches:
            return matches[0]
    return None

def analyze_nasa_target(target_id: Any, confidence_threshold: float = 0.75) -> Dict[str, Any]:
    """
    Downloads or loads target Kepler data, applies high-pass detrending,
    runs a transit search template (TLS/BLS), and validates candidates
    against stellar harmonics and eclipsing binaries.
    """
    target_clean = str(target_id).strip()
    digits = "".join(filter(str.isdigit, target_clean))
    kic_id = int(digits) if digits else 0

    time_arr = None
    flux_arr = None
    star_name = f"KIC {kic_id}" if kic_id > 0 else target_clean

    # 1. Attempt local file load first for maximum speed
    local_path = find_local_lightcurve(target_clean)
    if local_path and os.path.exists(local_path):
        try:
            lc = load_lightcurve(local_path, high_pass_detrend=False)
            det_lc, _ = adaptive_detrend(lc, window_length_days=2.0)
            time_arr = det_lc.time
            flux_arr = det_lc.flux
        except Exception as e:
            logger.warning(f"Failed to load local light curve {local_path}: {e}")

    # 2. Download live NASA Kepler Data from MAST if not available locally
    if (time_arr is None or len(time_arr) == 0) and kic_id > 0 and lk is not None:
        try:
            logger.info(f"Fetching live light curve for KIC {kic_id} from MAST...")
            search_result = lk.search_lightcurve(f"KIC {kic_id}", mission="Kepler", author="Kepler")
            if len(search_result) > 0:
                sr_subset = search_result[:6] if len(search_result) > 6 else search_result
                lc_collection = sr_subset.download_all()
                stitched = lc_collection.stitch()
                stitched = stitched.remove_nans()
                flat_flux, _ = wotan_highpass_detrend(stitched.time.value, stitched.flux.value, window_length_days=2.0)
                time_arr = np.array(stitched.time.value, dtype=np.float64)
                flux_arr = np.array(flat_flux, dtype=np.float64)
        except Exception as e:
            logger.warning(f"MAST live download error for KIC {kic_id}: {e}")

    if time_arr is None or len(time_arr) < 50:
        return {
            "status": "Error",
            "message": f"Target {target_clean} not found in local directories or NASA MAST archives.",
            "is_false_positive": True,
            "isFalsePositive": True,
            "classificationVerdict": "False Positive",
            "verdict": "False Positive",
            "rejection_reason": "No observational photometric data located.",
            "systemNotes": "No observational photometric data located.",
            "calibratedConfidence": "0.0%",
            "orbitalPeriod": "N/A",
            "depthAndDuration": "N/A",
            "plotData": {"x": [], "y": []}
        }

    # 3. Run Transit Search (TLS or fast coarse-to-fine BLS)
    detected_period = 0.0
    ppm_depth = 0.0
    duration_hours = 0.0
    sde_score = 0.0
    odd_even_mismatch = 0.0
    sde_coarse = 10.0

    use_tls = (transitleastsquares is not None and len(time_arr) <= 15000)
    if use_tls:
        try:
            model = transitleastsquares(time_arr, flux_arr)
            results = model.power()
            detected_period = float(results.period)
            detected_depth = float(results.depth)
            ppm_depth = (1.0 - detected_depth) * 1e6
            duration_hours = float(results.duration) * 24.0
            sde_score = float(results.SDE)

            if hasattr(results, 'transit_depths') and len(results.transit_depths) > 1:
                odd_depth = np.mean(results.transit_depths[::2])
                even_depth = np.mean(results.transit_depths[1::2])
                odd_even_mismatch = abs(odd_depth - even_depth) / (detected_depth + 1e-8)
            sde_coarse = getattr(results, "SDE_coarse", sde_score)
        except Exception as e:
            logger.warning(f"TLS search error: {e}, falling back to BLS")
            use_tls = False

    if detected_period <= 0.0:
        cands = coarse_to_fine_bls(
            time_arr, flux_arr, np.ones_like(flux_arr) * 1e-4,
            n_coarse=15000, n_peaks=6, star_id=target_clean, kepid=kic_id
        )
        if cands:
            best = cands[0]
            detected_period = float(best.period)
            ppm_depth = float(best.depth_ppm)
            duration_hours = float(best.duration_hours)
            sde_score = float(best.sde)
            odd_even_mismatch = 1.0 - float(best.odd_even_consistency)
            sde_coarse = sde_score

    # 4. Dynamic Automated Physics-Vetting Matrix
    calibrated_confidence = min(1.0, max(0.0, (sde_score - 5.0) / 15.0))
    is_false_positive = False
    rejection_reason = "None"
    verdict = "Planet Candidate"

    if calibrated_confidence < confidence_threshold:
        is_false_positive = True
        rejection_reason = f"Low Confidence Threshold ({calibrated_confidence:.1%} < {confidence_threshold:.1%})"
        verdict = "False Positive"
    elif odd_even_mismatch > 0.25:
        is_false_positive = True
        rejection_reason = "Eclipsing Binary Signature (Odd/Even depth mismatch detected)"
        verdict = "False Positive"
    elif sde_coarse < 4.0:
        is_false_positive = True
        rejection_reason = "Stellar Harmonic Artifact (Alias Loop Triggered)"
        verdict = "False Positive"
    elif ppm_depth > 50000.0:
        is_false_positive = True
        rejection_reason = "Eclipsing Binary Signature (Stellar Eclipse Depth > 5%)"
        verdict = "False Positive"

    # Slice for interface performance (subsample up to 2000 points)
    step = max(1, len(time_arr) // 2000)
    sub_idx = np.arange(0, len(time_arr), step)
    x_pts = [round(float(t), 4) for t in time_arr[sub_idx]]
    y_pts = [round(float(f), 6) for f in flux_arr[sub_idx]]

    # 5. Cross-validate with NASA Exoplanet Archive
    nasa_val = cross_validate_star_with_nasa(
        star_id=target_clean,
        cosmos_period=detected_period,
        cosmos_depth=ppm_depth,
        cosmos_duration=duration_hours,
        cosmos_confidence=calibrated_confidence
    )

    return {
        "status": "Success",
        "verdict": verdict,
        "classificationVerdict": verdict,
        "is_false_positive": is_false_positive,
        "isFalsePositive": is_false_positive,
        "rejection_reason": rejection_reason,
        "systemNotes": rejection_reason,
        "calibrated_confidence": f"{calibrated_confidence * 100:.1f}%",
        "calibratedConfidence": f"{calibrated_confidence * 100:.1f}%",
        "orbital_period_days": f"{detected_period:.4f}",
        "orbitalPeriod": f"{detected_period:.4f} days",
        "depth_ppm": f"{ppm_depth:.1f}",
        "duration_hours": f"{duration_hours:.2f}",
        "depthAndDuration": f"{ppm_depth:.1f} ppm / {duration_hours:.2f}h",
        "time_stamps": x_pts,
        "detrended_flux": y_pts,
        "plotData": {
            "x": x_pts,
            "y": y_pts
        },
        "nasaValidation": nasa_val
    }
