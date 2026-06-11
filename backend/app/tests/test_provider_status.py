from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_provider_status_does_not_leak_secrets():
    response = client.get("/api/providers/status")

    assert response.status_code == 200
    payload = response.json()
    assert "providers" in payload
    assert "evidence_cache" in payload
    text = response.text.lower()
    assert "hf_" not in text
    assert "rapidapi_key" not in text
    assert "secret" not in text


def test_api_status_includes_evidence_cache_and_providers():
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert "providers" in payload
    assert payload["evidence_cache"]["backend"] == "memory"
