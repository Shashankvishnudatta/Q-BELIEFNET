from __future__ import annotations

from fastapi import APIRouter, Request

from app.db.repository import recent_provider_health_events
from app.services.evidence_pipeline import provider_status_payload

router = APIRouter()


@router.get("/status")
async def get_provider_status(request: Request):
    payload = provider_status_payload()
    payload["recent_events"] = recent_provider_health_events(limit=20)
    return payload
