import pytest
import os
from src.pipeline import TransitDetectionPipeline

def test_pipeline_single_star():
    sample_file = "data/dev/KIC_5306984.parquet"
    if not os.path.exists(sample_file):
        pytest.skip("Dev sample file not found")
        
    pipeline = TransitDetectionPipeline(model_dir="models")
    res = pipeline.analyze_file(sample_file)
    assert "prediction" in res
    assert "confidence" in res
    assert 0.0 <= res["confidence"] <= 1.0
    assert res["prediction"] in [0, 1]
    if res["prediction"] == 1:
        assert res["period"] is not None and res["period"] > 0
        assert res["depth_ppm"] is not None and res["depth_ppm"] > 0
        assert res["duration_hours"] is not None and res["duration_hours"] > 0
