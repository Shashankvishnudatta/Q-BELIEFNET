import asyncio

from app.models.schemas import EvidenceRequest
from app.services.providers.demo_provider import DemoEvidenceProvider


def test_provider_runtime_metrics_update_on_success():
    provider = DemoEvidenceProvider()
    result = asyncio.run(provider.fetch_with_reliability("NVDA", EvidenceRequest(symbol="NVDA", mode="demo", window="metrics")))
    metrics = provider.runtime_metrics()

    assert result.status == "ok"
    assert metrics.success_count == 1
    assert metrics.failure_count == 0
    assert metrics.last_result_count > 0
    assert metrics.circuit_state == "closed"
