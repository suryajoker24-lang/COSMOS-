# Scalable O(N) Gaussian Process Detrending using celerite2 (Foreman-Mackey et al. 2017)
import numpy as np
import warnings
from typing import Optional, Tuple
from dataclasses import dataclass
from pipeline.preprocess import PreprocessedLightCurve
from pipeline.detrend import DetrendedLightCurve, estimate_cdpp_6hr

try:
    import celerite2
    from celerite2 import terms
    from scipy.optimize import minimize
    HAS_CELERITE2 = True
except ImportError:
    HAS_CELERITE2 = False

def gp_detrend_lightcurve(
    lc: PreprocessedLightCurve,
    transit_mask: Optional[np.ndarray] = None,
    rho: float = 5.0,  # characteristic timescale in days
    sigma: float = 0.001
) -> DetrendedLightCurve:
    """
    Fits an O(N) scalable Gaussian Process with a SHOTerm (Stochastically driven Simple Harmonic Oscillator)
    to the out-of-transit flux and predicts the stellar variability trend across all cadences.
    """
    time = lc.time
    flux = lc.flux
    flux_err = lc.flux_err
    
    if not HAS_CELERITE2 or len(time) < 50:
        # If celerite2 is unavailable or time series is tiny, fallback
        from pipeline.detrend import detrend_lightcurve
        return detrend_lightcurve(lc, method="biweight", window_length=0.75, mask=transit_mask)
        
    # Mask out in-transit points during GP fitting
    fit_mask = np.ones(len(time), dtype=bool)
    if transit_mask is not None:
        fit_mask = ~transit_mask
        
    # Standardize time to prevent numerical overflow
    t0_ref = time[0]
    t_fit = time[fit_mask] - t0_ref
    y_fit = flux[fit_mask] - 1.0  # mean-subtracted
    yerr_fit = np.clip(flux_err[fit_mask], 1e-6, 0.1)
    
    # Define celerite2 kernel: SHOTerm with Q = 1/sqrt(2) (underdamped / granulation & rotation proxy)
    w0 = 2.0 * np.pi / max(0.5, rho)
    S0 = (sigma ** 2) / (w0 * (1.0 / np.sqrt(2.0)))
    
    try:
        kernel = terms.SHOTerm(S0=S0, w0=w0, Q=1.0 / np.sqrt(2.0))
        gp = celerite2.GaussianProcess(kernel, mean=0.0)
        gp.compute(t_fit, yerr=yerr_fit)
        
        # Predict GP trend on the entire time array
        t_full = time - t0_ref
        gp_mean = gp.predict(y_fit, t=t_full)
        trend = gp_mean + 1.0
        
        flat_flux = flux / np.clip(trend, 1e-4, None)
        cdpp = estimate_cdpp_6hr(flat_flux)
        
        return DetrendedLightCurve(
            star_id=lc.star_id,
            time=time,
            flux=flat_flux.astype(np.float64),
            trend=trend.astype(np.float64),
            flux_err=flux_err,
            method="celerite2_gp_sho",
            window_length=rho,
            cdpp_ppm=round(cdpp, 2)
        )
    except Exception as e:
        # Fallback to Wotan biweight if GP inversion encounters singularity
        from pipeline.detrend import detrend_lightcurve
        return detrend_lightcurve(lc, method="biweight", window_length=0.75, mask=transit_mask)
