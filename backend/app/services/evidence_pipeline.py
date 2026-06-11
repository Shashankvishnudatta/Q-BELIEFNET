from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.contracts import AppHTTPException, make_provenance, utc_now_iso
from app.models.schemas import (
    EvidenceBundle,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceRequest,
    ProviderResult,
    SourceReliability,
)
from app.services.providers.cache import evidence_cache
from app.services.providers.registry import provider_registry
from app.db.repository import save_cache_record, save_provider_health_event


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _source_mix(items: list[EvidenceItem], results: list[ProviderResult]) -> dict[str, int]:
    mix = {"live": 0, "cached": 0, "synthetic": 0, "fallback": 0, "unavailable": 0}
    for item in items:
        if item.is_live:
            mix["live"] += 1
        if item.is_cached:
            mix["cached"] += 1
        if item.is_synthetic:
            mix["synthetic"] += 1
        if item.provenance.is_fallback:
            mix["fallback"] += 1
    mix["unavailable"] = sum(1 for result in results if result.status == "unavailable")
    return mix


def _freshness(items: list[EvidenceItem]) -> EvidenceFreshness:
    now = datetime.now(timezone.utc)
    timestamps = [parsed for item in items if (parsed := _parse_timestamp(item.timestamp))]
    fresh_cutoff = now - timedelta(minutes=30)
    return EvidenceFreshness(
        latest_timestamp=max(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None,
        oldest_timestamp=min(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None,
        fresh_item_count=sum(1 for stamp in timestamps if stamp >= fresh_cutoff),
        stale_item_count=sum(1 for stamp in timestamps if stamp < fresh_cutoff),
        cache_hit_count=sum(1 for item in items if item.is_cached),
        live_item_count=sum(1 for item in items if item.is_live),
        synthetic_item_count=sum(1 for item in items if item.is_synthetic),
        cache_state="stale" if any(getattr(item, "is_cached", False) for item in items) and any(result.served_stale for result in getattr(_freshness, "_last_results", [])) else "hit" if any(item.is_cached for item in items) else "miss",
        cache_hit=any(item.is_cached for item in items),
        cache_miss=not any(item.is_cached for item in items),
        served_stale=any(result.served_stale for result in getattr(_freshness, "_last_results", [])),
    )


async def _fetch_with_cache(provider, request: EvidenceRequest) -> ProviderResult:
    cached = evidence_cache.get(provider.name, request.symbol, request.mode, request.window)
    if cached:
        return cached
    result = await provider.fetch_with_reliability(request.symbol, request)
    if result.status not in {"ok", "partial", "cached"}:
        stale = evidence_cache.get_stale(
            provider.name,
            request.symbol,
            request.mode,
            request.window,
            reason=result.errors[0]["code"] if result.errors else "PROVIDER_FAILURE",
        )
        if stale and request.mode in {"hybrid", "live"}:
            stale.warnings = [*stale.warnings, "Provider failed; stale cache was served visibly."]
            return stale
    evidence_cache.set(provider.name, request.symbol, request.mode, request.window, result)
    return result


async def build_evidence_bundle(symbol: str, *, window: str = "latest") -> EvidenceBundle:
    normalized = validate_pipeline_symbol(symbol)
    mode = settings.DATA_MODE
    request = EvidenceRequest(
        symbol=normalized,
        mode=mode,
        window=window,
        allow_fallback=mode in {"demo", "hybrid"} or settings.ALLOW_LIVE_MODE_DEMO_FALLBACK,
    )

    providers = provider_registry.providers_for_mode(mode)
    results = await asyncio.gather(*[_fetch_with_cache(provider, request) for provider in providers])
    items = [item for result in results for item in result.evidence]
    warnings = [warning for result in results for warning in result.warnings]

    live_or_cached_items = [item for item in items if item.is_live or item.is_cached]
    if mode == "hybrid" and not live_or_cached_items:
        fallback_request = request.model_copy(update={"allow_fallback": True})
        fallback = await provider_registry.fallback_provider().fetch_evidence(normalized, fallback_request)
        fallback.is_fallback = True
        fallback.source = "fallback"
        results.append(fallback)
        items.extend(fallback.evidence)
        warnings.append("Live evidence unavailable. Showing demo fallback because DATA_MODE=hybrid.")

    if mode == "live" and not items:
        if settings.ALLOW_LIVE_MODE_DEMO_FALLBACK:
            fallback = await provider_registry.fallback_provider().fetch_evidence(normalized, request)
            fallback.is_fallback = True
            fallback.source = "fallback"
            results.append(fallback)
            items.extend(fallback.evidence)
            warnings.append("Live mode demo fallback is explicitly enabled; evidence is synthetic.")
        else:
            raise AppHTTPException(
                status_code=503,
                code="BELIEF_EVIDENCE_UNAVAILABLE",
                message="Live mode is active, but no configured provider returned evidence.",
                details={"mode": mode, "allow_demo_fallback": False},
            )

    mix = _source_mix(items, results)
    _freshness._last_results = results  # type: ignore[attr-defined]
    freshness = _freshness(items)
    for provider in provider_registry.providers:
        save_provider_health_event(provider.runtime_metrics())
    reliability = [
        SourceReliability(
            provider=result.provider,
            reliability_weight=max((item.reliability_weight for item in result.evidence), default=0.0),
            rationale=(
                "Live provider evidence." if result.is_live else
                "Cached evidence from in-memory TTL cache." if result.is_cached else
                "Synthetic demo/fallback evidence."
            ),
        )
        for result in results
    ]
    source = "generated" if mix["live"] == 0 and mix["synthetic"] > 0 and mode == "demo" else "fallback" if mix["fallback"] else "live" if mix["live"] else "unavailable"
    for result in results:
        if result.cache_key:
            save_cache_record(
                cache_key=result.cache_key,
                symbol=normalized,
                provider=result.provider,
                mode=mode,
                freshness={
                    **freshness.model_dump(),
                    "cached_at": result.cached_at,
                    "expires_at": result.expires_at,
                    "age_seconds": result.age_seconds,
                    "ttl_seconds": result.ttl_seconds,
                    "stale": result.stale,
                    "served_stale": result.served_stale,
                    "cache_hit": result.cache_hit,
                },
                source_mix=mix,
                item_count=len(result.evidence),
            )
    return EvidenceBundle(
        symbol=normalized,
        items=items,
        provider_results=results,
        freshness_summary=freshness,
        source_mix=mix,
        reliability=reliability,
        warnings=warnings,
        meta=make_provenance(
            source=source,
            provider="evidence-pipeline-v1",
            is_fallback=mix["fallback"] > 0,
            notes="Evidence bundle assembled from provider registry with explicit source mix and freshness.",
            confidence="prototype" if mix["live"] == 0 else "low",
        ),
    )


def provider_status_payload() -> dict[str, object]:
    metrics = [provider.runtime_metrics().model_dump() for provider in provider_registry.providers]
    return {
        "providers": [status.model_dump() for status in provider_registry.status(settings.DATA_MODE)],
        "runtime_metrics": metrics,
        "health_summary": {
            "healthy": sum(1 for metric in metrics if metric["status"] == "healthy"),
            "degraded": sum(1 for metric in metrics if metric["status"] not in {"healthy", "disabled"}),
            "circuit_open": sum(1 for metric in metrics if metric["circuit_state"] == "open"),
        },
        "evidence_cache": evidence_cache.summary(),
        "mode": settings.DATA_MODE,
    }
def validate_pipeline_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 8 or not re.fullmatch(r"[A-Z0-9.]+", normalized):
        raise AppHTTPException(
            status_code=400,
            code="INVALID_TICKER",
            message="Ticker must be a short alphanumeric symbol.",
            details={"ticker": symbol},
        )
    return normalized
