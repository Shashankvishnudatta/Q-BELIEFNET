from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings

DataSource = Literal["live", "mock", "generated", "cached", "fallback", "unavailable"]
Confidence = Literal["prototype", "low", "medium", "high"]
T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ProvenanceMeta(BaseModel):
    source: DataSource
    mode: str = Field(default_factory=lambda: settings.DATA_MODE)
    generated_at: str = Field(default_factory=utc_now_iso)
    is_fallback: bool = False
    provider: str
    confidence: Confidence = "prototype"
    notes: str


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ProvenanceMeta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppHTTPException(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
                "details": details or {},
            },
        )


def get_request_id(request: Request | None = None) -> str:
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            return str(request_id)
    return str(uuid4())


def make_provenance(
    *,
    source: DataSource,
    provider: str,
    is_fallback: bool = False,
    notes: str,
    confidence: Confidence = "prototype",
    mode: str | None = None,
) -> ProvenanceMeta:
    return ProvenanceMeta(
        source=source,
        mode=mode or settings.DATA_MODE,
        is_fallback=is_fallback,
        provider=provider,
        confidence=confidence,
        notes=notes,
    )


def live_market_configured() -> bool:
    return bool(settings.RAPIDAPI_KEY)


def require_live_market_config() -> None:
    if settings.DATA_MODE == "live" and not live_market_configured():
        raise AppHTTPException(
            status_code=503,
            code="MARKET_DATA_UNAVAILABLE",
            message="Market data is unavailable in live mode because provider credentials are missing.",
            details={"required": ["RAPIDAPI_KEY"]},
        )


def infer_market_provenance(data: Any, *, fallback_provider: str, live_provider: str) -> ProvenanceMeta:
    if settings.DATA_MODE == "demo":
        return make_provenance(
            source="generated",
            provider=fallback_provider,
            notes="Demo-generated market-belief data for product exploration.",
        )

    if settings.DATA_MODE == "live":
        return make_provenance(
            source="live",
            provider=live_provider,
            notes="Live-mode response from configured market-data provider.",
            confidence="low",
        )

    def has_live_marker(item: Any) -> bool:
        return isinstance(item, dict) and item.get("source") not in (None, "", "mock", "generated")

    if isinstance(data, list):
        has_live = any(has_live_marker(item) for item in data)
    else:
        has_live = has_live_marker(data)

    if has_live:
        return make_provenance(
            source="live",
            provider=live_provider,
            notes="Hybrid mode used live-capable provider data where available.",
            confidence="low",
        )

    return make_provenance(
        source="fallback",
        provider=fallback_provider,
        is_fallback=True,
        notes="Hybrid mode fell back to generated demo data because live data was unavailable.",
    )
