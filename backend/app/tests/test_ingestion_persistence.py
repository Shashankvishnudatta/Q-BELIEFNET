from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_manual_refresh_persists_ingestion_run_and_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'ingestion.db'}")
    monkeypatch.setattr(settings, "ENABLE_MANUAL_REFRESH", True)
    monkeypatch.setattr(settings, "REQUIRE_MANUAL_REFRESH_TOKEN", False)
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    init_db()
    client = TestClient(app)

    refresh_response = client.post("/api/ingestion/refresh", json={"symbols": ["AAPL"]})
    status_response = client.get("/api/ingestion/status")
    audit_response = client.get("/api/audit/operations")

    assert refresh_response.status_code == 200
    assert status_response.status_code == 200
    assert status_response.json()["recent_runs"][0]["trigger_type"] == "manual"
    assert any(entry["operation"] == "manual_refresh" for entry in audit_response.json()["data"])
