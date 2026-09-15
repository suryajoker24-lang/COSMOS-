import pytest
import os
import numpy as np
from src.data.lightcurve import load_lightcurve, LightCurve, parse_star_id

def test_parse_star_id():
    name, kepid = parse_star_id("data/train/KIC_10002867.parquet")
    assert "10002867" in name
    assert kepid == 10002867

def test_load_lightcurve():
    sample_file = "data/dev/KIC_5306984.parquet"
    if not os.path.exists(sample_file):
        pytest.skip("Dev sample file not found")
    lc = load_lightcurve(sample_file)
    assert isinstance(lc, LightCurve)
    assert len(lc.time) > 1000
    assert len(lc.flux) == len(lc.time)
    assert np.all(np.isfinite(lc.flux))
    assert lc.baseline_days > 100
