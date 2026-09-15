import pytest
import numpy as np
from src.validation.exoplanet_validator import fetch_gold_standard_data, validate_pipeline_metrics
from src.detrending.adaptive import wotan_highpass_detrend, adaptive_detrend
from src.data.lightcurve import LightCurve

def test_fetch_gold_standard_data_synthetic():
    # Synthetic target with 0 or negative ID returns error gracefully
    res = fetch_gold_standard_data(0)
    assert res["status"] == "error"
    assert "Invalid" in res["message"] or "synthetic" in res["message"]

def test_validate_pipeline_metrics_subharmonic():
    # True period = 100.0 days. Pipeline finds 10.0 days (1/10th sub-harmonic alias)
    # Mock validation logic by checking validate_pipeline_metrics with known KIC if available, or direct check
    from src.validation import exoplanet_validator
    # Inject mock into cache
    exoplanet_validator._GOLD_STANDARD_CACHE[99999999] = {
        "status": "success",
        "kic_id": 99999999,
        "koi_name": "K99999.01",
        "disposition": "CONFIRMED",
        "period_days": 100.0,
        "depth_ppm": 2500.0,
        "duration_hours": 4.5,
        "source_table": "mock"
    }

    val = validate_pipeline_metrics(
        kic_id=99999999,
        pipeline_period=10.0,  # 1/10th of 100.0
        pipeline_depth=2500.0,
        pipeline_duration=4.5,
        tolerance=0.05
    )
    assert val["status"] == "validated"
    assert val["is_alias"] is True
    assert "Sub-harmonic" in val["alias_type"]
    assert val["checks"]["period"]["valid"] is False
    assert val["checks"]["period"]["harmonic_factor"] == 10

def test_validate_pipeline_metrics_harmonic_multiple():
    from src.validation import exoplanet_validator
    exoplanet_validator._GOLD_STANDARD_CACHE[88888888] = {
        "status": "success",
        "kic_id": 88888888,
        "koi_name": "K88888.01",
        "disposition": "CONFIRMED",
        "period_days": 10.0,
        "depth_ppm": 1200.0,
        "duration_hours": 2.5,
        "source_table": "mock"
    }

    val = validate_pipeline_metrics(
        kic_id=88888888,
        pipeline_period=30.0,  # 3x multiple
        pipeline_depth=1200.0,
        pipeline_duration=2.5,
        tolerance=0.05
    )
    assert val["status"] == "validated"
    assert val["is_alias"] is True
    assert "Harmonic Multiple" in val["alias_type"]
    assert val["checks"]["period"]["valid"] is False
    assert val["checks"]["period"]["harmonic_factor"] == 3

def test_validate_pipeline_metrics_within_tolerance():
    from src.validation import exoplanet_validator
    exoplanet_validator._GOLD_STANDARD_CACHE[77777777] = {
        "status": "success",
        "kic_id": 77777777,
        "koi_name": "K77777.01",
        "disposition": "CONFIRMED",
        "period_days": 15.0,
        "depth_ppm": 1000.0,
        "duration_hours": 3.0,
        "source_table": "mock"
    }

    # Within 2% (tolerance is 5%)
    val = validate_pipeline_metrics(
        kic_id=77777777,
        pipeline_period=15.1,
        pipeline_depth=1010.0,
        pipeline_duration=3.05,
        tolerance=0.05
    )
    assert val["status"] == "validated"
    assert val["is_alias"] is False
    assert val["checks"]["period"]["valid"] is True
    assert val["checks"]["depth"]["valid"] is True
    assert val["checks"]["duration"]["valid"] is True

def test_wotan_highpass_detrend_flattens_spots():
    time = np.linspace(0, 20, 1000)
    # Strong spot rotation with period 3.5 days
    spot_rotation = 0.04 * np.sin(2 * np.pi * time / 3.5)
    raw_flux = 1.0 + spot_rotation + 0.001 * np.random.randn(1000)

    detrended, trend = wotan_highpass_detrend(time, raw_flux, window_length_days=1.5, method="biweight")
    assert len(detrended) == len(time)
    # The detrended standard deviation should be dramatically lower than the un-detrended
    assert np.std(detrended) < 0.01
    assert np.isclose(np.median(detrended), 1.0, atol=0.01)

def test_lightcurve_flatten_wotan():
    time = np.linspace(0, 10, 500)
    flux = 1.0 + 0.02 * np.sin(time)
    lc = LightCurve(
        star_id="TEST_STAR",
        kepid=12345,
        time=time,
        flux=flux,
        flux_err=np.ones_like(flux) * 1e-4,
        quality=np.zeros(len(time), dtype=np.int32),
        quarter=np.zeros(len(time), dtype=np.int16)
    )
    flat_lc = lc.flatten_wotan(window_length_days=1.0)
    assert len(flat_lc.time) == len(lc.time)
    assert np.std(flat_lc.flux) < np.std(lc.flux)
