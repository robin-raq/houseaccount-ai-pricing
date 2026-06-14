"""FastAPI /predict + /health contract (the internal Rails<->Python boundary)."""

from fastapi.testclient import TestClient

from service.main import app

client = TestClient(app)


def test_health_reports_model_version():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "model_version" in body


def test_predict_returns_full_estimate_shape():
    response = client.post(
        "/predict",
        json={
            "job_id": "abc123",
            "service_category": "Plumbing",
            "zip_code": "78704",
            "job_description": "50-gallon gas water heater, pilot won't stay lit",
            "original_estimate": 1825,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "abc123"
    assert body["estimate_lo"] <= body["estimate_midpoint"] <= body["estimate_hi"]
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["model_version"]
    assert "latency_ms" in body


def test_predict_validates_required_fields():
    response = client.post("/predict", json={"job_id": "x"})
    assert response.status_code == 422  # FastAPI/pydantic validation on the internal contract
