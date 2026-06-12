from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from main import app


def test_belief_snapshot_persists_and_history_uses_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'snapshots.db'}")
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    init_db()
    client = TestClient(app)

    snapshot_response = client.get("/api/belief/NVDA")
    history_response = client.get("/api/belief/NVDA/history")

    assert snapshot_response.status_code == 200
    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["meta"]["provider"] == "sqlite-belief-snapshot-store"
    assert payload["meta"]["source"] == "cached"
    assert len(payload["data"]) >= 1
