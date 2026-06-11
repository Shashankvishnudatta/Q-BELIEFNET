from __future__ import annotations

from app.core.config import settings
from app.core.contracts import make_provenance, utc_now_iso
from app.models.schemas import EvidenceItem, EvidenceRequest, ProviderResult
from app.services.market_data import fetch_stock_summary
from app.services.providers.base import EvidenceProvider, provider_timer, unavailable_result


class MarketEvidenceProvider(EvidenceProvider):
    name = "market-data-provider"
    source_type = "market"
    supports_live = True

    @property
    def configured(self) -> bool:
        return bool(settings.RAPIDAPI_KEY)

    async def fetch_evidence(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        if not self.configured:
            return unavailable_result(
                provider=self,
                mode=context.mode,
                code="PROVIDER_NOT_CONFIGURED",
                message="Market provider is not configured. Set backend market provider credentials to enable live market evidence.",
            )

        with provider_timer() as timer:
            summary = await fetch_stock_summary(symbol)

        if not summary:
            return unavailable_result(
                provider=self,
                mode=context.mode,
                code="PROVIDER_NO_DATA",
                message="Market provider returned no usable evidence for this symbol.",
                latency_ms=timer.latency_ms,
            )

        sentiment = 0.45 if summary.get("sentiment") == "bullish" else -0.35
        change_pct = float(summary.get("priceChangePct", 0) or 0)
        velocity = float(summary.get("velocity", 0) or 0)
        provenance = make_provenance(
            source="live",
            provider=self.name,
            notes="Live-capable market-derived evidence from configured provider path.",
            confidence="low",
        )
        evidence = [
            EvidenceItem(
                id=f"{symbol.lower()}-market-price-momentum",
                symbol=symbol,
                source_type="market",
                source_name=self.name,
                provider=self.name,
                text=(
                    f"Market-derived signal for {symbol}: one-month price movement is {change_pct:+.2f}% "
                    f"with average momentum {velocity:+.2f}. This is evidence context, not a price prediction."
                ),
                timestamp=utc_now_iso(),
                sentiment=max(-1.0, min(1.0, sentiment + change_pct / 100)),
                attention_weight=min(1.0, 0.45 + abs(change_pct) / 25),
                reliability_weight=0.72,
                matched_keywords=["momentum", "trend", "market"],
                provenance=provenance,
                note="Market-derived provider evidence. Not financial advice.",
                is_synthetic=False,
                is_live=True,
                is_cached=False,
            )
        ]
        self.last_success = utc_now_iso()
        self.last_error_code = None
        return ProviderResult(
            provider=self.name,
            source="live",
            mode=context.mode,
            is_live=True,
            generated_at=utc_now_iso(),
            fetched_at=utc_now_iso(),
            latency_ms=timer.latency_ms,
            status="ok",
            evidence=evidence,
        )
