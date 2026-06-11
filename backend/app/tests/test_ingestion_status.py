from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_ingestion_status_endpoint_works():
    response = client.get("/api/ingestion/status")

    assert response.status_code == 200
    payload = response.json()
    assert "scheduler_enabled" in payload
    assert "recent_runs" in payload
    assert "cache_summary" in payload


def test_manual_refresh_validates_symbols():
    response = client.post("/api/ingestion/refresh", json={"symbols": ["BAD!"]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TICKER"


def test_manual_refresh_runs_one_symbol():
    response = client.post("/api/ingestion/refresh", json={"symbols": ["NVDA"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["symbols_requested"] == ["NVDA"]
    assert payload["data"]["status"] in {"success", "partial"}
