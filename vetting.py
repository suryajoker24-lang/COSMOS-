# Scientific Candidate Vetting & False Positive Discrimination
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from pipeline.models import TransitCandidate
from pipeline.detrend import DetrendedLightCurve

def vet_candidate(
    detrended: DetrendedLightCurve,
    cand: TransitCandidate,
    quarter_array: Optional[np.ndarray] = None
) -> TransitCandidate:
    """
    Applies statistical vetting tests:
    1. Odd-even transit depth comparison (EB check)
    2. Secondary eclipse detection at phase 0.5 (EB check)
    3. Multi-quarter / multi-epoch presence
    4. Single epoch dominance
    5. Systematic artifact flags
    """
    time = detrended.time
    flux = detrended.flux
    flux_err = detrended.flux_err
    p = cand.period
    t0 = cand.t0
    dur_days = max(0.01, cand.duration / 24.0)
    
    if p <= 0 or len(time) < 30:
        return cand
        
    # Transit epoch calculation for each cadence
    phase = ((time - t0 + 0.5 * p) % p) / p - 0.5
    in_primary = np.abs(phase * p) <= (dur_days / 2.0)
    epoch_idx = np.round((time - t0) / p)
    
    # 1. Odd vs. Even transit depth test
    odd_mask = in_primary & (np.abs(epoch_idx) % 2 == 1)
    even_mask = in_primary & (np.abs(epoch_idx) % 2 == 0)
    
    odd_depth = 1.0 - np.nanmedian(flux[odd_mask]) if np.sum(odd_mask) >= 2 else cand.depth_ppm * 1e-6
    even_depth = 1.0 - np.nanmedian(flux[even_mask]) if np.sum(even_mask) >= 2 else cand.depth_ppm * 1e-6
    
    odd_std = np.nanstd(flux[odd_mask]) / np.sqrt(max(1, np.sum(odd_mask))) if np.sum(odd_mask) >= 2 else 1e-4
    even_std = np.nanstd(flux[even_mask]) / np.sqrt(max(1, np.sum(even_mask))) if np.sum(even_mask) >= 2 else 1e-4
    
    comb_std = np.sqrt(odd_std**2 + even_std**2)
    odd_even_sigma = float(abs(odd_depth - even_depth) / max(1e-5, comb_std))
    cand.odd_even_mismatch = round(odd_even_sigma, 3)
    
    # 2. Secondary eclipse search at phase 0.5
    in_secondary = np.abs(np.abs(phase) - 0.5) * p <= (dur_days / 2.0)
    
    sec_depth = 1.0 - np.nanmedian(flux[in_secondary]) if np.sum(in_secondary) >= 2 else 0.0
    sec_std = np.nanstd(flux[in_secondary]) / np.sqrt(max(1, np.sum(in_secondary))) if np.sum(in_secondary) >= 2 else 1e-4
    sec_sig = float(max(0.0, sec_depth) / max(1e-5, sec_std))
    cand.secondary_eclipse_score = round(sec_sig, 3)
    
    # 3. Quarter / chunk presence
    if quarter_array is not None and len(quarter_array) == len(time):
        quarters_with_transits = np.unique(quarter_array[in_primary])
        cand.n_quarters = int(len(quarters_with_transits))
    else:
        cand.n_quarters = max(1, min(cand.n_transits, 4))
        
    # 4. Single-epoch dominance check
    if np.sum(in_primary) > 0:
        transit_cadences = epoch_idx[in_primary]
        counts = pd.Series(transit_cadences).value_counts()
        cand.single_epoch_fraction = round(float(counts.max() / len(transit_cadences)), 3)
        
    # 5. Populate structured vetting flags
    cand.vetting_flags = {
        "pass_odd_even": bool(cand.odd_even_mismatch < 3.5),
        "pass_secondary": bool(cand.secondary_eclipse_score < 3.0),
        "pass_multi_transit": bool(cand.n_transits >= 2),
        "pass_epoch_fraction": bool(cand.single_epoch_fraction < 0.75),
        "pass_systematic": bool(not cand.systematic_period_flag),
        "pass_duration": bool(0.5 <= cand.duration <= 20.0)
    }
    
    return cand
