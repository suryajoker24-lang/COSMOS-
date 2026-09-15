# Robust Scientific Preprocessing: Quarter Stitching, Gap Splitting, Outlier Rejection
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from pipeline.io import RawLightCurve

@dataclass
class PreprocessedLightCurve:
    star_id: str
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    quarter: np.ndarray
    quarter_medians: Dict[int, float] = field(default_factory=dict)
    n_points: int = 0
    time_span_days: float = 0.0
    duty_cycle: float = 0.0

def preprocess_lightcurve(
    raw: RawLightCurve,
    upper_sigma_clip: float = 5.0,
    lower_extreme_clip: float = 20.0,
    min_points_per_quarter: int = 50
) -> PreprocessedLightCurve:
    """
    Quarter-by-quarter robust median normalization, gap-aware stitching,
    and positive flare/cosmic ray outlier rejection.
    """
    time = raw.time.copy()
    flux = raw.flux.copy()
    flux_err = raw.flux_err.copy()
    quarter = raw.quarter.copy()
    
    unique_quarters = np.unique(quarter)
    
    norm_time_list = []
    norm_flux_list = []
    norm_err_list = []
    norm_quarter_list = []
    quarter_medians = {}
    
    # If all quarters are 0, detect quarters/chunks by large time gaps (>10 days)
    if len(unique_quarters) == 1 and unique_quarters[0] == 0 and len(time) > 1:
        time_diffs = np.diff(time)
        split_indices = np.where(time_diffs > 10.0)[0] + 1
        chunks_time = np.split(time, split_indices)
        chunks_flux = np.split(flux, split_indices)
        chunks_err = np.split(flux_err, split_indices)
        
        for q_idx, (c_t, c_f, c_e) in enumerate(zip(chunks_time, chunks_flux, chunks_err)):
            if len(c_t) < min_points_per_quarter:
                continue
            med = float(np.nanmedian(c_f))
            if med <= 0 or not np.isfinite(med):
                continue
            quarter_medians[q_idx] = med
            
            c_fn = c_f / med
            c_en = c_e / med
            
            # Robust sigma clipping on flares (positive outliers)
            mad = np.nanmedian(np.abs(c_fn - 1.0))
            std_est = 1.4826 * mad if mad > 0 else np.nanstd(c_fn)
            if std_est > 0:
                # Mask extreme positive spikes (flares) and extreme unphysical negative spikes
                valid = (c_fn <= 1.0 + upper_sigma_clip * std_est) & (c_fn >= 1.0 - lower_extreme_clip * std_est)
                c_t = c_t[valid]
                c_fn = c_fn[valid]
                c_en = c_en[valid]
                
            norm_time_list.append(c_t)
            norm_flux_list.append(c_fn)
            norm_err_list.append(c_en)
            norm_quarter_list.append(np.full(len(c_t), q_idx, dtype=np.int32))
            
    else:
        for q in unique_quarters:
            q_mask = (quarter == q)
            q_time = time[q_mask]
            q_flux = flux[q_mask]
            q_err = flux_err[q_mask]
            
            if len(q_time) < min_points_per_quarter:
                continue
                
            med = float(np.nanmedian(q_flux))
            if med <= 0 or not np.isfinite(med):
                continue
                
            quarter_medians[int(q)] = med
            q_fn = q_flux / med
            q_en = q_err / med
            
            mad = np.nanmedian(np.abs(q_fn - 1.0))
            std_est = 1.4826 * mad if mad > 0 else np.nanstd(q_fn)
            if std_est > 0:
                valid = (q_fn <= 1.0 + upper_sigma_clip * std_est) & (q_fn >= 1.0 - lower_extreme_clip * std_est)
                q_time = q_time[valid]
                q_fn = q_fn[valid]
                q_en = q_en[valid]
                
            norm_time_list.append(q_time)
            norm_flux_list.append(q_fn)
            norm_err_list.append(q_en)
            norm_quarter_list.append(np.full(len(q_time), int(q), dtype=np.int32))
            
    if not norm_time_list:
        # Fallback if all filtering failed
        med = float(np.nanmedian(flux)) if len(flux) > 0 else 1.0
        return PreprocessedLightCurve(
            star_id=raw.star_id,
            time=time,
            flux=flux / max(med, 1e-6),
            flux_err=flux_err / max(med, 1e-6),
            quarter=quarter,
            quarter_medians={0: med},
            n_points=len(time),
            time_span_days=float(time[-1] - time[0]) if len(time) > 1 else 0.0,
            duty_cycle=1.0
        )
        
    stitched_time = np.concatenate(norm_time_list)
    stitched_flux = np.concatenate(norm_flux_list)
    stitched_err = np.concatenate(norm_err_list)
    stitched_quarter = np.concatenate(norm_quarter_list)
    
    # Sort by time
    sort_idx = np.argsort(stitched_time)
    stitched_time = stitched_time[sort_idx]
    stitched_flux = stitched_flux[sort_idx]
    stitched_err = stitched_err[sort_idx]
    stitched_quarter = stitched_quarter[sort_idx]
    
    time_span = float(stitched_time[-1] - stitched_time[0]) if len(stitched_time) > 1 else 0.0
    # Kepler long cadence is ~29.4 min = 0.0204 days
    expected_cadences = (time_span / 0.0204) if time_span > 0 else len(stitched_time)
    duty_cycle = round(float(len(stitched_time) / max(1.0, expected_cadences)), 4)
    duty_cycle = min(1.0, max(0.0, duty_cycle))
    
    return PreprocessedLightCurve(
        star_id=raw.star_id,
        time=stitched_time,
        flux=stitched_flux,
        flux_err=stitched_err,
        quarter=stitched_quarter,
        quarter_medians=quarter_medians,
        n_points=len(stitched_time),
        time_span_days=round(time_span, 3),
        duty_cycle=duty_cycle
    )
