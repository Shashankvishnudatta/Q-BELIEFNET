from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_trending_returns_provenance_envelope():
    response = client.get("/api/trending")

    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert "meta" in payload
    assert payload["meta"]["source"] in {"live", "mock", "generated", "cached", "fallback", "unavailable"}
    assert payload["meta"]["mode"] in {"demo", "hybrid", "live"}
    assert "generated_at" in payload["meta"]


def test_alerts_are_marked_as_demo_generated():
    response = client.get("/api/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["source"] == "generated"
    assert payload["meta"]["provider"] == "internal-demo-alerts"
