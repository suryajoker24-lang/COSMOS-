# Candidate-First Windowed Transit Least Squares (TLS) Refinement (Hippke & Heller 2019)
import numpy as np
import warnings
from typing import Optional, List, Dict, Any
from pipeline.models import TransitCandidate
from pipeline.detrend import DetrendedLightCurve

try:
    from transitleastsquares import transitleastsquares
    HAS_TLS = True
except ImportError:
    HAS_TLS = False

def refine_candidate_tls(
    detrended: DetrendedLightCurve,
    cand: TransitCandidate,
    period_window_pct: float = 0.02
) -> TransitCandidate:
    """
    Refines a BLS candidate using limb-darkened physical Transit Least Squares (TLS).
    Evaluates a narrow period band (P0 ± 2%) around the candidate period.
    """
    if not HAS_TLS or cand.period <= 0:
        return cand
        
    time = detrended.time
    flux = detrended.flux
    flux_err = detrended.flux_err
    
    p0 = cand.period
    
    if len(time) < 30:
        return cand
        
    # Search in narrow period band around BLS period [0.98*P, 1.02*P]
    p_min = max(0.2, p0 * (1.0 - period_window_pct))
    p_max = p0 * (1.0 + period_window_pct)
    
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = transitleastsquares(time, flux, flux_err)
            tls_res = model.power(
                period_min=p_min,
                period_max=p_max,
                oversampling_factor=2,
                duration_grid_step=1.2,
                show_progress_bar=False,
                verbose=False,
                use_threads=4
            )
            
        if tls_res.SDE > 1.0 and tls_res.period > 0:
            # Update candidate with physical TLS parameters
            cand.source_method = "TLS_refined"
            cand.period = round(float(tls_res.period), 6)
            cand.t0 = round(float(tls_res.T0), 5)
            cand.duration = round(float(tls_res.duration * 24.0), 4)
            cand.depth_ppm = round(float(tls_res.depth * 1e6), 2)
            cand.sde = round(float(tls_res.SDE), 3)
            cand.snr = round(float(tls_res.snr), 2)
            cand.rp_rs = round(float(tls_res.rp_rs), 4)
            cand.fap = round(float(tls_res.FAP), 6)
            cand.n_transits = int(tls_res.distinct_transit_count)
            cand.odd_even_mismatch = round(float(getattr(tls_res, "odd_even_mismatch", 0.0)), 4)
            cand.folded_phase = tls_res.folded_phase
            cand.folded_flux = tls_res.folded_y
            cand.tls_model = tls_res.model_folded_model
    except Exception:
        # Fallback cleanly to BLS candidate on any TLS numerical exception
        pass
        
    return cand
