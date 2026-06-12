from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_manual_refresh_requires_token_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'manual-refresh.db'}")
    monkeypatch.setattr(settings, "ENABLE_MANUAL_REFRESH", True)
    monkeypatch.setattr(settings, "REQUIRE_MANUAL_REFRESH_TOKEN", True)
    monkeypatch.setattr(settings, "MANUAL_REFRESH_TOKEN", "unit-test-token")
    init_db()
    client = TestClient(app)

    denied = client.post("/api/ingestion/refresh", json={"symbols": ["NVDA"]})
    allowed = client.post("/api/ingestion/refresh", json={"symbols": ["NVDA"]}, headers={"X-QBN-Admin-Token": "unit-test-token"})

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "MANUAL_REFRESH_TOKEN_REQUIRED"
    assert allowed.status_code == 200


def test_manual_refresh_symbol_limit_uses_config(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'manual-refresh-limit.db'}")
    monkeypatch.setattr(settings, "MAX_MANUAL_REFRESH_SYMBOLS", 1)
    init_db()
    client = TestClient(app)

    response = client.post("/api/ingestion/refresh", json={"symbols": ["NVDA", "AAPL"]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TOO_MANY_SYMBOLS"
