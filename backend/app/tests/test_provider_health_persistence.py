from app.db.init_db import init_db
from app.db.repository import recent_provider_health_events, save_provider_health_event
from app.core.config import settings
from app.models.schemas import ProviderRuntimeMetrics


def test_provider_health_event_persists_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERSISTENCE", True)
    monkeypatch.setattr(settings, "PERSISTENCE_MODE", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'provider-health.db'}")
    init_db()

    save_provider_health_event(
        ProviderRuntimeMetrics(
            provider_name="unit-test-provider",
            enabled=True,
            configured=False,
            supports_live=True,
            status="unavailable",
            failure_count=1,
            consecutive_failures=1,
            last_error_code="PROVIDER_NOT_CONFIGURED",
            last_error_message_redacted="Provider is not configured.",
        )
    )

    events = recent_provider_health_events()
    assert events[0]["provider_name"] == "unit-test-provider"
    assert events[0]["last_error_code"] == "PROVIDER_NOT_CONFIGURED"
    assert "token" not in str(events[0]).lower()
