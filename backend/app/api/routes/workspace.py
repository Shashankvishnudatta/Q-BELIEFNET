from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.websockets import publish_message
from app.core.contracts import ApiResponse, AppHTTPException, make_provenance
from app.db.repository import (
    add_portfolio_item,
    add_watchlist_item,
    create_alert_rule,
    delete_alert_rule,
    get_alert_rules,
    get_portfolio_items,
    get_watchlist_items,
    remove_portfolio_item,
    remove_watchlist_item,
    update_alert_rule,
    workspace_snapshot,
)

router = APIRouter()
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
ALERT_OPERATORS = {">", ">=", "<", "<=", "=="}


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(normalized):
        raise AppHTTPException(
            status_code=400,
            code="INVALID_SYMBOL",
            message="Ticker symbols must be 1-10 uppercase letters, numbers, dots, or dashes.",
            details={"symbol": symbol},
        )
    return normalized


def _workspace_meta(notes: str):
    return make_provenance(source="cached", provider="sqlite-workspace-store", notes=notes, confidence="prototype")


async def _broadcast_workspace_event(event_type: str, payload: dict[str, Any]) -> None:
    await publish_message(
        {
            "type": event_type,
            "payload": payload,
            "meta": _workspace_meta("Workspace persistence event broadcast from local SQLite-backed routes.").model_dump(),
        }
    )


class WatchlistItemCreate(BaseModel):
    symbol: str
    name: str | None = None
    notes: str | None = None
    pinned: bool = False


class PortfolioItemCreate(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    average_cost_optional: float | None = Field(default=None, ge=0)
    notes: str | None = None
    is_demo: bool = True


class AlertRuleCreate(BaseModel):
    symbol: str
    metric: str
    operator: str
    threshold: float
    enabled: bool = True
    notes: str | None = None


class AlertRuleUpdate(BaseModel):
    operator: str | None = None
    threshold: float | None = None
    enabled: bool | None = None
    notes: str | None = None


@router.get("/workspace")
async def get_workspace(request: Request):
    return ApiResponse[dict[str, Any]](
        data=workspace_snapshot(),
        meta=_workspace_meta("Local durable workspace snapshot. This is not a trading account."),
    )


@router.get("/watchlist")
async def get_watchlist(request: Request):
    return ApiResponse[list[dict[str, Any]]](
        data=get_watchlist_items(),
        meta=_workspace_meta("Persisted local watchlist from SQLite when persistence is enabled."),
    )


@router.post("/watchlist")
async def post_watchlist_item(request: Request, payload: WatchlistItemCreate):
    symbol = _normalize_symbol(payload.symbol)
    item = add_watchlist_item(symbol, name=payload.name, notes=payload.notes, pinned=payload.pinned, source="manual")
    await _broadcast_workspace_event("workspace_updated", {"operation": "watchlist_add", "symbol": symbol})
    await _broadcast_workspace_event("operation_audit_created", {"operation": "watchlist_add", "symbol": symbol})
    return ApiResponse[dict[str, Any]](
        data=item or {"symbol": symbol},
        meta=_workspace_meta("Watchlist item persisted locally."),
    )


@router.delete("/watchlist/{symbol}")
async def delete_watchlist_item(request: Request, symbol: str):
    normalized = _normalize_symbol(symbol)
    remove_watchlist_item(normalized)
    await _broadcast_workspace_event("workspace_updated", {"operation": "watchlist_remove", "symbol": normalized})
    await _broadcast_workspace_event("operation_audit_created", {"operation": "watchlist_remove", "symbol": normalized})
    return ApiResponse[dict[str, str]](
        data={"symbol": normalized, "status": "removed"},
        meta=_workspace_meta("Watchlist item removed from local workspace store."),
    )


@router.get("/portfolio")
async def get_portfolio(request: Request):
    return ApiResponse[list[dict[str, Any]]](
        data=get_portfolio_items(),
        meta=_workspace_meta("Persisted local tracking portfolio. This is not brokerage or trading data."),
    )


@router.post("/portfolio")
async def post_portfolio_item(request: Request, payload: PortfolioItemCreate):
    symbol = _normalize_symbol(payload.symbol)
    item = add_portfolio_item(
        symbol,
        quantity=payload.quantity,
        average_cost_optional=payload.average_cost_optional,
        notes=payload.notes,
        is_demo=payload.is_demo,
    )
    await _broadcast_workspace_event("workspace_updated", {"operation": "portfolio_add", "symbol": symbol})
    await _broadcast_workspace_event("operation_audit_created", {"operation": "portfolio_add", "symbol": symbol})
    return ApiResponse[dict[str, Any]](data=item, meta=_workspace_meta("Tracking portfolio item persisted locally."))


@router.delete("/portfolio/{item_id}")
async def delete_portfolio_item(request: Request, item_id: int):
    remove_portfolio_item(item_id)
    await _broadcast_workspace_event("workspace_updated", {"operation": "portfolio_remove", "id": item_id})
    return ApiResponse[dict[str, Any]](
        data={"id": item_id, "status": "removed"},
        meta=_workspace_meta("Tracking portfolio item removed from local workspace store."),
    )


@router.get("/alert-rules")
async def get_workspace_alert_rules(request: Request):
    return ApiResponse[list[dict[str, Any]]](
        data=get_alert_rules(),
        meta=_workspace_meta("Persisted local alert rules for belief metrics. No external notifications are sent."),
    )


@router.post("/alert-rules")
async def post_workspace_alert_rule(request: Request, payload: AlertRuleCreate):
    symbol = _normalize_symbol(payload.symbol)
    if payload.operator not in ALERT_OPERATORS:
        raise AppHTTPException(status_code=400, code="INVALID_ALERT_OPERATOR", message="Unsupported alert operator.", details={"operator": payload.operator})
    try:
        item = create_alert_rule(symbol, payload.metric, payload.operator, payload.threshold, enabled=payload.enabled, notes=payload.notes)
    except ValueError as exc:
        raise AppHTTPException(status_code=400, code="INVALID_ALERT_METRIC", message=str(exc), details={"metric": payload.metric}) from exc
    await _broadcast_workspace_event("workspace_updated", {"operation": "alert_create", "symbol": symbol})
    return ApiResponse[dict[str, Any]](data=item, meta=_workspace_meta("Belief-metric alert rule persisted locally."))


@router.patch("/alert-rules/{rule_id}")
async def patch_workspace_alert_rule(request: Request, rule_id: int, payload: AlertRuleUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if "operator" in updates and updates["operator"] not in ALERT_OPERATORS:
        raise AppHTTPException(status_code=400, code="INVALID_ALERT_OPERATOR", message="Unsupported alert operator.", details={"operator": updates["operator"]})
    update_alert_rule(rule_id, updates)
    await _broadcast_workspace_event("workspace_updated", {"operation": "alert_update", "id": rule_id})
    return ApiResponse[dict[str, Any]](
        data={"id": rule_id, "status": "updated"},
        meta=_workspace_meta("Belief-metric alert rule updated locally."),
    )


@router.delete("/alert-rules/{rule_id}")
async def delete_workspace_alert_rule(request: Request, rule_id: int):
    delete_alert_rule(rule_id)
    await _broadcast_workspace_event("workspace_updated", {"operation": "alert_delete", "id": rule_id})
    return ApiResponse[dict[str, Any]](
        data={"id": rule_id, "status": "removed"},
        meta=_workspace_meta("Belief-metric alert rule removed from local workspace store."),
    )
