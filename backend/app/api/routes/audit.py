from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.core.contracts import ApiResponse, make_provenance
from app.db.repository import recent_audit_operations

router = APIRouter()


@router.get("/operations")
async def get_operation_audit(request: Request, limit: int = Query(default=25, ge=1, le=100)):
    return ApiResponse[list[dict[str, Any]]](
        data=recent_audit_operations(limit=limit),
        meta=make_provenance(
            source="cached",
            provider="sqlite-operation-audit-log",
            notes="Recent local operation audit records. Secrets and tokens are not stored.",
            confidence="prototype",
        ),
    )
