# Submission Validator Script
import sys
import os
import pandas as pd
import numpy as np

def validate_submission_file(filepath: str) -> bool:
    if not os.path.exists(filepath):
        print(f"ERROR: File does not exist: {filepath}")
        return False
        
    try:
        sub = pd.read_csv(filepath)
    except Exception as e:
        print(f"ERROR: Failed to parse CSV: {e}")
        return False
        
    required_cols = ["star_id", "prediction", "confidence", "period", "depth_ppm", "duration_hours"]
    if list(sub.columns) != required_cols:
        print(f"ERROR: Columns must be exactly {required_cols}, got {list(sub.columns)}")
        return False
        
    if len(sub) != 87:
        print(f"WARNING / CHECK: Expected 87 rows for private submission set, got {len(sub)} rows.")
        
    if sub["star_id"].nunique() != len(sub):
        print("ERROR: Duplicate star_id found in submission.")
        return False
        
    if not sub["star_id"].str.match(r"^STAR_\d{4}$").all():
        print("ERROR: star_id does not match required format STAR_XXXX.")
        return False
        
    if not sub["prediction"].isin([0, 1]).all():
        print("ERROR: prediction values must be strictly 0 or 1.")
        return False
        
    if not sub["confidence"].between(0.0, 1.0).all():
        print("ERROR: confidence must be between 0 and 1.")
        return False
        
    if sub["confidence"].nunique() <= 2:
        print("WARNING: confidence column has very few unique values (<3). Ranking score may be degraded.")
        
    pos_mask = sub["prediction"] == 1
    neg_mask = sub["prediction"] == 0
    
    pos = sub[pos_mask]
    for c in ["period", "depth_ppm", "duration_hours"]:
        if not pos[c].notna().all():
            print(f"ERROR: Characterization column '{c}' is missing for some positive (prediction=1) detections.")
            return False
            
    if (pos["period"] <= 0).any():
        print("ERROR: period must be positive for all detections.")
        return False
        
    neg = sub[neg_mask]
    for c in ["period", "depth_ppm", "duration_hours"]:
        if neg[c].notna().any():
            print(f"ERROR: Non-detections (prediction=0) must have empty '{c}' field, found non-null values.")
            return False
            
    print(f"\nVALIDATION SUCCESSFUL!")
    print(f"Total stars: {len(sub)}")
    print(f"Detections (prediction=1): {len(pos)}")
    print(f"Non-detections (prediction=0): {len(neg)}")
    print(f"Confidence range: [{sub['confidence'].min():.4f}, {sub['confidence'].max():.4f}] ({sub['confidence'].nunique()} unique values)")
    print(f"Submission file '{filepath}' is 100% compliant with competition specifications.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_submission.py <path_to_submission.csv>")
        sys.exit(1)
        
    path = sys.argv[1]
    ok = validate_submission_file(path)
    sys.exit(0 if ok else 1)
