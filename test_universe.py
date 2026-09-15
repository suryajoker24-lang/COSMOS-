import io
import math
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.astra.astronomy.ephemeris import compute_solar_system_ephemerides, ra_dec_to_alt_az
from backend.astra.astronomy.catalog import get_space_tours, bv_to_rgb_hex, sky_catalog

client = TestClient(app)

# 1. Ephemeris & Orbital Mechanics Tests
def test_solar_system_ephemerides_computation():
    dt = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    lat, lon = 11.0168, 76.9558 # Coimbatore
    planets = compute_solar_system_ephemerides(dt, lat, lon)
    
    assert len(planets) >= 9 # Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune
    
    planet_names = [p["name"] for p in planets]
    assert "Sun" in planet_names
    assert "Moon" in planet_names
    assert "Jupiter" in planet_names
    assert "Mars" in planet_names
    
    for p in planets:
        assert 0.0 <= p["ra"] <= 360.0
        assert -90.0 <= p["dec"] <= 90.0
        assert -90.0 <= p["alt"] <= 90.0
        assert 0.0 <= p["az"] <= 360.0
        assert "distance_au" in p
        
    moon = next(p for p in planets if p["name"] == "Moon")
    assert 0.0 <= moon["illumination_pct"] <= 100.0

def test_ra_dec_to_alt_az_conversion():
    dt = datetime(2026, 3, 20, 0, 0, 0, tzinfo=timezone.utc)
    alt, az = ra_dec_to_alt_az(0.0, 90.0, dt, 90.0, 0.0) # North Pole looking at North Celestial Pole
    assert abs(alt - 90.0) < 1.0 # Should be zenith at North Pole

# 2. Astronomy Catalog & Guided Tours Tests
def test_astronomy_catalog_structure():
    assert len(sky_catalog._stars) >= 20
    assert len(sky_catalog._constellations) >= 5 # Orion, Cygnus, Ursa Major, Cassiopeia, Lyra
    assert len(sky_catalog._dsos) >= 5 # M42, M31, M45, M57, NGC 7000
    
    vega_matches = sky_catalog.search_object("Vega")
    assert len(vega_matches) > 0
    assert "Vega" in vega_matches[0]["name"]

def test_space_tours():
    tours = get_space_tours()
    assert len(tours) >= 3
    for t in tours:
        assert "id" in t
        assert "title" in t
        assert len(t["steps"]) >= 3
        for s in t["steps"]:
            assert "target" in s
            assert "narration" in s

def test_bv_color_hex():
    assert bv_to_rgb_hex(-0.2).startswith("#") # Blue star
    assert bv_to_rgb_hex(0.0).startswith("#")  # White star
    assert bv_to_rgb_hex(1.5).startswith("#")  # Red star

# 3. FastAPI Endpoints Integration Tests
def test_api_sky_planets_endpoint():
    res = client.get("/api/sky/planets?lat=11.0168&lon=76.9558")
    assert res.status_code == 200
    data = res.json()
    assert "planets" in data
    assert len(data["planets"]) >= 8

def test_api_sky_tours_endpoint():
    res = client.get("/api/sky/tours")
    assert res.status_code == 200
    data = res.json()
    assert "tours" in data
    assert len(data["tours"]) >= 3

