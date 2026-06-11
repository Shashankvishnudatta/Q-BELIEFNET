from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_belief_snapshot_route_returns_provenance():
    response = client.get("/api/belief/NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["asset"]["symbol"] == "NVDA"
    assert payload["data"]["meta"]["provider"] == "evidence-pipeline-v1"
    assert "evidence_bundle" in payload["data"]
    assert payload["meta"]["source"] in {"generated", "fallback"}
    assert payload["data"]["evidence"]


def test_belief_trending_route_returns_ranked_snapshots():
    response = client.get("/api/belief/trending?limit=4")

    assert response.status_code == 200
    payload = response.json()
    scores = [item["belief"]["score"] for item in payload["data"]]
    assert len(scores) == 4
    assert scores == sorted(scores, reverse=True)


def test_belief_history_route_returns_demo_history():
    response = client.get("/api/belief/AAPL/history?days=5")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 5
    assert "generated_at" in payload["meta"]


def test_invalid_ticker_returns_structured_error():
    response = client.get("/api/belief/BAD!")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_TICKER"
    assert "request_id" in payload["error"]
