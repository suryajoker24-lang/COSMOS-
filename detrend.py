# Transit-Preserving Detrending using Wōtan (Hippke et al. 2019)
import numpy as np
import warnings
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pipeline.preprocess import PreprocessedLightCurve

try:
    from wotan import flatten
    HAS_WOTAN = True
except ImportError:
    HAS_WOTAN = False

@dataclass
class DetrendedLightCurve:
    star_id: str
    time: np.ndarray
    flux: np.ndarray             # Flattened flux (centered at 1.0)
    trend: np.ndarray            # Removed low-frequency stellar activity trend
    flux_err: np.ndarray
    method: str
    window_length: float         # days
    cdpp_ppm: float              # 6-hour Combined Differential Photometric Precision proxy

def estimate_cdpp_6hr(flux: np.ndarray, cadence_days: float = 0.0204) -> float:
    """
    Computes 6-hour CDPP (Combined Differential Photometric Precision) proxy in ppm.
    6 hours = ~12-13 Kepler long-cadence intervals.
    """
    n_pts_6hr = max(3, int(0.25 / cadence_days))
    if len(flux) < n_pts_6hr * 2:
        return float(np.nanstd(flux) * 1e6)
        
    # Running mean with boxcar window of 6 hours
    kernel = np.ones(n_pts_6hr) / n_pts_6hr
    smoothed = np.convolve(flux, kernel, mode="same")
    diff = flux - smoothed
    mad = np.nanmedian(np.abs(diff - np.nanmedian(diff)))
    robust_std = 1.4826 * mad
    return float(robust_std * 1e6)

def detrend_lightcurve(
    lc: PreprocessedLightCurve,
    method: str = "biweight",
    window_length: float = 0.75,
    break_tolerance: float = 0.5,
    mask: Optional[np.ndarray] = None
) -> DetrendedLightCurve:
    """
    Detrends light curve using Wōtan robust biweight or median filter.
    Preserves transit depth and shape while eliminating stellar rotation/variability.
    """
    time = lc.time
    flux = lc.flux
    flux_err = lc.flux_err
    
    if len(time) < 10:
        return DetrendedLightCurve(
            star_id=lc.star_id,
            time=time,
            flux=flux,
            trend=np.ones_like(flux),
            flux_err=flux_err,
            method="none",
            window_length=window_length,
            cdpp_ppm=estimate_cdpp_6hr(flux)
        )
        
    if HAS_WOTAN:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                flatten_kwargs = {
                    "time": time,
                    "flux": flux,
                    "method": method,
                    "window_length": window_length,
                    "break_tolerance": break_tolerance,
                    "return_trend": True
                }
                if mask is not None:
                    flatten_kwargs["mask"] = mask
                    
                flat_flux, trend = flatten(**flatten_kwargs)
        except Exception:
            # Fallback to simple sliding median if wotan encounter numerical edge cases
            flat_flux, trend = _sliding_median_detrend(time, flux, window_length)
    else:
        flat_flux, trend = _sliding_median_detrend(time, flux, window_length)
        
    # Clean any remaining NaNs in trend
    nan_mask = ~np.isfinite(flat_flux) | ~np.isfinite(trend)
    if np.any(nan_mask):
        flat_flux = np.where(nan_mask, 1.0, flat_flux)
        trend = np.where(nan_mask, np.nanmedian(flux), trend)
        
    cdpp = estimate_cdpp_6hr(flat_flux)
    
    return DetrendedLightCurve(
        star_id=lc.star_id,
        time=time,
        flux=flat_flux.astype(np.float64),
        trend=trend.astype(np.float64),
        flux_err=flux_err,
        method=f"wotan_{method}" if HAS_WOTAN else "sliding_median",
        window_length=window_length,
        cdpp_ppm=round(cdpp, 2)
    )

def _sliding_median_detrend(
    time: np.ndarray,
    flux: np.ndarray,
    window_length: float
) -> Tuple[np.ndarray, np.ndarray]:
    """Fallback sliding median detrending."""
    trend = np.ones_like(flux)
    half_window = window_length / 2.0
    for i in range(len(time)):
        t_i = time[i]
        in_win = (time >= t_i - half_window) & (time <= t_i + half_window)
        med = np.nanmedian(flux[in_win])
        trend[i] = med if np.isfinite(med) and med > 0 else 1.0
    flat = flux / trend
    return flat, trend
