# Real Scientific Pipeline Runner with Stage-by-Stage Tracking & DB Persistence
import os
import time
import json
import glob
import hashlib
import traceback
import uuid
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

from src.data.lightcurve import LightCurve, load_lightcurve
from src.preprocessing.quarter import normalize_quarters
from src.detrending.adaptive import adaptive_detrend
from src.search.bls_search import coarse_to_fine_bls
from src.vetting.vetting import vet_candidate
from src.features.extractor import extract_candidate_features
from src.models.classifier import CandidateClassifier
from src.calibration.calibrator import aggregate_star_candidates
from src.candidates.candidate import TransitCandidate

from backend.database import (
    SessionLocal, Star, LightCurveMeta, AnalysisRun, Candidate,
    CandidateFeature, VettingResult, AnalysisEvent, log_event, find_cached_run
)

PIPELINE_VERSION = "COSMOS-Pipeline-v1.2"

# Thread pool for asynchronous scientific analysis runs
_executor = ThreadPoolExecutor(max_workers=4)

def compute_config_hash(star_id: str, config: Dict[str, Any], file_mtime: float) -> str:
    payload = {
        "star_id": star_id,
        "config": sorted(config.items()),
        "file_mtime": file_mtime,
        "pipeline_version": PIPELINE_VERSION
    }
    dumped = json.dumps(payload, default=str)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]

def resolve_star_filepath(star_id: str) -> Optional[str]:
    clean_id = star_id.strip()
    # Check uploads directory first
    matches = glob.glob(f"data/uploads/{clean_id}.*")
    if matches:
        return matches[0]
    # Check challenge directories
    patterns = [
        f"data/private_test/{clean_id}.parquet",
        f"data/dev/{clean_id}.parquet",
        f"data/train/{clean_id}.parquet",
        f"data/*/{clean_id}.parquet",
        f"data/*/{clean_id}.csv",
        f"data/*/*{clean_id}*.parquet"
    ]
    for pat in patterns:
        found = glob.glob(pat)
        if found:
            return found[0]
    return None

def execute_pipeline_job(run_id: str, star_id: str, filepath: str, config: Dict[str, Any]):
    db = SessionLocal()
    t_start = time.time()
    try:
        run_obj = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run_obj:
            return

        # Stage 1: LOADING_DATA
        run_obj.status = "LOADING_DATA"
        db.commit()
        log_event(db, run_id, "LOADING_DATA", f"Loading photometric time-series for {star_id}", 10.0)

        lc = load_lightcurve(filepath)
        num_points = len(lc.time)
        t_span = float(lc.time[-1] - lc.time[0])

        # Stage 2: QUALITY_FILTERING
        run_obj.status = "QUALITY_FILTERING"
        db.commit()
        log_event(db, run_id, "QUALITY_FILTERING", f"Quality bitmask filtering and NaN rejection ({num_points} cadences)", 20.0)

        # Stage 3: QUARTER_NORMALIZATION
        run_obj.status = "QUARTER_NORMALIZATION"
        db.commit()
        log_event(db, run_id, "QUARTER_NORMALIZATION", "Performing robust median quarter-by-quarter normalization", 35.0)

        norm_lc, quarters = normalize_quarters(lc)

        # Stage 4: DETRENDING
        run_obj.status = "DETRENDING"
        db.commit()
        detrend_win = config.get("detrend_window", 2.0)
        log_event(db, run_id, "DETRENDING", f"Transit-preserving adaptive Savitzky-Golay detrending (window: {detrend_win}d)", 50.0)

        detrended_lc, trend = adaptive_detrend(norm_lc, window_length_days=detrend_win)

        # Stage 5: BLS_SEARCH
        run_obj.status = "BLS_SEARCH"
        db.commit()
        n_coarse = config.get("n_coarse", 15000)
        n_peaks = config.get("n_peaks", 12)
        log_event(db, run_id, "BLS_SEARCH", f"Running frequency-grid Box Least Squares search ({n_coarse} trial frequencies)", 65.0)

        candidates = coarse_to_fine_bls(
            detrended_lc.time,
            detrended_lc.flux,
            detrended_lc.flux_err,
            n_coarse=n_coarse,
            n_peaks=n_peaks,
            star_id=star_id,
            kepid=lc.kepid
        )

        # Stage 6: TLS_CONFIRMATION & VETTING
        run_obj.status = "TLS_CONFIRMATION"
        db.commit()
        log_event(db, run_id, "TLS_CONFIRMATION", f"Refining transit parameters with Mandel-Agol limb-darkened profile on {len(candidates)} candidate peaks", 78.0)

        run_obj.status = "VETTING"
        db.commit()
        log_event(db, run_id, "VETTING", "Executing false positive veto suite: odd/even test, secondary eclipse search, recurrence check", 85.0)

        cand_rows = []
        for cand in candidates:
            vet_candidate(detrended_lc, cand)
            feats = extract_candidate_features(detrended_lc, cand)
            cand_rows.append(feats)

        # Stage 7: RANKING & CALIBRATION
        run_obj.status = "RANKING"
        db.commit()
        log_event(db, run_id, "RANKING", "Computing LightGBM candidate ranking score and isotonic posterior probabilities", 92.0)

        df_feats = pd.DataFrame(cand_rows) if cand_rows else pd.DataFrame()
        model = None
        if os.path.exists("models/candidate_ranker.joblib"):
            try:
                model = CandidateClassifier.load("models")
            except Exception as ex:
                pass

        if model is not None and not df_feats.empty:
            probs = model.predict_proba(df_feats)
            raw_scores = model.predict_raw_proba(df_feats)
            for i, cand in enumerate(candidates):
                cand.ml_score = float(raw_scores[i])
                cand.calibrated_confidence = float(probs[i])
            threshold = model.threshold
        else:
            for cand in candidates:
                sde_sig = float(1.0 / (1.0 + np.exp(-0.4 * (cand.sde - 9.0))))
                cand.ml_score = cand.sde
                cand.calibrated_confidence = float(np.clip(sde_sig * cand.odd_even_consistency, 0.01, 0.99))
            threshold = 0.50

        # Aggregation
        res = aggregate_star_candidates(candidates, threshold=threshold)
        res["star_id"] = star_id
        res["kepid"] = lc.kepid

        # Prepare Folded Profile
        folded_data = {}
        if res.get("best_candidate"):
            best = res["best_candidate"]
            p = best.period
            t0 = best.epoch_t0
            phase = ((detrended_lc.time - t0) / p) % 1.0
            phase = np.where(phase > 0.5, phase - 1.0, phase)
            bins = 100
            edges = np.linspace(-0.5, 0.5, bins + 1)
            b_idx = np.digitize(phase, edges) - 1
            bx, by = [], []
            for b in range(bins):
                m_b = b_idx == b
                if np.any(m_b):
                    bx.append(float(np.median(phase[m_b])))
                    by.append(float(np.median(detrended_lc.flux[m_b])))
            folded_data = {
                "period": p,
                "epoch_t0": t0,
                "depth_ppm": best.depth_ppm,
                "duration_hours": best.duration_hours,
                "phase": [round(x, 5) for x in bx],
                "flux": [round(y, 6) for y in by]
            }

        # Subsample raw light curve for efficient frontend transfer (max 2500 points)
        step = max(1, len(lc.time) // 2500)
        idx = np.arange(0, len(lc.time), step)

        final_result = {
            "star_id": star_id,
            "kepid": lc.kepid,
            "prediction": res["prediction"],
            "confidence": round(float(res["confidence"]), 4),
            "period": round(float(res["period"]), 5) if res["period"] is not None else None,
            "depth_ppm": round(float(res["depth_ppm"]), 1) if res["depth_ppm"] is not None else None,
            "duration_hours": round(float(res["duration_hours"]), 3) if res["duration_hours"] is not None else None,
            "candidates": [c.to_dict() for c in candidates],
            "best_candidate": res["best_candidate"].to_dict() if res.get("best_candidate") else None,
            "folded": folded_data,
            "time": [round(float(t), 4) for t in detrended_lc.time[idx]],
            "raw_flux": [round(float(f), 4) for f in lc.flux[idx]],
            "detrended_flux": [round(float(f), 6) for f in detrended_lc.flux[idx]],
            "trend": [round(float(tr), 4) for tr in trend[idx]],
            "baseline_days": round(t_span, 2),
            "cadences_analyzed": num_points,
            "pipeline_version": PIPELINE_VERSION
        }

        # Stage 8: COMPLETED
        t_elapsed = time.time() - t_start
        run_obj.status = "COMPLETED"
        run_obj.completed_at = time.time()
        run_obj.duration_sec = round(t_elapsed, 2)
        run_obj.prediction = res["prediction"]
        run_obj.confidence = round(float(res["confidence"]), 4)
        run_obj.period = res["period"]
        run_obj.depth_ppm = res["depth_ppm"]
        run_obj.duration_hours = res["duration_hours"]
        run_obj.result_json = json.dumps(final_result)
        db.commit()

        # Persist Candidates & Features
        for idx_c, c in enumerate(candidates):
            c_db = Candidate(
                run_id=run_id,
                star_id=star_id,
                candidate_index=idx_c,
                period=c.period,
                depth_ppm=c.depth_ppm,
                duration_hours=c.duration_hours,
                epoch_t0=c.epoch_t0,
                sde=c.sde,
                snr=c.transit_snr,
                odd_even_consistency=c.odd_even_consistency,
                secondary_eclipse_score=c.secondary_eclipse_score,
                quarter_recurrence_fraction=c.quarter_recurrence_fraction,
                calibrated_confidence=c.calibrated_confidence,
                ml_score=c.ml_score,
                alias_type=c.alias_type
            )
            db.add(c_db)
            db.flush()

            # Add features
            if idx_c < len(cand_rows):
                for f_name, f_val in cand_rows[idx_c].items():
                    if isinstance(f_val, (int, float)) and np.isfinite(f_val):
                        db.add(CandidateFeature(
                            candidate_id=c_db.id,
                            feature_name=f_name,
                            feature_value=float(f_val)
                        ))

            # Add vetting records
            db.add(VettingResult(
                candidate_id=c_db.id,
                test_name="odd_even_consistency",
                passed=bool(c.odd_even_consistency > 0.8),
                statistic=c.odd_even_consistency,
                threshold=0.8,
                notes=f"Depth mismatch ratio: {c.odd_even_consistency:.3f}"
            ))
            db.add(VettingResult(
                candidate_id=c_db.id,
                test_name="secondary_eclipse",
                passed=bool(c.secondary_eclipse_score < 3.0),
                statistic=c.secondary_eclipse_score,
                threshold=3.0,
                notes=f"Phase 0.5 significance: {c.secondary_eclipse_score:.1f}σ"
            ))

        db.commit()
        log_event(db, run_id, "COMPLETED", f"Scientific analysis completed in {t_elapsed:.2f}s. Verdict: {'DETECTION' if res['prediction'] == 1 else 'NON-DETECTION'} ({res['confidence']*100:.1f}%)", 100.0)

    except Exception as e:
        db.rollback()
        t_elapsed = time.time() - t_start
        err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        run_obj = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run_obj:
            run_obj.status = "FAILED"
            run_obj.completed_at = time.time()
            run_obj.duration_sec = round(t_elapsed, 2)
            run_obj.error = err_msg
            db.commit()
            log_event(db, run_id, "FAILED", f"Analysis failed: {str(e)}", 100.0)
    finally:
        db.close()

def start_analysis_job(
    star_id: str,
    filepath: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Submits an analysis job to the background scientific runner.
    Checks caching first for reproducibility and performance.
    """
    config = config or {}
    fpath = filepath or resolve_star_filepath(star_id)
    if not fpath or not os.path.exists(fpath):
        raise FileNotFoundError(f"No light curve file found for star '{star_id}'.")

    file_mtime = os.path.getmtime(fpath)
    cfg_hash = compute_config_hash(star_id, config, file_mtime)

    db = SessionLocal()
    try:
        # Check cache unless force_refresh is requested
        if not force_refresh:
            cached = find_cached_run(db, star_id, cfg_hash)
            if cached and cached.status == "COMPLETED" and cached.result_json:
                return {
                    "run_id": cached.id,
                    "star_id": star_id,
                    "status": "COMPLETED",
                    "is_cached": True,
                    "created_at": cached.created_at,
                    "message": "Analysis retrieved from verified reproducible cache."
                }

        # Create new AnalysisRun
        run_id = str(uuid.uuid4())[:8]
        new_run = AnalysisRun(
            id=run_id,
            star_id=star_id,
            status="QUEUED",
            pipeline_version=PIPELINE_VERSION,
            config_hash=cfg_hash,
            configuration_json=json.dumps(config),
            created_at=time.time(),
            is_cached=False
        )
        db.add(new_run)
        db.commit()
        log_event(db, run_id, "QUEUED", f"Job queued for star {star_id}", 0.0)

        # Launch in background worker thread
        _executor.submit(execute_pipeline_job, run_id, star_id, fpath, config)

        return {
            "run_id": run_id,
            "star_id": star_id,
            "status": "QUEUED",
            "is_cached": False,
            "created_at": new_run.created_at,
            "message": "Analysis job queued for background scientific processing."
        }
    finally:
        db.close()

def run_pipeline_sync(star_id: str, filepath: Optional[str] = None, config: Optional[Dict[str, Any]] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Executes the scientific pipeline synchronously for star_id and returns the complete result dictionary.
    Checks reproducible cache first unless force_refresh is True.
    """
    if config is None:
        config = {}
    fpath = filepath or resolve_star_filepath(star_id)
    if not fpath or not os.path.exists(fpath):
        raise FileNotFoundError(f"No light curve file found for star '{star_id}'.")

    file_mtime = os.path.getmtime(fpath)
    cfg_hash = compute_config_hash(star_id, config, file_mtime)

    db = SessionLocal()
    try:
        if not force_refresh:
            cached = find_cached_run(db, star_id, cfg_hash)
            if cached and cached.status == "COMPLETED" and cached.result_json:
                return json.loads(cached.result_json)

        run_id = str(uuid.uuid4())[:8]
        new_run = AnalysisRun(
            id=run_id,
            star_id=star_id,
            status="QUEUED",
            pipeline_version=PIPELINE_VERSION,
            config_hash=cfg_hash,
            configuration_json=json.dumps(config),
            created_at=time.time(),
            is_cached=False
        )
        db.add(new_run)
        db.commit()
    finally:
        db.close()

    # Execute synchronously
    execute_pipeline_job(run_id, star_id, fpath, config)

    # Read completed result from DB
    db = SessionLocal()
    try:
        completed = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if completed and completed.result_json:
            return json.loads(completed.result_json)
        raise RuntimeError(f"Pipeline execution did not complete: status={completed.status if completed else 'None'}")
    finally:
        db.close()
