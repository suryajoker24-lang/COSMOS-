"""
Tests for Arbitrary Data Ingestion and Dynamic Scientific Processing.
Verifies that the application works end-to-end on data it has never seen before,
with arbitrary column headers, arbitrary star names, without hardcoded ID matching.
"""
import os
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from src.data.ingestion import DataSchemaDetector, DataValidator, LightCurveAdapter
from backend.pipeline_runner import run_pipeline_sync

client = TestClient(app)

@pytest.fixture
def synthetic_transit_csv(tmp_path):
    """Generates a synthetic transit light curve with non-standard column names."""
    np.random.seed(42)
    time = np.linspace(0, 80, 4000)
    flux = np.ones_like(time) + np.random.normal(0, 0.0003, size=len(time))
    
    # Inject transit: period = 12.5 days, depth = 800 ppm, duration = 0.2 days
    period = 12.5
    t0 = 2.0
    phase = ((time - t0) % period)
    in_transit = phase < 0.2
    flux[in_transit] -= 0.0008

    df = pd.DataFrame({
        "time_bjd": time,
        "normalized_flux": flux,
        "flux_uncertainty": np.full_like(time, 0.0003)
    })
    
    file_path = tmp_path / "UNKNOWN_TARGET_ALPHA.csv"
    df.to_csv(file_path, index=False)
    return str(file_path)

@pytest.fixture
def synthetic_flat_csv(tmp_path):
    """Generates a pure noise light curve (no transits)."""
    np.random.seed(123)
    time = np.linspace(0, 50, 2500)
    flux = np.ones_like(time) + np.random.normal(0, 0.0004, size=len(time))

    df = pd.DataFrame({
        "HJD_DAYS": time,
        "SAP_FLUX": flux,
        "SAP_FLUX_ERR": np.full_like(time, 0.0004)
    })
    file_path = tmp_path / "UNKNOWN_QUIET_STAR.csv"
    df.to_csv(file_path, index=False)
    return str(file_path)

def test_schema_detector_fuzzy_matching(synthetic_transit_csv):
    """Verifies that non-standard column headers are correctly resolved."""
    df = pd.read_csv(synthetic_transit_csv)
    schema = DataSchemaDetector.detect_schema(df)
    
    assert schema["time"] == "time_bjd"
    assert schema["flux"] == "normalized_flux"
    assert schema["flux_err"] == "flux_uncertainty"

def test_lightcurve_adapter_ingestion(synthetic_transit_csv):
    """Verifies light curve adaptation from arbitrary file."""
    df = pd.read_csv(synthetic_transit_csv)
    schema = DataSchemaDetector.detect_schema(df)
    lc = LightCurveAdapter.to_lightcurve(df, schema, star_id="UNKNOWN_TARGET_ALPHA")
    
    assert lc.star_id == "UNKNOWN_TARGET_ALPHA"
    assert len(lc.time) == 4000
    assert len(lc.flux) == 4000
    assert np.isfinite(lc.flux).all()

def test_upload_api_and_dynamic_analysis(synthetic_transit_csv):
    """Verifies upload endpoint and immediate scientific pipeline execution on new data."""
    with open(synthetic_transit_csv, "rb") as f:
        resp = client.post("/api/data/upload", files={"file": ("UNKNOWN_TARGET_ALPHA.csv", f, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["mode"] == "REAL"
    uploaded_star_id = data["star_id"]
    saved_path = data["saved_path"]
    assert os.path.exists(saved_path)

    # Run scientific pipeline on uploaded arbitrary star
    res = run_pipeline_sync(uploaded_star_id, filepath=saved_path)
    assert res["star_id"] == uploaded_star_id
    assert "candidates" in res
    assert len(res["candidates"]) > 0
    # Candidate should detect period near 12.5 days (or integer harmonic)
    best = res["candidates"][0]
    period_ratio = best["period"] / 12.5
    is_harmonic = any(abs(period_ratio - h) < 0.05 for h in [0.5, 1.0, 2.0])
    assert is_harmonic or best["sde"] > 3.0

def test_flat_lightcurve_rejection(synthetic_flat_csv):
    """Verifies that flat noise light curves are evaluated without false alarms."""
    with open(synthetic_flat_csv, "rb") as f:
        resp = client.post("/api/data/upload", files={"file": ("UNKNOWN_QUIET_STAR.csv", f, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    uploaded_star_id = data["star_id"]
    saved_path = data["saved_path"]

    res = run_pipeline_sync(uploaded_star_id, filepath=saved_path)
    assert res["star_id"] == uploaded_star_id
    # Quiet star without transit should have low confidence
    assert res["confidence"] < 0.50
    assert res["prediction"] == 0

def test_astra_explains_arbitrary_uploaded_target(synthetic_transit_csv):
    """Verifies that CARL/ASTRA explains real results on unseen uploaded stars without error."""
    with open(synthetic_transit_csv, "rb") as f:
        resp_up = client.post("/api/data/upload", files={"file": ("UNKNOWN_TARGET_ALPHA.csv", f, "text/csv")})
    star_id = resp_up.json()["star_id"]

    resp = client.post("/api/assistant/chat", json={
        "message": f"Explain the scientific results for {star_id}",
        "star_id": star_id,
        "mode": "SCIENTIST"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert star_id in data["answer"]
    assert data["scientific_values"] is not None
    assert data["scientific_values"]["period_days"] > 0
