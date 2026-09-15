"""
Comprehensive Test Suite for NASA/MAST Cross-Validation Engine
Tests canonical KIC resolution, archival multi-table queries, candidate parameter matching,
harmonic checks, deterministic verdicts (NASA VERIFIED, NASA CONFLICT, UNVERIFIED),
and caching behavior.
"""
import os
import pytest
from src.validation.nasa_cross_validator import (
    resolve_canonical_kic,
    match_candidate_against_nasa_record,
    cross_validate_star_with_nasa,
    CACHE_DIR
)


def test_resolve_canonical_kic():
    """Test resolution of various input formats to canonical KIC identifiers."""
    # Standard KIC formats
    res = resolve_canonical_kic("KIC_11904011")
    assert res["kic_id"] == 11904011
    assert res["canonical_name"] == "KIC 11904011"

    res = resolve_canonical_kic("kic 5306984")
    assert res["kic_id"] == 5306984
    assert res["canonical_name"] == "KIC 5306984"

    res = resolve_canonical_kic(11442793)
    assert res["kic_id"] == 11442793
    assert res["canonical_name"] == "KIC 11442793"

    # Synthetic / Anonymized star IDs
    res = resolve_canonical_kic("STAR_0037")
    assert res["kic_id"] is None
    assert res["canonical_name"] == "STAR_0037"

    # File paths
    res = resolve_canonical_kic("data/dev/STAR_0037.parquet")
    assert res["kic_id"] is None
    assert res["canonical_name"] == "STAR_0037"

    res = resolve_canonical_kic("data/dev/KIC_5306984.parquet")
    assert res["kic_id"] == 5306984
    assert res["canonical_name"] == "KIC 5306984"


def test_match_direct_hit():
    """Exact period match within 2% tolerance yields NASA VERIFIED."""
    candidate = {
        "period": 140.32,
        "depth": 1500.0,
        "duration": 6.5,
        "epoch": 135.0,
        "confidence": 0.95
    }
    nasa_records = {
        "found": True,
        "kic_id": 5306984,
        "disposition": "CONFIRMED",
        "planets": [{
            "pl_name": "Kepler-32 b",
            "period": 140.315,
            "depth_ppm": 1520.0,
            "duration_hours": 6.45,
            "epoch_bkjd": 135.02,
            "source": "pscomppars"
        }],
        "kois": [],
        "tces": []
    }

    result = match_candidate_against_nasa_record(candidate, nasa_records)
    assert result["status"] == "NASA VERIFIED"
    assert result["matched_planet"] == "Kepler-32 b"
    assert result["metrics"]["period"]["status"] == "MATCH"
    assert result["metrics"]["period"]["delta_pct"] < 2.0


def test_match_harmonic_alias():
    """Harmonic alias (e.g. 2x period multiple) yields NASA VERIFIED with harmonic flag."""
    candidate = {
        "period": 280.64,  # Exactly 2x true 140.32d
        "depth": 1500.0,
        "duration": 6.5,
        "epoch": 135.0,
        "confidence": 0.90
    }
    nasa_records = {
        "found": True,
        "kic_id": 5306984,
        "disposition": "CONFIRMED",
        "planets": [{
            "pl_name": "Kepler-32 b",
            "period": 140.32,
            "depth_ppm": 1500.0,
            "duration_hours": 6.5,
            "epoch_bkjd": 135.0,
            "source": "pscomppars"
        }],
        "kois": [],
        "tces": []
    }

    result = match_candidate_against_nasa_record(candidate, nasa_records)
    assert result["status"] == "NASA VERIFIED"
    assert result["metrics"]["period"]["status"] == "HARMONIC"
    assert any("harmonic" in r.lower() for r in result["reasons"])


def test_match_conflict_divergent_period():
    """Divergent period (>2% and non-harmonic) yields NASA CONFLICT."""
    candidate = {
        "period": 42.15,  # Completely divergent from 140.32d
        "depth": 1500.0,
        "duration": 6.5,
        "epoch": 135.0,
        "confidence": 0.85
    }
    nasa_records = {
        "found": True,
        "kic_id": 5306984,
        "disposition": "CONFIRMED",
        "planets": [{
            "pl_name": "Kepler-32 b",
            "period": 140.32,
            "depth_ppm": 1500.0,
            "duration_hours": 6.5,
            "epoch_bkjd": 135.0,
            "source": "pscomppars"
        }],
        "kois": [],
        "tces": []
    }

    result = match_candidate_against_nasa_record(candidate, nasa_records)
    assert result["status"] == "NASA CONFLICT"
    assert result["metrics"]["period"]["status"] == "CONFLICT"


def test_synthetic_star_unverified():
    """Anonymized STAR_XXXX targets deterministically evaluate to UNVERIFIED."""
    result = cross_validate_star_with_nasa(
        star_id="STAR_0037",
        cosmos_period=8.25,
        cosmos_depth=450.0,
        cosmos_duration=3.2,
        cosmos_confidence=0.88
    )
    assert result["status"] == "UNVERIFIED"
    assert result["canonical_star_id"] == "STAR_0037"
    assert result["kic_id"] is None
    assert any("anonymized" in r.lower() or "synthetic" in r.lower() for r in result["reasons"])


def test_unverified_when_nasa_records_absent():
    """When no NASA records exist, deterministic verdict is UNVERIFIED, never CONFLICT."""
    candidate = {
        "period": 12.5,
        "depth": 800.0,
        "duration": 2.5,
        "confidence": 0.80
    }
    nasa_records = {
        "found": False,
        "kic_id": 99999999,
        "disposition": "NONE",
        "planets": [],
        "kois": [],
        "tces": []
    }

    result = match_candidate_against_nasa_record(candidate, nasa_records)
    assert result["status"] == "UNVERIFIED"
    assert result["disposition"] == "NONE"
    assert any("No corresponding NASA" in r for r in result["reasons"])


def test_kic_11904011_live_archival_status():
    """
    KIC 11904011 has 15 quarters in MAST Kepler, but no KOI/TCE entries.
    Should yield UNVERIFIED with MAST observations confirmed.
    """
    result = cross_validate_star_with_nasa(
        star_id="KIC 11904011",
        cosmos_period=10.0,
        cosmos_depth=500.0,
        cosmos_duration=2.0,
        cosmos_confidence=0.75
    )
    assert result["status"] == "UNVERIFIED"
    assert result["kic_id"] == 11904011
    assert result["mast"]["has_observations"] is True
    assert result["mast"]["observation_count"] >= 10
