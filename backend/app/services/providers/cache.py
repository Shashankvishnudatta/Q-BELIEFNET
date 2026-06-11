from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.contracts import utc_now_iso
from app.models.schemas import ProviderResult


class EvidenceCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[datetime, datetime, ProviderResult]] = {}

    @property
    def enabled(self) -> bool:
        return bool(settings.ENABLE_EVIDENCE_CACHE)

    @property
    def ttl_seconds(self) -> int:
        return max(1, int(settings.EVIDENCE_CACHE_TTL_SECONDS))

    def key(self, provider: str, symbol: str, mode: str, window: str) -> str:
        return f"{provider}:{symbol.upper()}:{mode}:{window}"

    def get(self, provider: str, symbol: str, mode: str, window: str) -> ProviderResult | None:
        if not self.enabled:
            return None
        key = self.key(provider, symbol, mode, window)
        entry = self._items.get(key)
        if not entry:
            return None
        cached_at, expires_at, result = entry
        now = datetime.now(timezone.utc)
        if now >= expires_at:
            return None

        return self._decorate_cached(result, key=key, cached_at=cached_at, expires_at=expires_at, stale=False)

    def get_stale(self, provider: str, symbol: str, mode: str, window: str, *, reason: str) -> ProviderResult | None:
        if not self.enabled or not settings.ALLOW_STALE_CACHE_ON_PROVIDER_FAILURE:
            return None
        key = self.key(provider, symbol, mode, window)
        entry = self._items.get(key)
        if not entry:
            return None
        cached_at, expires_at, result = entry
        now = datetime.now(timezone.utc)
        max_age = timedelta(seconds=max(settings.STALE_CACHE_MAX_AGE_SECONDS, self.ttl_seconds))
        if now - cached_at > max_age:
            return None
        return self._decorate_cached(result, key=key, cached_at=cached_at, expires_at=expires_at, stale=True, reason=reason)

    def set(self, provider: str, symbol: str, mode: str, window: str, result: ProviderResult) -> None:
        if not self.enabled or result.status not in {"ok", "partial"}:
            return
        cached_at = datetime.now(timezone.utc)
        expires_at = cached_at + timedelta(seconds=self.ttl_seconds)
        stored = result.model_copy(deep=True)
        stored.cached_at = cached_at.isoformat().replace("+00:00", "Z")
        stored.expires_at = expires_at.isoformat().replace("+00:00", "Z")
        stored.cache_key = self.key(provider, symbol, mode, window)
        stored.ttl_seconds = self.ttl_seconds
        self._items[self.key(provider, symbol, mode, window)] = (cached_at, expires_at, stored)

    def summary(self) -> dict[str, bool | int | str]:
        return {
            "enabled": self.enabled,
            "backend": "memory",
            "ttl_seconds": self.ttl_seconds,
            "entries": len(self._items),
            "allow_stale_on_failure": bool(settings.ALLOW_STALE_CACHE_ON_PROVIDER_FAILURE),
            "stale_max_age_seconds": int(settings.STALE_CACHE_MAX_AGE_SECONDS),
        }

    def _decorate_cached(
        self,
        result: ProviderResult,
        *,
        key: str,
        cached_at: datetime,
        expires_at: datetime,
        stale: bool,
        reason: str | None = None,
    ) -> ProviderResult:
        now = datetime.now(timezone.utc)
        cached = result.model_copy(deep=True)
        cached.is_cached = True
        cached.status = "cached"
        cached.cache_key = key
        cached.cache_hit = True
        cached.cache_miss = False
        cached.cached_at = cached_at.isoformat().replace("+00:00", "Z")
        cached.expires_at = expires_at.isoformat().replace("+00:00", "Z")
        cached.age_seconds = round((now - cached_at).total_seconds(), 2)
        cached.ttl_seconds = self.ttl_seconds
        cached.stale = stale
        cached.served_stale = stale
        cached.stale_reason = reason if stale else None
        message = "Stale evidence served from in-memory cache after provider failure." if stale else "Evidence served from in-memory TTL cache."
        cached.warnings = [*cached.warnings, message]
        cached.evidence = [item.model_copy(update={"is_cached": True}) for item in cached.evidence]
        return cached


evidence_cache = EvidenceCache()
