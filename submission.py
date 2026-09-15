# Competition-Compliant Submission Generator
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pipeline.models import StarDetectionResult

REQUIRED_COLUMNS = ["star_id", "prediction", "confidence", "period", "depth_ppm", "duration_hours"]

def results_to_submission_dataframe(results: List[StarDetectionResult]) -> pd.DataFrame:
    """Converts a list of StarDetectionResult objects to a standard submission DataFrame."""
    rows = []
    for r in results:
        rows.append({
            "star_id": r.star_id,
            "prediction": int(r.prediction),
            "confidence": round(float(r.confidence), 4),
            "period": round(float(r.period), 6) if (r.prediction == 1 and r.period is not None) else "",
            "depth_ppm": round(float(r.depth_ppm), 2) if (r.prediction == 1 and r.depth_ppm is not None) else "",
            "duration_hours": round(float(r.duration_hours), 4) if (r.prediction == 1 and r.duration_hours is not None) else ""
        })
    df = pd.DataFrame(rows)
    return df[REQUIRED_COLUMNS]

def save_submission_file(df: pd.DataFrame, output_path: str) -> None:
    """Saves DataFrame as a submission CSV and strictly verifies formatting."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    
    # Validation check
    df_check = pd.read_csv(output_path)
    for col in REQUIRED_COLUMNS:
        if col not in df_check.columns:
            raise ValueError(f"Missing required submission column: {col}")
            
    if not (df_check["confidence"].between(0.0, 1.0)).all():
        raise ValueError("Confidence values must be strictly between 0.0 and 1.0")
        
    if not set(df_check["prediction"].unique()).issubset({0, 1}):
        raise ValueError("Predictions must be binary (0 or 1)")
        
    print(f"Submission successfully written to {output_path} ({len(df_check)} stars).")
