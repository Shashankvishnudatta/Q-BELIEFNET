from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_status_includes_persistence_and_manual_refresh_without_paths_or_tokens(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'status.db'}")
    monkeypatch.setattr(settings, "REQUIRE_MANUAL_REFRESH_TOKEN", True)
    monkeypatch.setattr(settings, "MANUAL_REFRESH_TOKEN", "status-test-token")
    init_db()
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence"]["database"] == "configured"
    assert payload["manual_refresh"]["requires_token"] is True
    serialized = str(payload)
    assert "status-test-token" not in serialized
    assert str(tmp_path) not in serialized
