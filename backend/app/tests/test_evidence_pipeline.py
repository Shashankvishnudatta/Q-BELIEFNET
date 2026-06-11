import asyncio

import pytest

from app.core.contracts import AppHTTPException
from app.services.evidence_pipeline import build_evidence_bundle
from app.services.providers.cache import evidence_cache


def test_demo_pipeline_returns_source_mix(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATA_MODE", "demo")
    evidence_cache._items.clear()

    bundle = asyncio.run(build_evidence_bundle("NVDA", window="fixed"))

    assert bundle.source_mix["synthetic"] > 0
    assert bundle.source_mix["live"] == 0
    assert bundle.freshness_summary.synthetic_item_count == len(bundle.items)


def test_hybrid_pipeline_marks_demo_fallback_when_live_unavailable(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATA_MODE", "hybrid")
    monkeypatch.setattr("app.core.config.settings.RAPIDAPI_KEY", None)
    evidence_cache._items.clear()

    bundle = asyncio.run(build_evidence_bundle("MSFT", window="fixed"))

    assert bundle.source_mix["fallback"] > 0
    assert bundle.meta.is_fallback is True
    assert any("DATA_MODE=hybrid" in warning for warning in bundle.warnings)


def test_live_pipeline_does_not_silently_use_demo(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATA_MODE", "live")
    monkeypatch.setattr("app.core.config.settings.RAPIDAPI_KEY", None)
    monkeypatch.setattr("app.core.config.settings.ALLOW_LIVE_MODE_DEMO_FALLBACK", False)
    evidence_cache._items.clear()

    with pytest.raises(AppHTTPException):
        asyncio.run(build_evidence_bundle("TSLA", window="fixed"))
