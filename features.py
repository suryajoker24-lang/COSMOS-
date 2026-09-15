# 23-Feature Tabular Vector Extraction for ML Candidate Ranking
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from pipeline.models import TransitCandidate
from pipeline.detrend import DetrendedLightCurve
from pipeline.preprocess import PreprocessedLightCurve

FEATURE_NAMES = [
    "period",
    "log_period",
    "duration_hours",
    "depth_ppm",
    "log_depth",
    "sde",
    "snr",
    "fap",
    "rp_rs",
    "duration_over_period",
    "odd_even_mismatch",
    "secondary_eclipse_score",
    "n_transits",
    "n_quarters",
    "single_epoch_fraction",
    "systematic_period_flag",
    "cdpp_ppm",
    "duty_cycle",
    "time_span_days",
    "depth_to_cdpp_ratio",
    "transit_duty_cycle",
    "log_snr",
    "source_method_is_tls"
]

def extract_candidate_features(
    cand: TransitCandidate,
    detrended: DetrendedLightCurve,
    preprocessed: Optional[PreprocessedLightCurve] = None
) -> Dict[str, float]:
    """
    Extracts standardized 23-feature vector for LightGBM candidate ranker.
    """
    p = max(0.001, cand.period)
    dur_h = max(0.01, cand.duration)
    dur_days = dur_h / 24.0
    depth = max(1.0, cand.depth_ppm)
    snr = max(0.01, cand.snr)
    cdpp = max(1.0, detrended.cdpp_ppm)
    
    time_span = float(detrended.time[-1] - detrended.time[0]) if len(detrended.time) > 1 else 100.0
    duty_cycle = preprocessed.duty_cycle if preprocessed is not None else 0.9
    
    feats = {
        "period": float(p),
        "log_period": float(np.log10(p)),
        "duration_hours": float(dur_h),
        "depth_ppm": float(depth),
        "log_depth": float(np.log10(depth)),
        "sde": float(cand.sde),
        "snr": float(snr),
        "fap": float(cand.fap),
        "rp_rs": float(cand.rp_rs),
        "duration_over_period": float(dur_days / p),
        "odd_even_mismatch": float(cand.odd_even_mismatch),
        "secondary_eclipse_score": float(cand.secondary_eclipse_score),
        "n_transits": float(cand.n_transits),
        "n_quarters": float(cand.n_quarters),
        "single_epoch_fraction": float(cand.single_epoch_fraction),
        "systematic_period_flag": 1.0 if cand.systematic_period_flag else 0.0,
        "cdpp_ppm": float(cdpp),
        "duty_cycle": float(duty_cycle),
        "time_span_days": float(time_span),
        "depth_to_cdpp_ratio": float(depth / cdpp),
        "transit_duty_cycle": float((cand.n_transits * dur_days) / max(1.0, time_span)),
        "log_snr": float(np.log10(snr)),
        "source_method_is_tls": 1.0 if "TLS" in cand.source_method else 0.0
    }
    
    return feats

def features_dict_to_dataframe(feature_dicts: List[Dict[str, float]]) -> pd.DataFrame:
    """Converts a list of feature dictionaries to a strictly-ordered DataFrame."""
    df = pd.DataFrame(feature_dicts)
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df[col] = 0.0
    return df[FEATURE_NAMES]
