import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_models_endpoint():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_invalid_file_analysis():
    response = client.post("/api/analyze/star", data={"filepath": "non_existent.parquet"})
    assert response.status_code == 400
