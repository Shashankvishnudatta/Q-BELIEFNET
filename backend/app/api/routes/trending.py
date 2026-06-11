import asyncio

from fastapi import APIRouter, Request
from typing import List
from app.core.contracts import ApiResponse, infer_market_provenance, require_live_market_config
from app.core.config import settings
from app.models.schemas import TrendingStock
from app.services.market_data import build_trending_stocks
from app.services.mock_data import generate_mock_trending_data
from app.core.middleware import limiter, RATE_LIMITING_AVAILABLE

router = APIRouter()

async def trending_handler():
    if settings.DATA_MODE == "demo":
        data = generate_mock_trending_data()
        return ApiResponse[List[TrendingStock]](
            data=data,
            meta=infer_market_provenance(
                data,
                fallback_provider="internal-demo-generator",
                live_provider="rapidapi-yahoo-finance",
            ),
        )

    require_live_market_config()
    try:
        data = await asyncio.wait_for(build_trending_stocks(), timeout=4.0)
    except asyncio.TimeoutError:
        data = generate_mock_trending_data()

    return ApiResponse[List[TrendingStock]](
        data=data,
        meta=infer_market_provenance(
            data,
            fallback_provider="internal-demo-generator",
            live_provider="rapidapi-yahoo-finance",
        ),
    )

if RATE_LIMITING_AVAILABLE:
    @router.get("", response_model=ApiResponse[List[TrendingStock]])
    @limiter.limit("10/minute")
    async def get_trending(request: Request):
        return await trending_handler()
else:
    @router.get("", response_model=ApiResponse[List[TrendingStock]])
    async def get_trending(request: Request):
        return await trending_handler()
