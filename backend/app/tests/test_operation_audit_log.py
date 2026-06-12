from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_operation_audit_endpoint_returns_workspace_operations(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'audit.db'}")
    init_db()
    client = TestClient(app)

    client.post("/api/watchlist", json={"symbol": "TSLA"})
    response = client.get("/api/audit/operations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["provider"] == "sqlite-operation-audit-log"
    assert payload["data"][0]["operation"] == "watchlist_add"
    assert "secret-value" not in str(payload).lower()
