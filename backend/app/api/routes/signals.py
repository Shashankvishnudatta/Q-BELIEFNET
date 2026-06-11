from fastapi import APIRouter, Request
from typing import List
from app.core.contracts import ApiResponse, infer_market_provenance, require_live_market_config
from app.core.config import settings
from app.models.schemas import Signal
from app.services.market_data import build_market_signals
from app.core.middleware import limiter, RATE_LIMITING_AVAILABLE

router = APIRouter()

async def signals_handler(request: Request):
    if settings.DATA_MODE == "demo":
        data = [
            {
                "id": "demo-signal-1",
                "type": "demo",
                "title": "Demo signal: AI narrative momentum",
                "description": "Generated prototype signal showing how market-belief alerts appear in demo mode.",
                "impact": "medium",
                "timestamp": "demo",
            }
        ]
    else:
        require_live_market_config()
        data = await build_market_signals()
    return ApiResponse[List[Signal]](
        data=data,
        meta=infer_market_provenance(
            data,
            fallback_provider="internal-demo-generator",
            live_provider="social-and-market-data-providers",
        ),
    )

if RATE_LIMITING_AVAILABLE:
    @router.get("", response_model=ApiResponse[List[Signal]])
    @limiter.limit("10/minute")
    async def get_signals(request: Request):
        return await signals_handler(request)
else:
    @router.get("", response_model=ApiResponse[List[Signal]])
    async def get_signals(request: Request):
        return await signals_handler(request)
