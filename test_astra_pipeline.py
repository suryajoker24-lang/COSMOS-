import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.astra.schemas import UserMode
from backend.astra.safety import safety_guard, SafetyViolation
from backend.astra.tools import tool_registry
from backend.astra.astronomy.catalog import catalog_provider
from backend.astra.astronomy.plate_solver import get_plate_solver

client = TestClient(app)

def test_astra_chat_endpoint_scientist_mode():
    resp = client.post("/api/assistant/chat", json={
        "message": "Explain the scientific summary for STAR_0001",
        "star_id": "STAR_0001",
        "mode": "SCIENTIST"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "STAR_0001" in data["answer"]
    assert data["scientific_values"] is not None
    assert data["scientific_values"]["period_days"] > 0
    assert data["mode"] == "SCIENTIST"

def test_astra_chat_endpoint_beginner_mode():
    resp = client.post("/api/assistant/chat", json={
        "message": "Explain this candidate for a beginner",
        "star_id": "STAR_0001",
        "mode": "BEGINNER"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "What we see" in data["answer"]
    assert data["mode"] == "BEGINNER"

def test_astra_safety_input_sanitization():
    with pytest.raises(SafetyViolation):
        safety_guard.sanitize_user_input("Please run DROP TABLE users; --")

def test_astra_private_truth_protection():
    unsafe_dict = {
        "star_id": "STAR_0001",
        "period": 82.5,
        "private_truth": {"true_class": 1, "injected_truth_ppm": 450},
        "ground_truth_label": 1
    }
    safe_dict = safety_guard.protect_private_truth(unsafe_dict)
    assert "private_truth" not in safe_dict
    assert "ground_truth_label" not in safe_dict
    assert safe_dict["period"] == 82.5

def test_astra_tools_allowlist():
    res = tool_registry.execute_tool("get_validation_metrics", {})
    assert res["status"] == "success"
    assert "precision" in res["result"]

    invalid_res = tool_registry.execute_tool("arbitrary_dangerous_tool", {})
    assert "error" in invalid_res

def test_sky_plate_solving_endpoint():
    resp = client.post("/api/sky/solve", json={
        "hint_ra": 295.5,
        "hint_dec": 44.5,
        "hint_fov": 15.0
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["solved"] is True
    assert "Cygnus" in data["constellation"]
    assert len(data["identified_objects"]) > 0

def test_sky_visible_and_object_catalog():
    resp = client.get("/api/sky/visible?ra=295.5&dec=44.5&fov=15.0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["objects"]) > 0

    obj_resp = client.get("/api/sky/object/Kepler-186")
    assert obj_resp.status_code == 200
    obj_data = obj_resp.json()
    assert obj_data["name"] == "Kepler-186"
    assert obj_data["kepler_host"] is True

def test_telescope_safety_slew_confirmation():
    # Attempt slew without user confirmation -> should be rejected safely
    resp = client.post("/api/telescope/goto", json={
        "action": "goto",
        "target_ra": 298.65,
        "target_dec": 44.62,
        "confirmed_by_user": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "confirmation required" in data["error"].lower()

    # Slew with explicit user confirmation
    resp_confirmed = client.post("/api/telescope/goto", json={
        "action": "goto",
        "target_ra": 298.65,
        "target_dec": 44.62,
        "confirmed_by_user": True
    })
    assert resp_confirmed.status_code == 200
    assert resp_confirmed.json()["success"] is True

def test_voice_endpoints():
    trans_resp = client.post("/api/assistant/voice/transcribe", json={
        "audio_base64": "ZXhwbGFpbiB0aGlzIHRyYW5zaXQ=",
        "format": "webm"
    })
    assert trans_resp.status_code == 200
    assert "text" in trans_resp.json()

    speak_resp = client.post("/api/assistant/voice/speak", json={
        "text": "Orbital period is 82.5 days."
    })
    assert speak_resp.status_code == 200
