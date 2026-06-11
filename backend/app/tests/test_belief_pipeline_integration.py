from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_belief_endpoint_includes_evidence_bundle_source_mix():
    response = client.get("/api/belief/NVDA")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["evidence_bundle"]["source_mix"]["synthetic"] > 0
    assert data["freshness_summary"]["synthetic_item_count"] > 0
    assert data["provider_results"]


def test_llm_fallback_mentions_source_context(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.HF_API_KEY", None)
    response = client.post("/api/llm", json={"question": "Explain NVDA belief"})

    assert response.status_code == 200
    text = response.json()["response"].lower()
    assert "source mix" in text
    assert "synthetic" in text
    assert "not financial advice" in text
