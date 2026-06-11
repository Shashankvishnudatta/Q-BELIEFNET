from __future__ import annotations

import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from app.core.config import settings
from app.core.contracts import utc_now_iso
from app.models.schemas import EvidenceRequest, ProviderHealth, ProviderResult, ProviderRuntimeMetrics


class EvidenceProvider(ABC):
    name: str
    source_type: str
    supports_live: bool = False
    enabled: bool = True
    last_success: str | None = None
    last_error_code: str | None = None
    last_failure: str | None = None
    last_error_message_redacted: str | None = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0
    last_latency_ms: float = 0
    circuit_state: str = "closed"
    circuit_opened_at: str | None = None
    last_result_source: str | None = None
    last_result_count: int = 0
    last_fallback_used: bool = False

    @property
    def configured(self) -> bool:
        return True

    @abstractmethod
    async def fetch_evidence(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        raise NotImplementedError

    async def fetch_with_reliability(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        circuit_result = self._circuit_preflight(context.mode)
        if circuit_result:
            return circuit_result

        attempts = max(1, int(settings.PROVIDER_RETRY_COUNT) + 1)
        last_result: ProviderResult | None = None
        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    self.fetch_evidence(symbol, context),
                    timeout=max(0.1, float(settings.PROVIDER_TIMEOUT_SECONDS)),
                )
            except asyncio.TimeoutError:
                result = unavailable_result(
                    provider=self,
                    mode=context.mode,
                    code="PROVIDER_TIMEOUT",
                    message="Provider timed out while fetching evidence.",
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    status="timeout",
                )
            except Exception as exc:
                result = unavailable_result(
                    provider=self,
                    mode=context.mode,
                    code="PROVIDER_ERROR",
                    message=f"Provider failed: {type(exc).__name__}",
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    status="error",
                )

            last_result = result
            if result.status in {"ok", "partial", "cached"}:
                self._record_success(result)
                return result
            self._record_failure(result)
            if attempt < attempts - 1:
                await asyncio.sleep(0.05)

        return last_result or unavailable_result(
            provider=self,
            mode=context.mode,
            code="PROVIDER_ERROR",
            message="Provider failed without returning a result.",
            status="error",
        )

    def health(self, *, mode: str) -> ProviderHealth:
        status = self.metrics_status()
        return ProviderHealth(
            name=self.name,
            enabled=self.enabled,
            configured=self.configured,
            supports_live=self.supports_live,
            status=status,
            last_success=self.last_success,
            last_error_code=self.last_error_code,
            mode_behavior=self.mode_behavior(mode),
        )

    def runtime_metrics(self) -> ProviderRuntimeMetrics:
        avg = self.total_latency_ms / self.success_count if self.success_count else 0
        return ProviderRuntimeMetrics(
            provider_name=self.name,
            enabled=self.enabled,
            configured=self.configured,
            supports_live=self.supports_live,
            status=self.metrics_status(),
            last_success_at=self.last_success,
            last_failure_at=self.last_failure,
            last_error_code=self.last_error_code,
            last_error_message_redacted=self.last_error_message_redacted,
            success_count=self.success_count,
            failure_count=self.failure_count,
            consecutive_failures=self.consecutive_failures,
            average_latency_ms=round(avg, 2),
            last_latency_ms=self.last_latency_ms,
            circuit_state=self.circuit_state,  # type: ignore[arg-type]
            circuit_opened_at=self.circuit_opened_at,
            last_result_source=self.last_result_source,
            last_result_count=self.last_result_count,
            last_fallback_used=self.last_fallback_used,
        )

    def metrics_status(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.circuit_state == "open":
            return "circuit_open"
        if not self.configured:
            return "unavailable"
        if self.consecutive_failures > 0:
            return "partial"
        return "healthy"

    def mode_behavior(self, mode: str) -> str:
        if mode == "demo":
            return "Used only when selected by the evidence pipeline."
        if mode == "hybrid":
            return "Live-capable providers are attempted first; fallback is explicit."
        return "Only live-capable configured providers are used unless demo fallback is explicitly allowed."

    def _circuit_preflight(self, mode: str) -> ProviderResult | None:
        if self.circuit_state != "open" or not self.circuit_opened_at:
            return None
        opened = datetime.fromisoformat(self.circuit_opened_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - opened >= timedelta(seconds=max(1, settings.PROVIDER_CIRCUIT_RESET_SECONDS)):
            self.circuit_state = "half_open"
            return None
        return unavailable_result(
            provider=self,
            mode=mode,
            code="PROVIDER_CIRCUIT_OPEN",
            message="Provider circuit is open after repeated failures.",
            status="circuit_open",
        )

    def _record_success(self, result: ProviderResult) -> None:
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_success = utc_now_iso()
        self.last_error_code = None
        self.last_error_message_redacted = None
        self.last_latency_ms = result.latency_ms
        self.total_latency_ms += result.latency_ms
        self.circuit_state = "closed"
        self.circuit_opened_at = None
        self.last_result_source = result.source
        self.last_result_count = len(result.evidence)
        self.last_fallback_used = result.is_fallback

    def _record_failure(self, result: ProviderResult) -> None:
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure = utc_now_iso()
        error = result.errors[0] if result.errors else {"code": "PROVIDER_ERROR", "message": "Provider failed."}
        self.last_error_code = error.get("code")
        self.last_error_message_redacted = error.get("message")
        self.last_latency_ms = result.latency_ms
        self.last_result_source = result.source
        self.last_result_count = len(result.evidence)
        self.last_fallback_used = result.is_fallback
        if self.consecutive_failures >= max(1, settings.PROVIDER_CIRCUIT_FAILURE_THRESHOLD):
            self.circuit_state = "open"
            self.circuit_opened_at = utc_now_iso()


class provider_timer:
    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.latency_ms = round((time.perf_counter() - self.started) * 1000, 2)
        return False


def iso_from_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def unavailable_result(
    *,
    provider: EvidenceProvider,
    mode: str,
    code: str,
    message: str,
    latency_ms: float = 0,
    status: str = "unavailable",
) -> ProviderResult:
    return ProviderResult(
        provider=provider.name,
        source="unavailable",
        mode=mode,
        generated_at=utc_now_iso(),
        latency_ms=latency_ms,
        status=status,  # type: ignore[arg-type]
        errors=[{"code": code, "message": message}],
    )
