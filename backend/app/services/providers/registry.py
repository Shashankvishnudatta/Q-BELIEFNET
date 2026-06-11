from __future__ import annotations

from app.core.config import settings
from app.models.schemas import ProviderHealth
from app.services.providers.base import EvidenceProvider
from app.services.providers.demo_provider import DemoEvidenceProvider
from app.services.providers.market_provider import MarketEvidenceProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self.demo_provider = DemoEvidenceProvider()
        self.market_provider = MarketEvidenceProvider()
        self.providers: list[EvidenceProvider] = [self.demo_provider, self.market_provider]

    def providers_for_mode(self, mode: str | None = None) -> list[EvidenceProvider]:
        active_mode = mode or settings.DATA_MODE
        if active_mode == "demo":
            return [self.demo_provider]
        if active_mode == "hybrid":
            return [self.market_provider]
        live = [provider for provider in self.providers if provider.supports_live]
        if settings.ALLOW_LIVE_MODE_DEMO_FALLBACK:
            live.append(self.demo_provider)
        return live

    def fallback_provider(self) -> EvidenceProvider:
        return self.demo_provider

    def status(self, mode: str | None = None) -> list[ProviderHealth]:
        active_mode = mode or settings.DATA_MODE
        return [provider.health(mode=active_mode) for provider in self.providers]


provider_registry = ProviderRegistry()
