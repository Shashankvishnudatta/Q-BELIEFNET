from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import trending, stock, signals, alerts, llm, belief, providers, ingestion, workspace, audit
from app.api.websockets import router as ws_router, background_task, memory_safety_task, latency_test_task, redis_listener, heartbeat_task
from app.core.config import settings
from app.core.contracts import get_request_id
from app.core.middleware import add_middlewares
from app.core.logging import logger
from app.services.evidence_pipeline import provider_status_payload
from app.services.background_refresh import background_refresh_loop, ingestion_status_payload
from app.db.init_db import init_db
from app.db.session import persistence_status
from app.db.repository import cache_record_summary
from fastapi.responses import JSONResponse
import asyncio
import socket
import os

try:
    from app.services.ingestion.scheduler import ingestion_worker
except Exception as exc:
    logger.warning(f"Ingestion worker disabled: {exc}")
    ingestion_worker = None

try:
    from app.services.processing.worker import processing_worker
except Exception as exc:
    logger.warning(f"Processing worker disabled: {exc}")
    processing_worker = None

try:
    from app.services.processing.embedding_worker import embedding_worker_loop
except Exception as exc:
    logger.warning(f"Embedding worker disabled: {exc}")
    embedding_worker_loop = None

try:
    from app.services.processing.metrics_worker import metrics_worker_loop
except Exception as exc:
    logger.warning(f"Metrics worker disabled: {exc}")
    metrics_worker_loop = None

logger.info("Module imports completed successfully. Creating FastAPI app.")
init_db()

background_tasks: list[asyncio.Task] = []

app = FastAPI(
    title="Q-Belief Net API",
    description="Financial belief intelligence system API",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middlewares (logging, rate limiting)
add_middlewares(app)

# Include routers
app.include_router(trending.router, prefix="/api/trending", tags=["trending"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(belief.router, prefix="/api/belief", tags=["belief"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(workspace.router, prefix="/api", tags=["workspace"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(ws_router, tags=["websocket"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception from {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "details": {},
                "request_id": get_request_id(request),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get("code", "HTTP_ERROR")
    message = detail.get("message", str(exc.detail))
    details = detail.get("details", {})
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": get_request_id(request),
            }
        },
        headers=getattr(exc, "headers", None),
    )


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Q-Belief Net API",
        "version": app.version,
        "app_mode": settings.APP_MODE,
        "data_mode": settings.DATA_MODE,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": app.version,
    }


@app.get("/api/status")
async def api_status():
    redis_available = redis_is_available()
    provider_status = provider_status_payload()
    evidence_cache_status = dict(provider_status["evidence_cache"])
    evidence_cache_status["persistent_records"] = cache_record_summary()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": app.version,
        "app_mode": settings.APP_MODE,
        "app_env": settings.APP_ENV,
        "data_mode": settings.DATA_MODE,
        "redis": {
            "configured": bool(settings.REDIS_URL),
            "available": redis_available,
        },
        "llm": {
            "configured": bool(settings.HF_API_KEY),
            "provider": "huggingface",
            "model": settings.HF_MODEL_ID or "not-configured",
        },
        "features": {
            "websocket": True,
            "market_data": settings.DATA_MODE,
            "belief_engine": "prototype",
            "evidence_pipeline": "enabled",
            "alerts": "demo",
            "portfolio": "demo",
            "reports": "demo",
            "embeddings": "partial",
            "redis_processing": "optional",
        },
        "providers": provider_status["providers"],
        "provider_health": provider_status.get("health_summary", {}),
        "evidence_cache": evidence_cache_status,
        "ingestion": {
            "scheduler_enabled": ingestion_status_payload()["scheduler_enabled"],
            "interval_seconds": ingestion_status_payload()["interval_seconds"],
            "last_run": ingestion_status_payload()["last_run"],
        },
        "persistence": persistence_status(),
        "manual_refresh": {
            "enabled": settings.ENABLE_MANUAL_REFRESH,
            "requires_token": settings.REQUIRE_MANUAL_REFRESH_TOKEN,
        },
    }


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


def redis_is_available(redis_url: str | None = None, host: str = "localhost", port: int = 6379, timeout: float = 0.5) -> bool:
    try:
        # Prefer explicit REDIS_URL from settings or env when present
        from urllib.parse import urlparse

        url = redis_url or getattr(settings, 'REDIS_URL', None) or os.getenv('REDIS_URL')
        if url:
            parsed = urlparse(url)
            host = parsed.hostname or host
            port = parsed.port or port

        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def create_background_task(coro, name: str) -> None:
    task = asyncio.create_task(coro, name=name)
    background_tasks.append(task)

@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Executing startup event...")
        init_db()
        redis_available = redis_is_available()
        logger.info(f"Redis available: {redis_available}")
        create_background_task(background_task(), "ws-demo-broadcast")
        if ingestion_worker:
            create_background_task(ingestion_worker(), "ingestion-worker")
        if processing_worker and redis_available:
            create_background_task(processing_worker(), "processing-worker")
        if embedding_worker_loop and redis_available:
            create_background_task(embedding_worker_loop(), "embedding-worker")
        if metrics_worker_loop and redis_available:
            create_background_task(metrics_worker_loop(), "metrics-worker")
        elif not redis_available:
            logger.info("Redis is unavailable; skipping processing, embedding, metrics, and Redis listener tasks.")
        create_background_task(memory_safety_task(), "ws-memory-safety")
        create_background_task(latency_test_task(), "ws-latency-test")
        if redis_available:
            create_background_task(redis_listener(), "redis-listener")
        create_background_task(heartbeat_task(), "ws-heartbeat")
        create_background_task(background_refresh_loop(), "evidence-background-refresh")
    except Exception as e:
        logger.error("Startup event failed", exc_info=True)
        logger.info("App startup completed despite errors.")


@app.on_event("shutdown")
async def shutdown_event():
    for task in background_tasks:
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
        background_tasks.clear()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
