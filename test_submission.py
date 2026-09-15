import pytest
import os
import pandas as pd
import numpy as np
from scripts.validate_submission import validate_submission_file

def test_submission_validation_valid(tmp_path):
    csv_path = str(tmp_path / "submission_test.csv")
    stars = [f"STAR_{i:04d}" for i in range(87)]
    df = pd.DataFrame({
        "star_id": stars,
        "prediction": [1 if i % 3 == 0 else 0 for i in range(87)],
        "confidence": np.linspace(0.05, 0.95, 87).round(4),
        "period": [15.2345 if i % 3 == 0 else np.nan for i in range(87)],
        "depth_ppm": [850.2 if i % 3 == 0 else np.nan for i in range(87)],
        "duration_hours": [4.125 if i % 3 == 0 else np.nan for i in range(87)],
    })
    df.to_csv(csv_path, index=False)
    assert validate_submission_file(csv_path) is True
