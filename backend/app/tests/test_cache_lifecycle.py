import asyncio
from datetime import datetime, timedelta, timezone

from app.models.schemas import EvidenceRequest
from app.services.providers.cache import evidence_cache
from app.services.providers.demo_provider import DemoEvidenceProvider


def test_stale_cache_is_marked_when_served(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATA_MODE", "hybrid")
    monkeypatch.setattr("app.core.config.settings.ENABLE_EVIDENCE_CACHE", True)
    monkeypatch.setattr("app.core.config.settings.ALLOW_STALE_CACHE_ON_PROVIDER_FAILURE", True)
    evidence_cache._items.clear()

    provider = DemoEvidenceProvider()
    request = EvidenceRequest(symbol="NVDA", mode="hybrid", window="stale-test")
    result = asyncio.run(provider.fetch_evidence("NVDA", request))
    evidence_cache.set(provider.name, "NVDA", "hybrid", "stale-test", result)
    key = evidence_cache.key(provider.name, "NVDA", "hybrid", "stale-test")
    cached_at, expires_at, stored = evidence_cache._items[key]
    evidence_cache._items[key] = (
        datetime.now(timezone.utc) - timedelta(seconds=400),
        datetime.now(timezone.utc) - timedelta(seconds=100),
        stored,
    )

    stale = evidence_cache.get_stale(provider.name, "NVDA", "hybrid", "stale-test", reason="PROVIDER_FAILURE")

    assert stale is not None
    assert stale.served_stale is True
    assert stale.stale is True
    assert stale.cache_hit is True
