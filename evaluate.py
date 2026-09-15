# Evaluate the candidate ranker on dev_pack and report metrics
import os
import sys
import time
import numpy as np
import pandas as pd
import json

sys.path.insert(0, os.path.abspath("."))

from pipeline import (
    load_raw_lightcurve,
    preprocess_lightcurve,
    detrend_lightcurve,
    search_candidates_bls,
    refine_candidate_tls,
    vet_candidate,
    extract_candidate_features,
    ExoHunterModel,
)

PROJECT_DIR = os.path.dirname(os.path.abspath("."))
DATA_DIR = os.path.join(PROJECT_DIR, "data", "raw")
DEV_DIR = os.path.join(DATA_DIR, "dev_pack", "dev")
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results", "evaluation")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Load dev truth
truth_path = os.path.join(DATA_DIR, "dev_pack", "dev_truth.csv")
df_truth = pd.read_csv(truth_path)
truth_set = set()
for _, row in df_truth.iterrows():
    kepid = int(row["kepid"])
    truth_set.add(kepid)

# Load dev labels for star metadata
labels_path = os.path.join(DATA_DIR, "dev_pack", "dev_labels.csv")
df_labels = pd.read_csv(labels_path)


def detect_alias(period: float, true_period: float) -> str:
    """Check if detected period is a harmonic/sub-harmonic alias of true period."""
    if period <= 0 or true_period <= 0:
        return "none"
    ratios = [
        (2.0, "2x"), (0.5, "1/2"), (3.0, "3x"), (1.0/3.0, "1/3"),
        (4.0, "4x"), (1.0/4.0, "1/4"), (1.5, "3/2"), (2.0/3.0, "2/3"),
    ]
    for ratio, alias_name in ratios:
        if abs(period - true_period * ratio) / true_period < 0.02:
            return alias_name
    if abs(period - true_period) / true_period < 0.02:
        return "1x"
    return "none"


def evaluate():
    print("=" * 60)
    print("Evaluating Pipeline on dev_pack")
    print("=" * 60)

    model_path = os.path.join(MODELS_DIR, "candidate_ranker.joblib")
    if os.path.exists(model_path):
        model = ExoHunterModel(model_path=model_path)
        print(f"Loaded trained model (threshold={model.threshold:.3f})")
    else:
        model = ExoHunterModel()
        print("Using physics-based baseline heuristic")

    star_files = sorted(glob.glob(os.path.join(DEV_DIR, "*.parquet")))
    print(f"Found {len(star_files)} dev stars")

    results = []
    t0 = time.time()
    n_pos_truth = 0
    n_detected = 0
    n_correct_period = 0
    n_correct_depth = 0
    alias_counts = {"1x": 0, "1/2": 0, "2x": 0, "3x": 0, "1/3": 0, "none": 0}

    for i, fpath in enumerate(star_files):
        star_id = os.path.splitext(os.path.basename(fpath))[0]
        kepid_str = star_id.replace("KIC_", "")
        try:
            kepid = int(kepid_str)
        except ValueError:
            continue

        has_truth = kepid in truth_set
        if has_truth:
            n_pos_truth += 1
            truth_row = df_truth[df_truth["kepid"] == kepid].iloc[0]
            true_period = float(truth_row["period_days"])
            true_depth = float(truth_row["depth_ppm"])
            true_duration = float(truth_row["duration_hours"])
        else:
            true_period = None
            true_depth = None
            true_duration = None

        try:
            r = process_star_end_to_end(
                fpath,
                model=model,
                use_gp=False,
                use_tls=True,
            )
        except Exception as e:
            print(f"  Error {star_id}: {e}")
            r = StarDetectionResult(star_id=star_id, prediction=0, confidence=0.01, status="ERROR")

        detected = r.prediction == 1
        if detected:
            n_detected += 1
            if true_period and r.period:
                alias = detect_alias(r.period, true_period)
                alias_counts[alias] = alias_counts.get(alias, 0) + 1
                if alias in ("1x", "1/2", "2x", "3x", "1/3"):
                    n_correct_period += 1
                if true_depth and r.depth_ppm:
                    depth_err = abs(r.depth_ppm - true_depth) / true_depth
                    if depth_err < 0.5:
                        n_correct_depth += 1

        results.append({
            "star_id": star_id,
            "kepid": kepid,
            "truth": 1 if has_truth else 0,
            "prediction": int(r.prediction),
            "confidence": round(float(r.confidence), 4),
            "period": round(float(r.period), 5) if r.period else None,
            "depth_ppm": round(float(r.depth_ppm), 1) if r.depth_ppm else None,
            "duration_hours": round(float(r.duration_hours), 3) if r.duration_hours else None,
        })

        if (i + 1) % 20 == 0 or i + 1 == len(star_files):
            print(f"  [{i+1}/{len(star_files)}] stars processed, {n_detected} detections so far ({n_pos_truth} truth positives)")

    elapsed = time.time() - t0

    # Compute metrics
    df_res = pd.DataFrame(results)
    y_true = df_res["truth"].values
    y_pred = df_res["prediction"].values
    confidences = df_res["confidence"].values

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    ap = average_precision_score(y_true, confidences)
    pr_auc = roc_auc_score(y_true, confidences)

    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS (dev_pack, {len(star_files)} stars)")
    print(f"{'='*60}")
    print(f"  Truth positives: {n_pos_truth}")
    print(f"  Detections: {n_detected}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print(f"  F1: {f1:.4f}")
    print(f"  PR-AUC: {pr_auc:.4f}")
    print(f"  Average Precision: {ap:.4f}")
    print(f"  Correct period (alias-included): {n_correct_period}/{n_pos_truth}")
    print(f"  Correct depth (<50% error): {n_correct_depth}/{n_pos_truth}")
    print(f"  Alias breakdown: {alias_counts}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/len(star_files):.2f}s per star)")

    # Save results
    df_res.to_csv(os.path.join(RESULTS_DIR, "predictions.csv"), index=False)

    metrics = {
        "evaluated": True,
        "mode": "REAL",
        "n_stars": len(star_files),
        "n_truth_positives": int(n_pos_truth),
        "n_detections": int(n_detected),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "pr_auc": round(float(pr_auc), 4),
        "average_precision": round(float(ap), 4),
        "correct_period": int(n_correct_period),
        "correct_depth": int(n_correct_depth),
        "alias_breakdown": {k: int(v) for k, v in alias_counts.items()},
        "elapsed_seconds": round(elapsed, 2),
        "seconds_per_star": round(elapsed / len(star_files), 3),
    }

    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nMetrics saved to {RESULTS_DIR}/metrics.json")
    print(f"Predictions saved to {RESULTS_DIR}/predictions.csv")

    return metrics


if __name__ == "__main__":
    from pipeline.model import process_star_end_to_end
    from pipeline.models import StarDetectionResult
    from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
    import glob

    evaluate()
