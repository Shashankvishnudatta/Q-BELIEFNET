from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.contracts import AppHTTPException
from app.services.background_refresh import ingestion_status_payload, refresh_symbols

router = APIRouter()


class ManualRefreshRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


@router.get("/status")
async def get_ingestion_status(request: Request):
    return ingestion_status_payload()


@router.post("/refresh")
async def manual_refresh(request: Request, payload: ManualRefreshRequest):
    if not settings.ENABLE_MANUAL_REFRESH:
        raise AppHTTPException(status_code=403, code="MANUAL_REFRESH_DISABLED", message="Manual refresh is disabled.", details={})
    if len(payload.symbols) > settings.MAX_MANUAL_REFRESH_SYMBOLS:
        raise AppHTTPException(
            status_code=400,
            code="TOO_MANY_SYMBOLS",
            message="Manual refresh requested too many symbols.",
            details={"max_symbols": settings.MAX_MANUAL_REFRESH_SYMBOLS},
        )
    if settings.REQUIRE_MANUAL_REFRESH_TOKEN:
        supplied = request.headers.get("X-QBN-Admin-Token")
        if not settings.MANUAL_REFRESH_TOKEN or supplied != settings.MANUAL_REFRESH_TOKEN:
            raise AppHTTPException(status_code=403, code="MANUAL_REFRESH_TOKEN_REQUIRED", message="Valid manual refresh token is required.", details={})
    run = await refresh_symbols(
        payload.symbols,
        trigger_type="manual",
        triggered_by="local-user",
        request_id=getattr(request.state, "request_id", None),
    )
    return {"data": run.model_dump(), "meta": {"mode": "manual", "message": "Manual refresh completed. Auth is required before production use."}}
