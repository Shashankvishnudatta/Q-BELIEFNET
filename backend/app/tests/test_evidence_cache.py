import asyncio

from app.services.evidence_pipeline import build_evidence_bundle
from app.services.providers.cache import evidence_cache


def test_evidence_cache_marks_second_result_cached(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATA_MODE", "demo")
    monkeypatch.setattr("app.core.config.settings.ENABLE_EVIDENCE_CACHE", True)
    monkeypatch.setattr("app.core.config.settings.EVIDENCE_CACHE_TTL_SECONDS", 300)
    evidence_cache._items.clear()

    first = asyncio.run(build_evidence_bundle("AAPL", window="cache-test"))
    second = asyncio.run(build_evidence_bundle("AAPL", window="cache-test"))

    assert first.freshness_summary.cache_hit_count == 0
    assert second.freshness_summary.cache_hit_count == len(second.items)
    assert second.provider_results[0].is_cached is True
