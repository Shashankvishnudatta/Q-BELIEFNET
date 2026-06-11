from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_llm_missing_key_returns_belief_fallback_without_secret(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.HF_API_KEY", None)
    response = client.post("/api/llm", json={"question": "What is happening with NVDA?"})

    assert response.status_code == 200
    payload = response.json()
    assert "response" in payload
    assert "belief score" in payload["response"].lower()
    assert "not financial advice" in payload["response"].lower()
    assert "HF_API_KEY" not in response.text
    assert "hf_" not in response.text.lower()
