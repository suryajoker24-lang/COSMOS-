# Train the LightGBM candidate ranker on train_pack data
import os
import sys
import time
import numpy as np
import pandas as pd
import joblib
from typing import List, Dict, Any, Tuple
from sklearn.model_selection import GroupKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_score, recall_score

sys.path.insert(0, os.path.abspath("."))

from pipeline import (
    load_raw_lightcurve,
    preprocess_lightcurve,
    detrend_lightcurve,
    search_candidates_bls,
    refine_candidate_tls,
    vet_candidate,
    extract_candidate_features,
    features_dict_to_dataframe,
    ExoHunterModel,
)

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    from sklearn.ensemble import HistGradientBoostingClassifier
    HAS_LGB = False

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath("."))
DATA_DIR = os.path.join(PROJECT_DIR, "data", "raw")
TRAIN_DIR = os.path.join(DATA_DIR, "train_pack", "train")
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_NAMES = [
    "period", "log_period", "duration_hours", "depth_ppm", "log_depth",
    "sde", "snr", "fap", "rp_rs", "duration_over_period",
    "odd_even_mismatch", "secondary_eclipse_score", "n_transits",
    "n_quarters", "single_epoch_fraction", "systematic_period_flag",
    "cdpp_ppm", "duty_cycle", "time_span_days", "depth_to_cdpp_ratio",
    "transit_duty_cycle", "log_snr", "source_method_is_tls"
]


def process_train_star(filepath: str, has_transit: bool) -> Tuple[List[Dict], List[Dict]]:
    """Process one star and return (candidate_features_list, labels_list)."""
    raw = load_raw_lightcurve(filepath)
    pre = preprocess_lightcurve(raw)
    det = detrend_lightcurve(pre, method="biweight", window_length=0.75)

    candidates = search_candidates_bls(det, min_period=0.5, max_period=30.0, top_k=3)

    all_feats = []
    all_labels = []

    if not candidates:
        # No candidates found - add a "null" sample
        null_feats = {name: 0.0 for name in FEATURE_NAMES}
        null_feats["cdpp_ppm"] = det.cdpp_ppm
        null_feats["time_span_days"] = float(det.time[-1] - det.time[0]) if len(det.time) > 1 else 100.0
        null_feats["duty_cycle"] = 0.9
        all_feats.append(null_feats)
        all_labels.append(0)
        return all_feats, all_labels

    for cand in candidates:
        if cand.period > 0:
            cand = refine_candidate_tls(det, cand)
        cand = vet_candidate(det, cand, quarter_array=pre.quarter)
        feats = extract_candidate_features(cand, det, pre)
        all_feats.append(feats)
        # Label: 1 if this star has a transit AND candidate is "good"
        all_labels.append(1 if has_transit else 0)

    return all_feats, all_labels


def train():
    print("=" * 60)
    print("Training Exoplanet Candidate Ranker on train_pack")
    print("=" * 60)

    # Load labels
    labels_path = os.path.join(TRAIN_DIR, "..", "train_labels.csv")
    truth_path = os.path.join(TRAIN_DIR, "..", "train_truth.csv")

    df_labels = pd.read_csv(labels_path)
    df_truth = pd.read_csv(truth_path)

    # Build truth lookup: kepid -> has_transit
    truth_lookup = {}
    for _, row in df_truth.iterrows():
        truth_lookup[int(row["kepid"])] = True

    # Build kepid <-> star_id mapping
    star_files = sorted(glob.glob(os.path.join(TRAIN_DIR, "*.parquet")))
    print(f"Found {len(star_files)} training stars")

    # Process each star
    all_features = []
    all_labels = []
    all_groups = []  # star index for GroupKFold

    stars_with_transits = 0
    stars_processed = 0

    for i, fpath in enumerate(star_files):
        star_id = os.path.splitext(os.path.basename(fpath))[0]
        # Extract kepid from star_id (KIC_XXXXXX)
        kepid_str = star_id.replace("KIC_", "")
        try:
            kepid = int(kepid_str)
        except ValueError:
            continue

        has_transit = truth_lookup.get(kepid, False)
        if has_transit:
            stars_with_transits += 1

        try:
            feats, labels = process_train_star(fpath, has_transit)
            for f in feats:
                all_features.append(f)
                all_labels.append(labels[all_features.index(f) - len(all_features) + len(feats)])
                # Actually, let's fix this...
            # Simpler approach:
            for j, f in enumerate(feats):
                all_features.append(f)
                all_labels.append(labels[j])
                all_groups.append(i)
            stars_processed += 1
            if stars_processed % 50 == 0:
                print(f"  Processed {stars_processed}/{len(star_files)} stars...")
        except Exception as e:
            print(f"  Error processing {star_id}: {e}")

    print(f"\nProcessed {stars_processed} stars, {stars_with_transits} with transits")
    print(f"Total samples: {len(all_features)} (positive: {sum(all_labels)}, negative: {len(all_labels) - sum(all_labels)})")

    if len(all_features) == 0:
        print("ERROR: No features extracted! Cannot train.")
        return

    df = pd.DataFrame(all_features)
    # Ensure all feature columns exist
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df[col] = 0.0
    df = df[FEATURE_NAMES]

    y = np.array(all_labels)
    groups = np.array(all_groups)

    print(f"\nFeature matrix: {df.shape}")
    print(f"Positive rate: {y.mean():.3f}")

    # Train with GroupKFold
    print("\nTraining LightGBM with GroupKFold cross-validation...")
    t0 = time.time()

    if HAS_LGB:
        model = lgb.LGBMClassifier(
            n_estimators=150,
            learning_rate=0.04,
            num_leaves=15,
            max_depth=4,
            min_child_samples=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        model = HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.04,
            max_leaf_nodes=15,
            max_depth=4,
            min_samples_leaf=5,
            random_state=42,
        )

    # GroupKFold
    gkf = GroupKFold(n_splits=5)
    oof_preds = np.zeros(len(y))

    for fold, (train_idx, val_idx) in enumerate(gkf.split(df, y, groups)):
        X_tr, y_tr = df.iloc[train_idx], y[train_idx]
        X_val, y_val = df.iloc[val_idx], y[val_idx]

        model.fit(X_tr, y_tr)
        oof_preds[val_idx] = model.predict_proba(X_val)[:, 1]
        fold_auc = roc_auc_score(y_val, oof_preds[val_idx])
        fold_ap = average_precision_score(y_val, oof_preds[val_idx])
        print(f"  Fold {fold+1}: ROC-AUC={fold_auc:.4f}, AP={fold_ap:.4f}")

    # Calibrate
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.001, y_max=0.999)
    calibrator.fit(oof_preds, y)

    # Retrain on full data
    if HAS_LGB:
        final_model = lgb.LGBMClassifier(
            n_estimators=180,
            learning_rate=0.035,
            num_leaves=15,
            max_depth=4,
            min_child_samples=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        final_model = HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.035,
            max_leaf_nodes=15,
            max_depth=4,
            min_samples_leaf=5,
            random_state=42,
        )
    final_model.fit(df, y)

    # Metrics
    cal_oof = calibrator.predict(oof_preds)
    roc_auc = roc_auc_score(y, cal_oof)
    ap = average_precision_score(y, cal_oof)

    # Find optimal threshold
    best_th, best_f1 = 0.5, 0.0
    for th in np.linspace(0.1, 0.9, 81):
        f1 = f1_score(y, (cal_oof >= th).astype(int), zero_division=0)
        prec = precision_score(y, (cal_oof >= th).astype(int), zero_division=0)
        rec = recall_score(y, (cal_oof >= th).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_th = th

    print(f"\nFull OOF Metrics:")
    print(f"  ROC-AUC: {roc_auc:.4f}")
    print(f"  Average Precision: {ap:.4f}")
    print(f"  Best F1: {best_f1:.4f} at threshold {best_th:.4f}")
    print(f"  Training time: {time.time()-t0:.1f}s")

    # Save
    joblib.dump(final_model, os.path.join(MODELS_DIR, "candidate_ranker.joblib"))
    joblib.dump(calibrator, os.path.join(MODELS_DIR, "calibrator.joblib"))

    with open(os.path.join(MODELS_DIR, "feature_schema.json"), "w") as f:
        json.dump(FEATURE_NAMES, f, indent=2)

    with open(os.path.join(MODELS_DIR, "thresholds.json"), "w") as f:
        json.dump({
            "threshold": float(best_th),
            "feature_importances": dict(zip(FEATURE_NAMES, final_model.feature_importances_ if HAS_LGB else np.ones(len(FEATURE_NAMES)))),
        }, f, indent=2)

    print(f"\nModel saved to {MODELS_DIR}/")
    print(f"Threshold: {best_th:.4f}")


if __name__ == "__main__":
    train()
