from fastapi import APIRouter, Request
from app.core.contracts import ApiResponse, infer_market_provenance, require_live_market_config
from app.core.config import settings
from app.models.schemas import StockDetail
from app.services.mock_data import generate_mock_stock_data
from app.services.market_data import build_stock_detail
from app.core.middleware import limiter, RATE_LIMITING_AVAILABLE

router = APIRouter()

async def stock_detail_handler(ticker: str):
    normalized = ticker.strip().upper()
    if not normalized or len(normalized) > 8 or not normalized.replace(".", "").isalnum():
        from app.core.contracts import AppHTTPException
        raise AppHTTPException(
            status_code=400,
            code="INVALID_TICKER",
            message="Ticker must be a short alphanumeric symbol.",
            details={"ticker": ticker},
        )

    if settings.DATA_MODE == "demo":
        data = generate_mock_stock_data(normalized)
    else:
        require_live_market_config()
        data = await build_stock_detail(normalized)
    return ApiResponse[StockDetail](
        data=data,
        meta=infer_market_provenance(
            data,
            fallback_provider="internal-demo-generator",
            live_provider="rapidapi-yahoo-finance-social-sources",
        ),
    )

if RATE_LIMITING_AVAILABLE:
    @router.get("/{ticker}", response_model=ApiResponse[StockDetail])
    @limiter.limit("20/minute")
    async def get_stock_detail(request: Request, ticker: str):
        return await stock_detail_handler(ticker)
else:
    @router.get("/{ticker}", response_model=ApiResponse[StockDetail])
    async def get_stock_detail(request: Request, ticker: str):
        return await stock_detail_handler(ticker)
