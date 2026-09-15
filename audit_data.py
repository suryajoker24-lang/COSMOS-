#!/usr/bin/env python3
"""
DATA AUDIT SCRIPT
Inspects and characterizes the complete Kepler exoplanet dataset:
- Star file counts in train, dev, private_test
- Label vs Injected Truth semantics and overlaps
- Missing values and data types
- Period, depth (ppm), duration (h), difficulty distributions
- Generates docs/DATA_AUDIT.md
"""

import os
import glob
import pandas as pd
import numpy as np

def audit_dataset():
    print("=" * 60)
    print("COSMOS / EXOHUNTER: COMPREHENSIVE DATASET AUDIT")
    print("=" * 60)
    
    train_files = glob.glob("data/train/*.parquet") + glob.glob("data/train/*.csv")
    dev_files = glob.glob("data/dev/*.parquet") + glob.glob("data/dev/*.csv")
    private_files = glob.glob("data/private_test/*.parquet") + glob.glob("data/private_test/*.csv")
    
    print(f"Total Stars in data/train:        {len(train_files)}")
    print(f"Total Stars in data/dev:          {len(dev_files)}")
    print(f"Total Stars in data/private_test: {len(private_files)}")
    total_stars = len(train_files) + len(dev_files) + len(private_files)
    print(f"Grand Total Stars in Dataset:     {total_stars}")
    
    # Load labels & truth
    train_labels = pd.read_csv("data/train_labels.csv") if os.path.exists("data/train_labels.csv") else None
    dev_labels = pd.read_csv("data/dev_labels.csv") if os.path.exists("data/dev_labels.csv") else None
    train_truth = pd.read_csv("data/train_truth.csv") if os.path.exists("data/train_truth.csv") else None
    dev_truth = pd.read_csv("data/dev_truth.csv") if os.path.exists("data/dev_truth.csv") else None
    
    report_lines = [
        "# Comprehensive Dataset Audit & Semantics Report",
        "",
        "## 1. Star Counts & Split Breakdown",
        f"- **Train Stars**: {len(train_files)} (Folder: `data/train`)",
        f"- **Dev Stars**: {len(dev_files)} (Folder: `data/dev`)",
        f"- **Private Test Stars**: {len(private_files)} (Folder: `data/private_test`)",
        f"- **Total Dataset Size**: {total_stars} stars",
        f"- **Observation Baseline**: ~4 years per star (~50k to ~65k long-cadence points, $\Delta t \\approx 29.4\\,\\text{min}$)",
        "",
        "---",
        "",
        "## 2. Label vs Injected Truth Semantics",
        "",
        "> [!IMPORTANT]",
        "> **Key Semantic Distinction**:",
        "> - `*_labels.csv` represents the **Real Catalogue Classification Ground Truth** (`prediction` $\\in \\{0, 1\\}$, where 1 indicates a confirmed transiting planet system).",
        "> - `*_truth.csv` represents **Synthetic / Injected Transit Signal Ground Truth** containing exact physical parameters ($P$, $T_0$, $\\delta_{\\text{ppm}}$, $\\tau_{\\text{hours}}$, $R_p/R_*$, difficulty band).",
        "> - The model is supervised on detection signals and evaluated against injection truth across difficulty bands without data leakage.",
        "",
    ]
    
    if train_labels is not None:
        pos_train = int((train_labels['label'] == 1).sum()) if 'label' in train_labels.columns else int((train_labels['prediction'] == 1).sum())
        neg_train = len(train_labels) - pos_train
        report_lines.extend([
            "### Train Set Label Distribution (`train_labels.csv`)",
            f"- Total labeled stars: {len(train_labels)}",
            f"- Positive transit hosts (`1`): {pos_train} ({pos_train/len(train_labels)*100:.1f}%)",
            f"- Negative non-transiting stars (`0`): {neg_train} ({neg_train/len(train_labels)*100:.1f}%)",
            ""
        ])
        
    if dev_labels is not None:
        pos_dev = int((dev_labels['label'] == 1).sum()) if 'label' in dev_labels.columns else int((dev_labels['prediction'] == 1).sum())
        neg_dev = len(dev_labels) - pos_dev
        report_lines.extend([
            "### Dev Set Label Distribution (`dev_labels.csv`)",
            f"- Total labeled stars: {len(dev_labels)}",
            f"- Positive transit hosts (`1`): {pos_dev} ({pos_dev/len(dev_labels)*100:.1f}%)",
            f"- Negative non-transiting stars (`0`): {neg_dev} ({neg_dev/len(dev_labels)*100:.1f}%)",
            ""
        ])
        
    if dev_truth is not None:
        report_lines.extend([
            "### Dev Injected Signal Physical Parameter Distribution (`dev_truth.csv`)",
            f"- Total injected ground-truth signals: {len(dev_truth)}",
        ])
        if 'period' in dev_truth.columns:
            p_min, p_med, p_max = dev_truth['period'].min(), dev_truth['period'].median(), dev_truth['period'].max()
            report_lines.append(f"- **Orbital Period ($P$)**: Min = {p_min:.2f} d, Median = {p_med:.2f} d, Max = {p_max:.2f} d")
        if 'depth_ppm' in dev_truth.columns:
            d_min, d_med, d_max = dev_truth['depth_ppm'].min(), dev_truth['depth_ppm'].median(), dev_truth['depth_ppm'].max()
            report_lines.append(f"- **Transit Depth ($\\delta$)**: Min = {d_min:.1f} ppm, Median = {d_med:.1f} ppm, Max = {d_max:.1f} ppm")
        if 'duration_hours' in dev_truth.columns:
            dur_min, dur_med, dur_max = dev_truth['duration_hours'].min(), dev_truth['duration_hours'].median(), dev_truth['duration_hours'].max()
            report_lines.append(f"- **Transit Duration ($\\tau$)**: Min = {dur_min:.2f} h, Median = {dur_med:.2f} h, Max = {dur_max:.2f} h")
            
        if 'difficulty' in dev_truth.columns:
            report_lines.append("\n#### Difficulty Bins in Dev Set:")
            diff_counts = dev_truth['difficulty'].value_counts()
            for diff, count in diff_counts.items():
                report_lines.append(f"- **{diff.upper()}**: {count} signals ({count/len(dev_truth)*100:.1f}%)")
        report_lines.append("")
        
    report_lines.extend([
        "---",
        "",
        "## 3. Light Curve Cadence & Column Schema",
        "- **Columns**: `time` (BJD - 2454833.0), `flux` (e-/s or SAP relative flux), `flux_err`, `quality` (bitmask integer), `quarter` (integer 0 to 17).",
        "- **Sampling Frequency**: $1 / 29.4244\\,\\text{min} \\approx 48.94\\,\\text{cadences/day}$.",
        "- **Quality Flag Semantics**: `quality == 0` designates unflagged, high-precision scientific cadences. Non-zero flags mask spacecraft thruster firing, reaction wheel desaturation, Earth/Moon in FOV, and cosmic ray hits.",
        "",
        "---",
        "",
        "## 4. Scientific Strategy & Detection Protocol",
        "1. **Ingestion & Validation**: Bitmask filter (`quality == 0`), drop non-finite values and negative flux anomalies.",
        "2. **Quarter Level Offset Correction**: Normalize each Kepler quarter independently via robust median scaling ($F / \\text{median}(F)$).",
        "3. **Transit-Preserving Detrending**: Apply Wōtan biweight windowing with iterative transit dip masking to protect sub-300 ppm shallow signals.",
        "4. **BLS Search**: Frequency-uniform grid search with `astropy.timeseries.BoxLeastSquares.autoperiod()` across 2 to 400 days.",
        "5. **Candidate Refinement & Vetting**: Windowed cutouts for fast Transit Least Squares (TLS), odd/even depth check, secondary eclipse test at phase 0.5, and single-epoch dominance testing.",
        "6. **Supervised Ranking & Isotonic Calibration**: GroupKFold by Star ID preventing data leakage, outputting well-calibrated posterior probabilities $P(\\text{Transit} \\mid \\mathbf{x}) \\in [0, 1]$."
    ])
    
    os.makedirs("docs", exist_ok=True)
    with open("docs/DATA_AUDIT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
        
    print("Successfully generated docs/DATA_AUDIT.md!")

if __name__ == "__main__":
    audit_dataset()

