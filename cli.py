# CLI Entrypoint for Exoplanet Detection System
import os
import sys
import argparse
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from pipeline.model import process_star_end_to_end
from pipeline.submission import results_to_submission_dataframe, save_submission_file
from pipeline.models import StarDetectionResult, TransitCandidate
from pipeline import ExoHunterModel

def cmd_train(args):
    import subprocess
    cmd = [sys.executable, "scripts/train.py"]
    subprocess.run(cmd, check=True)

def cmd_evaluate(args):
    import subprocess
    cmd = [sys.executable, "scripts/evaluate.py", "--split", args.split, "--workers", str(args.workers)]
    subprocess.run(cmd, check=True)

def cmd_analyze(args):
    if not os.path.exists(args.input):
        print(f"Error: file not found {args.input}")
        sys.exit(1)

    model_path = os.path.join("models", "candidate_ranker.joblib")
    model = None
    if os.path.exists(model_path):
        model = ExoHunterModel(model_path=model_path)

    result = process_star_end_to_end(
        args.input,
        model=model,
        use_gp=False,
        use_tls=True,
        detrend_window=args.detrend_window,
    )

    print("\n" + "=" * 50)
    print(f"ANALYSIS REPORT FOR: {result.star_id}")
    print("=" * 50)
    print(f"Prediction:         {'PLANET CANDIDATE DETECTED (1)' if result.prediction == 1 else 'NO PLANET DETECTED (0)'}")
    print(f"Calibrated Conf:    {result.confidence:.4f}")
    if result.prediction == 1 and result.period:
        print(f"Orbital Period:     {result.period:.5f} days")
        print(f"Transit Depth:      {result.depth_ppm:.1f} ppm")
        print(f"Transit Duration:   {result.duration_hours:.3f} hours")
    print(f"Candidates Tested:  {len(result.all_candidates)}")
    if result.best_candidate:
        best = result.best_candidate
        print(f"Top SDE:            {best.sde:.2f}")
        print(f"Top SNR:            {best.snr:.2f}")
        print(f"Odd/Even Mismatch:  {best.odd_even_mismatch:.3f}")
        print(f"Secondary Eclipse:  {best.secondary_eclipse_score:.2f}")
    print("=" * 50 + "\n")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))

def cmd_batch(args):
    if not os.path.exists(args.input):
        print(f"Error: directory not found {args.input}")
        sys.exit(1)

    model_path = os.path.join("models", "candidate_ranker.joblib")
    model = None
    if os.path.exists(model_path):
        model = ExoHunterModel(model_path=model_path)

    paths = sorted([os.path.join(args.input, f) for f in os.listdir(args.input) if f.endswith('.parquet')])
    if not paths:
        paths = sorted([os.path.join(args.input, f) for f in os.listdir(args.input) if f.endswith('.csv')])
        if not paths:
            print(f"No parquet/csv files in {args.input}")
            sys.exit(1)

    print(f"Batch analyzing {len(paths)} stars from {args.input}...")

    results = []
    for i, p in enumerate(paths):
        try:
            r = process_star_end_to_end(p, model=model, use_gp=False, use_tls=True)
            results.append(r)
            print(f"  [{i+1}/{len(paths)}] {r.star_id}: pred={r.prediction}, conf={r.confidence:.4f}")
        except Exception as e:
            print(f"  [{i+1}/{len(paths)}] {os.path.basename(p)}: ERROR {e}")
            results.append(StarDetectionResult(
                star_id=os.path.splitext(os.path.basename(p))[0],
                prediction=0, confidence=0.01, status="ERROR"
            ))

    df = results_to_submission_dataframe(results)
    df.to_csv(args.output, index=False)
    print(f"\nBatch results saved to {args.output} ({len(df)} stars)")

def cmd_submission(args):
    if not os.path.exists(args.input):
        print(f"Error: directory not found {args.input}")
        sys.exit(1)

    model_path = os.path.join("models", "candidate_ranker.joblib")
    model = None
    if os.path.exists(model_path):
        model = ExoHunterModel(model_path=model_path)

    paths = sorted([os.path.join(args.input, f) for f in os.listdir(args.input) if f.endswith('.parquet')])
    if not paths:
        paths = sorted([os.path.join(args.input, f) for f in os.listdir(args.input) if f.endswith('.csv')])
        if not paths:
            print(f"No parquet/csv files in {args.input}")
            sys.exit(1)

    print(f"Generating submission for {len(paths)} stars from {args.input}...")

    results = []
    t0 = __import__('time').time()
    for i, p in enumerate(paths):
        try:
            r = process_star_end_to_end(p, model=model, use_gp=False, use_tls=True)
            results.append(r)
        except Exception as e:
            print(f"  Error {os.path.basename(p)}: {e}")
            results.append(StarDetectionResult(
                star_id=os.path.splitext(os.path.basename(p))[0],
                prediction=0, confidence=0.01, status="ERROR"
            ))

        if (i + 1) % 10 == 0 or i + 1 == len(paths):
            elapsed = __import__('time').time() - t0
            print(f"  [{i+1}/{len(paths)}] Progress: {elapsed:.1f}s elapsed")

    df = results_to_submission_dataframe(results)
    output_path = os.path.join(os.path.dirname(args.output) or ".", os.path.basename(args.output))
    df.to_csv(output_path, index=False)

    n_pos = (df["prediction"] == 1).sum()
    n_neg = (df["prediction"] == 0).sum()
    print(f"\nSubmission saved to: {output_path}")
    print(f"Total stars: {len(df)}, Detections: {n_pos}, Non-detections: {n_neg}")

def cmd_validate(args):
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"Error: file not found {filepath}")
        sys.exit(1)

    df = pd.read_csv(filepath)
    required = ["star_id", "prediction", "confidence", "period", "depth_ppm", "duration_hours"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"FAIL: Missing columns: {missing}")
        sys.exit(1)

    # Check constraints
    errors = []
    if not df["prediction"].isin([0, 1]).all():
        errors.append("Predictions must be 0 or 1")
    if not df["confidence"].between(0, 1).all():
        errors.append("Confidence must be between 0 and 1")
    if len(df) != 87:
        errors.append(f"Expected 87 stars, got {len(df)}")

    # Check NaN handling for prediction=0
    for _, row in df.iterrows():
        if row["prediction"] == 0:
            for col in ["period", "depth_ppm", "duration_hours"]:
                if pd.notna(row[col]) and row[col] != "":
                    pass  # Allow empty/NaN for non-detections

    if errors:
        print(f"FAIL: {', '.join(errors)}")
        sys.exit(1)

    n_pos = (df["prediction"] == 1).sum()
    print(f"OK: {len(df)} stars, {n_pos} detections, {len(df)-n_pos} non-detections")
    print(f"Columns: {list(df.columns)}")
    print(f"Confidence range: [{df['confidence'].min():.4f}, {df['confidence'].max():.4f}]")

def main():
    parser = argparse.ArgumentParser(description="AI Exoplanet Detection CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train
    p_train = subparsers.add_parser("train", help="Train candidate classifier")
    p_train.set_defaults(func=cmd_train)

    # Evaluate
    p_eval = subparsers.add_parser("evaluate", help="Evaluate model on dev or train split")
    p_eval.add_argument("--split", type=str, default="dev", choices=["dev", "train"])
    p_eval.add_argument("--workers", type=int, default=min(8, max(1, (os.cpu_count() or 4) - 1)))
    p_eval.set_defaults(func=cmd_evaluate)

    # Analyze
    p_ana = subparsers.add_parser("analyze", help="Analyze a single light curve parquet file")
    p_ana.add_argument("--input", type=str, required=True, help="Path to lightcurve parquet")
    p_ana.add_argument("--detrend-window", type=float, default=0.75, help="Detrending window length in days")
    p_ana.add_argument("--json", action="store_true", help="Output full JSON result")
    p_ana.set_defaults(func=cmd_analyze)

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch analyze a directory of light curves")
    p_batch.add_argument("--input", type=str, required=True, help="Directory containing parquet files")
    p_batch.add_argument("--output", type=str, default="batch_results.csv", help="Output CSV path")
    p_batch.set_defaults(func=cmd_batch)

    # Submission
    p_sub = subparsers.add_parser("submission", help="Generate competition submission CSV")
    p_sub.add_argument("--input", type=str, required=True, help="Path to private set directory")
    p_sub.add_argument("--output", type=str, default="submission_antigravity.csv", help="Output submission CSV path")
    p_sub.set_defaults(func=cmd_submission)

    # Validate
    p_val = subparsers.add_parser("validate", help="Validate submission CSV against rules")
    p_val.add_argument("file", type=str, help="Submission CSV path")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
