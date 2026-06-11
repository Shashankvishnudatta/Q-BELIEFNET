from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from app.core.config import settings
from app.core.contracts import AppHTTPException, utc_now_iso
from app.core.logging import logger
from app.models.schemas import IngestionRun
from app.services.evidence_pipeline import build_evidence_bundle, provider_status_payload, validate_pipeline_symbol
from app.services.providers.cache import evidence_cache
from app.db.repository import audit_log, recent_ingestion_runs, save_ingestion_run

MAX_RUN_HISTORY = 20
recent_runs: list[IngestionRun] = []
current_run: IngestionRun | None = None


def configured_refresh_symbols() -> list[str]:
    symbols = [item.strip().upper() for item in settings.BACKGROUND_REFRESH_SYMBOLS.split(",") if item.strip()]
    return [validate_pipeline_symbol(symbol) for symbol in symbols[:20]]


async def refresh_symbols(symbols: list[str] | None = None, *, trigger_type: str = "background", triggered_by: str | None = None, request_id: str | None = None) -> IngestionRun:
    global current_run
    normalized = [validate_pipeline_symbol(symbol) for symbol in (symbols or configured_refresh_symbols())][:20]
    if not normalized:
        raise AppHTTPException(
            status_code=400,
            code="NO_REFRESH_SYMBOLS",
            message="At least one valid symbol is required for refresh.",
            details={},
        )

    started = time.perf_counter()
    run = IngestionRun(
        run_id=str(uuid4()),
        started_at=utc_now_iso(),
        symbols_requested=normalized,
    )
    current_run = run
    for symbol in normalized:
        try:
            bundle = await build_evidence_bundle(symbol)
            run.symbols_succeeded.append(symbol)
            run.fallback_count += bundle.source_mix.get("fallback", 0)
            run.cache_updates += sum(1 for result in bundle.provider_results if not result.is_cached and result.status in {"ok", "partial"})
            for result in bundle.provider_results:
                run.provider_results_summary[result.provider] = run.provider_results_summary.get(result.provider, 0) + len(result.evidence)
        except Exception as exc:
            run.symbols_failed.append(symbol)
            run.errors.append({"code": type(exc).__name__, "message": "Refresh failed for symbol."})
            logger.warning("Background refresh failed for %s: %s", symbol, type(exc).__name__)

    run.finished_at = utc_now_iso()
    run.duration_ms = round((time.perf_counter() - started) * 1000, 2)
    run.status = "success" if not run.symbols_failed else "partial" if run.symbols_succeeded else "failed"
    recent_runs.insert(0, run)
    del recent_runs[MAX_RUN_HISTORY:]
    save_ingestion_run(run, trigger_type=trigger_type, triggered_by=triggered_by, request_id=request_id)
    audit_log(
        f"{trigger_type}_refresh" if trigger_type in {"manual", "background"} else "background_refresh",
        status=run.status,
        triggered_by=triggered_by,
        request_id=request_id,
        symbols=normalized,
        details={"fallback_count": run.fallback_count, "cache_updates": run.cache_updates},
    )
    current_run = None
    return run


async def background_refresh_loop() -> None:
    while True:
        if settings.ENABLE_BACKGROUND_REFRESH:
            try:
                await refresh_symbols(trigger_type="background", triggered_by="scheduler")
            except Exception as exc:
                logger.warning("Background refresh cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(max(5, int(settings.BACKGROUND_REFRESH_INTERVAL_SECONDS)))


def ingestion_status_payload() -> dict[str, object]:
    persisted_runs = recent_ingestion_runs(limit=10)
    return {
        "scheduler_enabled": bool(settings.ENABLE_BACKGROUND_REFRESH),
        "interval_seconds": int(settings.BACKGROUND_REFRESH_INTERVAL_SECONDS),
        "symbols": configured_refresh_symbols(),
        "current_run": current_run.model_dump() if current_run else None,
        "last_run": persisted_runs[0] if persisted_runs else recent_runs[0].model_dump() if recent_runs else None,
        "recent_runs": persisted_runs or [run.model_dump() for run in recent_runs[:10]],
        "cache_summary": evidence_cache.summary(),
        "provider_health_summary": provider_status_payload().get("health_summary", {}),
    }
