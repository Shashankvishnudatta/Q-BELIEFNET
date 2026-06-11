from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_route_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_status_does_not_expose_secrets():
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "llm" in payload
    assert "redis" in payload
    assert "app_mode" in payload
    assert "data_mode" in payload
    assert "HF_API_KEY" not in payload
    assert "RAPIDAPI_KEY" not in payload
