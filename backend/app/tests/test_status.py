from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_status_includes_runtime_contract():
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_mode"] in {"demo", "hybrid", "live"}
    assert payload["data_mode"] in {"demo", "hybrid", "live"}
    assert isinstance(payload["llm"]["configured"], bool)
    assert "features" in payload
    assert payload["features"]["websocket"] is True


def test_status_does_not_leak_secret_values():
    response = client.get("/api/status")
    text = response.text.lower()

    assert "hf_" not in text
    assert "rapidapi_key" not in text
    assert "reddit_client_secret" not in text
