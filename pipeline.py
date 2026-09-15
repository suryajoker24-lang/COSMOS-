# End-to-end Transit Detection Pipeline
import os
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ProcessPoolExecutor, as_completed

from .data.lightcurve import LightCurve, load_lightcurve
from .preprocessing.quarter import normalize_quarters
from .detrending.adaptive import adaptive_detrend
from .search.bls_search import coarse_to_fine_bls
from .vetting.vetting import vet_candidate
from .features.extractor import extract_candidate_features
from .models.classifier import CandidateClassifier
from .calibration.calibrator import aggregate_star_candidates
from .candidates.candidate import TransitCandidate

class TransitDetectionPipeline:
    def __init__(self, model_dir: Optional[str] = "models"):
        self.model: Optional[CandidateClassifier] = None
        if model_dir and os.path.exists(os.path.join(model_dir, "candidate_ranker.joblib")):
            try:
                self.model = CandidateClassifier.load(model_dir)
            except Exception as e:
                print(f"Warning: Could not load trained model from {model_dir}: {e}")
                
    def analyze_lightcurve(
        self,
        lc: LightCurve,
        stellar_meta: Optional[Dict[str, Any]] = None,
        n_coarse: int = 15000,
        n_peaks: int = 12
    ) -> Dict[str, Any]:
        # 1. Normalize quarters
        norm_lc, _ = normalize_quarters(lc)
        
        # 2. Adaptive detrending
        detrended_lc, _ = adaptive_detrend(norm_lc, window_length_days=2.0)
        
        # 3. Coarse-to-fine BLS search
        candidates = coarse_to_fine_bls(
            detrended_lc.time,
            detrended_lc.flux,
            detrended_lc.flux_err,
            n_coarse=n_coarse,
            n_peaks=n_peaks,
            star_id=lc.star_id,
            kepid=lc.kepid
        )
        
        if not candidates:
            return {
                "star_id": lc.star_id,
                "kepid": lc.kepid,
                "prediction": 0,
                "confidence": 0.02,
                "period": None,
                "depth_ppm": None,
                "duration_hours": None,
                "candidates": [],
                "best_candidate": None
            }
            
        # 4. Vetting & Feature Extraction
        cand_rows = []
        for cand in candidates:
            vet_candidate(detrended_lc, cand)
            feats = extract_candidate_features(detrended_lc, cand, stellar_meta)
            cand_rows.append(feats)
            
        df_feats = pd.DataFrame(cand_rows)
        
        # 5. ML Scoring & Confidence Calibration
        if self.model is not None:
            probs = self.model.predict_proba(df_feats)
            raw_scores = self.model.predict_raw_proba(df_feats)
            for i, cand in enumerate(candidates):
                cand.ml_score = float(raw_scores[i])
                cand.calibrated_confidence = float(probs[i])
            threshold = self.model.threshold
        else:
            # Physics-based baseline heuristic if no ML model is loaded yet
            for cand in candidates:
                sde_sig = float(1.0 / (1.0 + np.exp(-0.4 * (cand.sde - 9.0))))
                cand.ml_score = cand.sde
                cand.calibrated_confidence = float(np.clip(sde_sig * cand.odd_even_consistency, 0.01, 0.99))
            threshold = 0.50
            
        # 6. Star-Level Decision Aggregation
        res = aggregate_star_candidates(candidates, threshold=threshold)
        res["star_id"] = lc.star_id
        res["kepid"] = lc.kepid
        res["candidates"] = [c.to_dict() for c in candidates]
        return res

    def analyze_file(self, filepath: str, stellar_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        lc = load_lightcurve(filepath)
        return self.analyze_lightcurve(lc, stellar_meta=stellar_meta)
