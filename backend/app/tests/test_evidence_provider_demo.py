import asyncio

from app.models.schemas import EvidenceRequest
from app.services.providers.demo_provider import DemoEvidenceProvider, PROTOTYPE_NOTE


def test_demo_provider_returns_synthetic_provenance():
    provider = DemoEvidenceProvider()
    result = asyncio.run(provider.fetch_evidence("NVDA", EvidenceRequest(symbol="NVDA", mode="demo", window="fixed")))

    assert result.status == "ok"
    assert result.provider == "internal-demo-generator"
    assert result.evidence
    assert all(item.is_synthetic for item in result.evidence)
    assert all(item.note == PROTOTYPE_NOTE for item in result.evidence)
    assert all(item.provenance.source == "generated" for item in result.evidence)


def test_demo_provider_is_stable_for_same_window():
    provider = DemoEvidenceProvider()
    first = asyncio.run(provider.fetch_evidence("AAPL", EvidenceRequest(symbol="AAPL", mode="demo", window="fixed")))
    second = asyncio.run(provider.fetch_evidence("AAPL", EvidenceRequest(symbol="AAPL", mode="demo", window="fixed")))

    assert [item.text for item in first.evidence] == [item.text for item in second.evidence]
