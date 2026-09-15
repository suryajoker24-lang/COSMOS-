import numpy as np
import warnings
from dataclasses import dataclass
from typing import Optional
from pipeline.preprocess import PreprocessedLightCurve

try:
    from wotan import flatten
    HAS_WOTAN=True
except ImportError:
    HAS_WOTAN=False

@dataclass
class DetrendedLightCurve:
    star_id: str
    time: np.ndarray
    flux: np.ndarray
    trend: np.ndarray
    flux_err: np.ndarray
    method: str
    window_length: float
    cdpp_ppm: float

def estimate_cdpp_6hr(flux, cadence_days=0.0204):
    n=max(3,int(0.25/cadence_days))
    if len(flux)<2*n: return float(np.nanstd(flux)*1e6)
    smooth=np.convolve(flux,np.ones(n)/n,mode='same')
    d=flux-smooth; mad=np.nanmedian(np.abs(d-np.nanmedian(d)))
    return float(1.4826*mad*1e6)

def _median_detrend(time,flux,window):
    trend=np.empty_like(flux); half=window/2
    for i,ti in enumerate(time):
        m=(time>=ti-half)&(time<=ti+half); med=np.nanmedian(flux[m])
        trend[i]=med if np.isfinite(med) and med>0 else 1.0
    return flux/np.clip(trend,1e-8,None),trend

def detrend_lightcurve(lc: PreprocessedLightCurve, method='biweight', window_length=0.75, break_tolerance=0.5, mask: Optional[np.ndarray]=None):
    if HAS_WOTAN and len(lc.time)>=10:
        try:
            kw=dict(time=lc.time,flux=lc.flux,method=method,window_length=window_length,break_tolerance=break_tolerance,return_trend=True)
            if mask is not None: kw['mask']=mask
            with warnings.catch_warnings():
                warnings.simplefilter('ignore'); flat,trend=flatten(**kw)
        except Exception: flat,trend=_median_detrend(lc.time,lc.flux,window_length)
    else: flat,trend=_median_detrend(lc.time,lc.flux,window_length)
    bad=~np.isfinite(flat)|~np.isfinite(trend)
    flat=np.where(bad,1.0,flat); trend=np.where(bad,np.nanmedian(lc.flux),trend)
    return DetrendedLightCurve(lc.star_id,lc.time,flat.astype(float),trend.astype(float),lc.flux_err,f'wotan_{method}' if HAS_WOTAN else 'median_fallback',window_length,round(estimate_cdpp_6hr(flat),2))
