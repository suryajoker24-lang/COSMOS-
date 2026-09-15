# End-to-End Scientific Detection Engine & Model Inference
import os
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import joblib

from pipeline.models import TransitCandidate, StarDetectionResult
from pipeline.io import load_raw_lightcurve, RawLightCurve
from pipeline.preprocess import preprocess_lightcurve, PreprocessedLightCurve
from pipeline.detrend import detrend_lightcurve, DetrendedLightCurve
from pipeline.gp import gp_detrend_lightcurve
from pipeline.search import search_candidates_bls
from pipeline.refine import refine_candidate_tls
from pipeline.vetting import vet_candidate
from pipeline.features import extract_candidate_features, features_dict_to_dataframe

try:
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import GroupKFold
    HAS_ML = True
except ImportError:
    HAS_ML = False

class ExoHunterModel:
    """GroupKFold-trained LightGBM candidate ranker with isotonic probability calibration."""
    def __init__(self, model_path: Optional[str] = None):
        self.ranker = None
        self.calibrator = None
        self.threshold = 0.50
        
        if model_path and os.path.exists(model_path):
            self.load(model_path)
            
    def load(self, model_path: str):
        data = joblib.load(model_path)
        # Handle both dict format (our save) and direct model format (CandidateClassifier save)
        if isinstance(data, dict):
            self.ranker = data.get("ranker")
            self.calibrator = data.get("calibrator")
            self.threshold = data.get("threshold", 0.50)
        else:
            # Direct model object (from CandidateClassifier.save)
            self.ranker = data
            self.calibrator = None
            self.threshold = 0.20
        
    def save(self, model_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
        joblib.dump({
            "ranker": self.ranker,
            "calibrator": self.calibrator,
            "threshold": self.threshold
        }, model_path)
        
    def predict_candidate_proba(self, df_features: pd.DataFrame) -> np.ndarray:
        if self.ranker is None:
            # Physics-based baseline heuristic
            sde = df_features.get("sde", pd.Series([0]*len(df_features))).values
            snr = df_features.get("snr", pd.Series([0]*len(df_features))).values
            mismatch = df_features.get("odd_even_mismatch", pd.Series([0]*len(df_features))).values
            sec = df_features.get("secondary_eclipse_score", pd.Series([0]*len(df_features))).values

            raw_score = 1.0 / (1.0 + np.exp(-0.6 * (sde - 5.5)))
            penalty = (mismatch > 4.5).astype(float) * 0.35 + (sec > 3.0).astype(float) * 0.35
            cal_prob = np.clip(raw_score - penalty, 0.01, 0.99)
            return cal_prob

        # Check feature count match
        n_expected = getattr(self.ranker, 'n_features_in_', 0)
        n_actual = df_features.shape[1]
        if n_expected > 0 and n_actual != n_expected:
            # Feature mismatch: use physics baseline instead
            sde = df_features.get("sde", pd.Series([0]*len(df_features))).values
            raw_score = 1.0 / (1.0 + np.exp(-0.6 * (sde - 5.5)))
            return np.clip(raw_score, 0.01, 0.99)

        raw_preds = self.ranker.predict_proba(df_features)[:, 1]
        if self.calibrator is not None:
            cal_preds = self.calibrator.predict(raw_preds)
            return np.clip(cal_preds, 0.01, 0.99)
        return raw_preds

def process_star_end_to_end(
    filepath: str,
    model: Optional[ExoHunterModel] = None,
    use_gp: bool = False,
    use_tls: bool = True,
    detrend_window: float = 0.75
) -> StarDetectionResult:
    """
    Executes full 8-stage scientific detection and characterization pipeline on a single star.
    """
    t_start = time.perf_counter()
    
    # 1. IO & Quality Ingestion
    raw = load_raw_lightcurve(filepath)
    
    # 2. Preprocessing & Quarter Stitching
    pre = preprocess_lightcurve(raw)
    
    # 3. Detrending (Wotan Biweight or celerite2 GP)
    if use_gp:
        det = gp_detrend_lightcurve(pre, rho=5.0)
    else:
        det = detrend_lightcurve(pre, method="biweight", window_length=detrend_window)
        
    # 4. BLS Period Search (up to 400 days per problem spec)
    candidates = search_candidates_bls(det, min_period=0.5, max_period=None, top_k=5)
    
    if not candidates:
        t_elapsed = time.perf_counter() - t_start
        return StarDetectionResult(
            star_id=raw.star_id,
            prediction=0,
            confidence=0.01,
            status="SUCCESS",
            runtime_sec=t_elapsed,
            cadence_count=raw.original_len,
            retained_cadence_count=raw.retained_len,
            provenance={
                "detrending": det.method,
                "window_days": det.window_length,
                "cdpp_ppm": det.cdpp_ppm,
                "n_candidates_found": 0
            }
        )
        
    # 5. Windowed TLS Refinement & 6. Statistical Vetting
    refined_cands: List[TransitCandidate] = []
    cand_feats: List[Dict[str, float]] = []
    
    for cand in candidates:
        if use_tls:
            cand = refine_candidate_tls(det, cand)
        cand = vet_candidate(det, cand, quarter_array=pre.quarter)
        feats = extract_candidate_features(cand, det, pre)
        refined_cands.append(cand)
        cand_feats.append(feats)
        
    # 7. ML Ranking & Probability Calibration
    df_feats = features_dict_to_dataframe(cand_feats)
    if model is not None:
        probs = model.predict_candidate_proba(df_feats)
    else:
        probs = ExoHunterModel().predict_candidate_proba(df_feats)
        
    for i, c in enumerate(refined_cands):
        c.confidence = float(probs[i])
        c.ranking_score = float(probs[i])
        
    # 8. Star-Level Decision Aggregation
    best_cand = max(refined_cands, key=lambda c: c.confidence)
    star_confidence = best_cand.confidence
    threshold = model.threshold if model is not None else 0.50
    star_pred = 1 if star_confidence >= threshold else 0
    
    t_elapsed = time.perf_counter() - t_start
    
    return StarDetectionResult(
        star_id=raw.star_id,
        prediction=star_pred,
        confidence=star_confidence,
        period=best_cand.period if star_pred == 1 else None,
        depth_ppm=best_cand.depth_ppm if star_pred == 1 else None,
        duration_hours=best_cand.duration if star_pred == 1 else None,
        best_candidate=best_cand,
        all_candidates=refined_cands,
        status="SUCCESS",
        runtime_sec=t_elapsed,
        cadence_count=raw.original_len,
        retained_cadence_count=raw.retained_len,
        provenance={
            "detrending": det.method,
            "window_days": det.window_length,
            "cdpp_ppm": det.cdpp_ppm,
            "tls_applied": use_tls,
            "n_candidates_found": len(refined_cands)
        }
    )
