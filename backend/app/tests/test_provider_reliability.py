import asyncio

from app.models.schemas import EvidenceRequest, ProviderResult
from app.services.providers.base import EvidenceProvider
from app.core.contracts import utc_now_iso


class FailingProvider(EvidenceProvider):
    name = "failing-provider"
    source_type = "test"
    supports_live = True

    async def fetch_evidence(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        raise RuntimeError("boom")


class SlowProvider(EvidenceProvider):
    name = "slow-provider"
    source_type = "test"
    supports_live = True

    async def fetch_evidence(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        await asyncio.sleep(0.2)
        return ProviderResult(provider=self.name, source="live", mode=context.mode, generated_at=utc_now_iso(), status="ok")


def test_provider_circuit_opens_after_repeated_failures(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PROVIDER_RETRY_COUNT", 0)
    monkeypatch.setattr("app.core.config.settings.PROVIDER_CIRCUIT_FAILURE_THRESHOLD", 2)
    provider = FailingProvider()
    request = EvidenceRequest(symbol="NVDA", mode="live")

    asyncio.run(provider.fetch_with_reliability("NVDA", request))
    asyncio.run(provider.fetch_with_reliability("NVDA", request))
    result = asyncio.run(provider.fetch_with_reliability("NVDA", request))

    assert provider.runtime_metrics().circuit_state == "open"
    assert result.status == "circuit_open"


def test_provider_timeout_is_structured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PROVIDER_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr("app.core.config.settings.PROVIDER_RETRY_COUNT", 0)
    provider = SlowProvider()
    result = asyncio.run(provider.fetch_with_reliability("NVDA", EvidenceRequest(symbol="NVDA", mode="live")))

    assert result.status == "timeout"
    assert result.errors[0]["code"] == "PROVIDER_TIMEOUT"
