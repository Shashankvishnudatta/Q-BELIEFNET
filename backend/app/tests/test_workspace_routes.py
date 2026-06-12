from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_watchlist_portfolio_and_alert_rule_routes_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'workspace.db'}")
    init_db()
    client = TestClient(app)

    watchlist_create = client.post("/api/watchlist", json={"symbol": "MSFT", "notes": "Track belief changes"})
    portfolio_create = client.post("/api/portfolio", json={"symbol": "MSFT", "quantity": 2, "is_demo": True})
    alert_create = client.post(
        "/api/alert-rules",
        json={"symbol": "MSFT", "metric": "belief_score", "operator": ">=", "threshold": 70},
    )
    workspace_response = client.get("/api/workspace")

    assert watchlist_create.status_code == 200
    assert portfolio_create.status_code == 200
    assert alert_create.status_code == 200
    workspace = workspace_response.json()["data"]
    assert workspace["watchlist"][0]["symbol"] == "MSFT"
    assert workspace["portfolio"][0]["symbol"] == "MSFT"
    assert workspace["alerts"][0]["metric"] == "belief_score"


def test_workspace_symbol_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'workspace-invalid.db'}")
    init_db()
    client = TestClient(app)

    response = client.post("/api/watchlist", json={"symbol": "BAD!"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SYMBOL"
