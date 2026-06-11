from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query, Request

from app.core.config import settings
from app.core.contracts import ApiResponse, AppHTTPException, live_market_configured, make_provenance
from app.models.schemas import BeliefHistoryPoint, BeliefSnapshot
import asyncio

from app.db.repository import audit_log, get_belief_snapshot_history, save_belief_snapshot
from app.services.belief_engine import build_belief_history, build_belief_snapshot_async

router = APIRouter()


def _ensure_belief_mode_is_available() -> None:
    if settings.DATA_MODE == "live" and not live_market_configured() and not settings.ALLOW_LIVE_MODE_DEMO_FALLBACK:
        raise AppHTTPException(
            status_code=503,
            code="BELIEF_EVIDENCE_UNAVAILABLE",
            message="Belief evidence is unavailable in live mode because provider credentials are missing.",
            details={"required": ["RAPIDAPI_KEY"], "fallback_available_in": ["demo", "hybrid"]},
        )


def _belief_route_meta():
    source = "generated"
    is_fallback = False
    notes = "Deterministic prototype belief analytics derived from synthetic demo evidence."
    if settings.DATA_MODE in {"hybrid", "live"}:
        source = "fallback"
        is_fallback = True
        notes = "Belief analytics are generated fallback data until live evidence aggregation is connected."
    return make_provenance(
        source=source,
        provider="belief-engine-v1",
        is_fallback=is_fallback,
        notes=notes,
        confidence="prototype",
    )


@router.get("/trending", response_model=ApiResponse[List[BeliefSnapshot]])
async def get_trending_beliefs(request: Request, limit: int = Query(default=8, ge=1, le=20)):
    _ensure_belief_mode_is_available()
    universe = [ticker.strip().upper() for ticker in settings.MARKET_DATA_TICKERS.split(",") if ticker.strip()]
    data = await asyncio.gather(*[build_belief_snapshot_async(symbol) for symbol in universe[: max(limit * 2, limit)]])
    data = sorted(data, key=lambda item: (item.belief.score, abs(item.belief.velocity)), reverse=True)[:limit]
    for snapshot in data:
        save_belief_snapshot(snapshot)
    return ApiResponse[List[BeliefSnapshot]](data=data, meta=_belief_route_meta())


@router.get("/{symbol}", response_model=ApiResponse[BeliefSnapshot])
async def get_belief_snapshot(request: Request, symbol: str):
    _ensure_belief_mode_is_available()
    snapshot = await build_belief_snapshot_async(symbol)
    save_belief_snapshot(snapshot)
    audit_log(
        "belief_snapshot_generated",
        status="success",
        symbol=snapshot.asset.symbol,
        symbols=[snapshot.asset.symbol],
        request_id=getattr(request.state, "request_id", None),
        details={"score": snapshot.belief.score, "mode": snapshot.meta.mode, "is_fallback": snapshot.meta.is_fallback},
    )
    return ApiResponse[BeliefSnapshot](data=snapshot, meta=snapshot.meta)


@router.get("/{symbol}/history", response_model=ApiResponse[List[BeliefHistoryPoint]])
async def get_belief_history(request: Request, symbol: str, days: int = Query(default=14, ge=3, le=30)):
    _ensure_belief_mode_is_available()
    persisted = get_belief_snapshot_history(symbol, limit=days)
    if persisted:
        data = [
            BeliefHistoryPoint(
                timestamp=item["created_at"],
                score=item["score"],
                velocity=item["velocity"],
                coherence=item["coherence"],
                fragility=item["fragility"],
            )
            for item in persisted
        ]
        return ApiResponse[List[BeliefHistoryPoint]](
            data=data,
            meta=make_provenance(
                source="cached",
                provider="sqlite-belief-snapshot-store",
                notes="Persisted belief snapshot history from local SQLite store.",
                confidence="prototype",
            ),
        )
    data = build_belief_history(symbol, days=days)
    return ApiResponse[List[BeliefHistoryPoint]](data=data, meta=_belief_route_meta())
