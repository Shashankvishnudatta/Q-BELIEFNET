from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_route_is_json_service_metadata():
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "Q-Belief Net API"
    assert payload["docs"] == "/docs"


def test_alerts_route_returns_demo_alerts():
    response = client.get("/api/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["data"], list)
    assert payload["data"]
    assert {"id", "ticker", "message", "severity", "time"}.issubset(payload["data"][0])
    assert payload["meta"]["source"] == "generated"
