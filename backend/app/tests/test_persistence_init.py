from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import persistence_status


def test_sqlite_persistence_initializes_temp_database(tmp_path, monkeypatch):
    db_path = tmp_path / "qbeliefnet-test.db"
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")

    init_db()
    status = persistence_status()

    assert db_path.exists()
    assert status["enabled"] is True
    assert status["available"] is True
    assert status["database"] == "configured"
    assert status["stores"]["belief_snapshots"] is True
    assert status["stores"]["audit_log"] is True


def test_persistence_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", False)
    init_db()

    status = persistence_status()

    assert status["enabled"] is False
    assert status["available"] is False
