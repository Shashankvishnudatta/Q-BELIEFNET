from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.contracts import utc_now_iso
from app.db.session import db_connection, persistence_enabled
from app.models.schemas import BeliefSnapshot, IngestionRun, ProviderRuntimeMetrics


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def safe_write(operation):
    if not persistence_enabled():
        return None
    try:
        return operation()
    except Exception:
        return None


def save_belief_snapshot(snapshot: BeliefSnapshot) -> None:
    def op():
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO belief_snapshots (
                    symbol, created_at, score, velocity, coherence, fragility, source_agreement,
                    source_mix_json, freshness_summary_json, provider_results_json, evidence_bundle_json,
                    narratives_json, explanation_json, meta_json, mode, is_fallback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.asset.symbol,
                    snapshot.meta.generated_at,
                    snapshot.belief.score,
                    snapshot.belief.velocity,
                    snapshot.belief.coherence,
                    snapshot.belief.fragility,
                    snapshot.breakdown.source_agreement,
                    _json(snapshot.source_mix),
                    _json(snapshot.freshness_summary.model_dump() if snapshot.freshness_summary else {}),
                    _json([result.model_dump() for result in snapshot.provider_results]),
                    _json(snapshot.evidence_bundle.model_dump() if snapshot.evidence_bundle else {}),
                    _json([cluster.model_dump() for cluster in snapshot.narratives]),
                    _json(snapshot.explanation.model_dump()),
                    _json(snapshot.meta.model_dump()),
                    snapshot.meta.mode,
                    1 if snapshot.meta.is_fallback else 0,
                ),
            )
            prune_old_snapshots(snapshot.asset.symbol, conn=conn)
    safe_write(op)


def prune_old_snapshots(symbol: str, *, conn=None) -> None:
    max_rows = max(1, int(settings.MAX_SNAPSHOTS_PER_SYMBOL))
    close_after = False
    if conn is None:
        if not persistence_enabled():
            return
        conn_cm = db_connection()
        conn = conn_cm.__enter__()
        close_after = True
    try:
        conn.execute(
            """
            DELETE FROM belief_snapshots
            WHERE symbol = ?
              AND id NOT IN (
                SELECT id FROM belief_snapshots
                WHERE symbol = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
              )
            """,
            (symbol.upper(), symbol.upper(), max_rows),
        )
    finally:
        if close_after:
            conn_cm.__exit__(None, None, None)


def get_latest_belief_snapshot(symbol: str) -> dict[str, Any] | None:
    if not persistence_enabled():
        return None
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM belief_snapshots WHERE symbol = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (symbol.upper(),),
        ).fetchone()
    return dict(row) if row else None


def get_belief_snapshot_history(symbol: str, limit: int = 30) -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT created_at, score, velocity, coherence, fragility
            FROM belief_snapshots
            WHERE symbol = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def save_ingestion_run(run: IngestionRun, *, trigger_type: str = "background", triggered_by: str | None = None, request_id: str | None = None) -> None:
    def op():
        with db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ingestion_runs (
                    run_id, started_at, finished_at, duration_ms, symbols_requested_json,
                    symbols_succeeded_json, symbols_failed_json, provider_results_summary_json,
                    cache_updates, fallback_count, status, errors_json, triggered_by, trigger_type, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.started_at,
                    run.finished_at,
                    run.duration_ms,
                    _json(run.symbols_requested),
                    _json(run.symbols_succeeded),
                    _json(run.symbols_failed),
                    _json(run.provider_results_summary),
                    run.cache_updates,
                    run.fallback_count,
                    run.status,
                    _json(run.errors),
                    triggered_by,
                    trigger_type,
                    request_id,
                ),
            )
    safe_write(op)


def recent_ingestion_runs(limit: int = 10) -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
    data = []
    for row in rows:
        item = dict(row)
        for key in ("symbols_requested_json", "symbols_succeeded_json", "symbols_failed_json", "provider_results_summary_json", "errors_json"):
            item[key.replace("_json", "")] = _loads(item.pop(key), [] if "symbols" in key or key == "errors_json" else {})
        data.append(item)
    return data


def save_provider_health_event(metric: ProviderRuntimeMetrics) -> None:
    def op():
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO provider_health_events (
                    provider_name, created_at, status, circuit_state, success_count, failure_count,
                    consecutive_failures, average_latency_ms, last_latency_ms, last_error_code,
                    last_error_message_redacted, last_result_source, last_result_count, fallback_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.provider_name,
                    utc_now_iso(),
                    metric.status,
                    metric.circuit_state,
                    metric.success_count,
                    metric.failure_count,
                    metric.consecutive_failures,
                    metric.average_latency_ms,
                    metric.last_latency_ms,
                    metric.last_error_code,
                    metric.last_error_message_redacted,
                    metric.last_result_source,
                    metric.last_result_count,
                    1 if metric.last_fallback_used else 0,
                ),
            )
    safe_write(op)


def recent_provider_health_events(limit: int = 20) -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM provider_health_events ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def save_cache_record(*, cache_key: str, symbol: str, provider: str, mode: str, freshness: dict[str, Any], source_mix: dict[str, int], item_count: int) -> None:
    def op():
        with db_connection() as conn:
            existing = conn.execute("SELECT hit_count FROM evidence_cache_records WHERE cache_key = ?", (cache_key,)).fetchone()
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence_cache_records (
                    cache_key, symbol, provider, mode, cached_at, expires_at, age_seconds, ttl_seconds,
                    stale, served_stale, source_mix_json, freshness_summary_json, item_count, last_accessed_at, hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    symbol,
                    provider,
                    mode,
                    freshness.get("cached_at"),
                    freshness.get("expires_at"),
                    freshness.get("age_seconds"),
                    freshness.get("ttl_seconds"),
                    1 if freshness.get("stale") else 0,
                    1 if freshness.get("served_stale") else 0,
                    _json(source_mix),
                    _json(freshness),
                    item_count,
                    utc_now_iso(),
                    (existing["hit_count"] if existing else 0) + (1 if freshness.get("cache_hit") else 0),
                ),
            )
    safe_write(op)


def cache_record_summary() -> dict[str, int]:
    if not persistence_enabled():
        return {"records": 0, "stale": 0, "served_stale": 0}
    with db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) records, SUM(stale) stale, SUM(served_stale) served_stale FROM evidence_cache_records").fetchone()
    return {"records": int(row["records"] or 0), "stale": int(row["stale"] or 0), "served_stale": int(row["served_stale"] or 0)}


def audit_log(operation: str, *, status: str, triggered_by: str | None = None, request_id: str | None = None, symbol: str | None = None, symbols: list[str] | None = None, details: dict[str, Any] | None = None, error_code: str | None = None) -> None:
    def op():
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO operation_audit_log (
                    created_at, operation, triggered_by, request_id, symbol, symbols_json, status, details_json, error_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (utc_now_iso(), operation, triggered_by, request_id, symbol, _json(symbols or []), status, _json(details or {}), error_code),
            )
    safe_write(op)


def recent_audit_operations(limit: int = 25) -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM operation_audit_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    data = []
    for row in rows:
        item = dict(row)
        item["symbols"] = _loads(item.pop("symbols_json"), [])
        item["details"] = _loads(item.pop("details_json"), {})
        data.append(item)
    return data


def add_watchlist_item(symbol: str, name: str | None = None, notes: str | None = None, pinned: bool = False, source: str = "manual") -> dict[str, Any] | None:
    normalized = symbol.upper()
    def op():
        with db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO watchlist_items(symbol, name, created_at, notes, pinned, source) VALUES (?, ?, COALESCE((SELECT created_at FROM watchlist_items WHERE symbol=?), ?), ?, ?, ?)",
                (normalized, name, normalized, utc_now_iso(), notes, 1 if pinned else 0, source),
            )
    safe_write(op)
    audit_log("watchlist_add", status="success", symbol=normalized, symbols=[normalized], details={"source": source})
    return {"symbol": normalized, "name": name, "notes": notes, "pinned": pinned, "source": source}


def get_watchlist_items() -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM watchlist_items ORDER BY pinned DESC, created_at DESC").fetchall()
    return [dict(row) for row in rows]


def remove_watchlist_item(symbol: str) -> None:
    normalized = symbol.upper()
    def op():
        with db_connection() as conn:
            conn.execute("DELETE FROM watchlist_items WHERE symbol = ?", (normalized,))
    safe_write(op)
    audit_log("watchlist_remove", status="success", symbol=normalized, symbols=[normalized])


def add_portfolio_item(symbol: str, quantity: float, average_cost_optional: float | None = None, notes: str | None = None, is_demo: bool = True) -> dict[str, Any]:
    new_id = None
    def op():
        nonlocal new_id
        with db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO portfolio_items(symbol, quantity, average_cost_optional, created_at, notes, is_demo) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol.upper(), quantity, average_cost_optional, utc_now_iso(), notes, 1 if is_demo else 0),
            )
            new_id = cursor.lastrowid
    safe_write(op)
    audit_log("portfolio_add", status="success", symbol=symbol, symbols=[symbol], details={"quantity": quantity, "is_demo": is_demo})
    return {"id": new_id, "symbol": symbol.upper(), "quantity": quantity, "average_cost_optional": average_cost_optional, "notes": notes, "is_demo": is_demo}


def get_portfolio_items() -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM portfolio_items ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def remove_portfolio_item(item_id: int) -> None:
    def op():
        with db_connection() as conn:
            conn.execute("DELETE FROM portfolio_items WHERE id = ?", (item_id,))
    safe_write(op)
    audit_log("portfolio_remove", status="success", details={"id": item_id})


ALERT_METRICS = {"belief_score", "velocity", "fragility", "coherence", "source_agreement"}


def create_alert_rule(symbol: str, metric: str, operator: str, threshold: float, enabled: bool = True, notes: str | None = None) -> dict[str, Any]:
    if metric not in ALERT_METRICS:
        raise ValueError("Unsupported alert metric.")
    new_id = None
    def op():
        nonlocal new_id
        with db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO alert_rules(symbol, metric, operator, threshold, enabled, created_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (symbol.upper(), metric, operator, threshold, 1 if enabled else 0, utc_now_iso(), notes),
            )
            new_id = cursor.lastrowid
    safe_write(op)
    audit_log("alert_create", status="success", symbol=symbol, symbols=[symbol], details={"metric": metric, "operator": operator, "threshold": threshold})
    return {"id": new_id, "symbol": symbol.upper(), "metric": metric, "operator": operator, "threshold": threshold, "enabled": enabled, "notes": notes}


def get_alert_rules() -> list[dict[str, Any]]:
    if not persistence_enabled():
        return []
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM alert_rules ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def update_alert_rule(rule_id: int, updates: dict[str, Any]) -> None:
    allowed = {key: value for key, value in updates.items() if key in {"enabled", "notes", "threshold", "operator"}}
    if not allowed:
        return
    def op():
        with db_connection() as conn:
            for key, value in allowed.items():
                if key == "enabled":
                    value = 1 if value else 0
                conn.execute(f"UPDATE alert_rules SET {key} = ? WHERE id = ?", (value, rule_id))
    safe_write(op)
    audit_log("alert_update", status="success", details={"id": rule_id, "updates": allowed})


def delete_alert_rule(rule_id: int) -> None:
    def op():
        with db_connection() as conn:
            conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
    safe_write(op)
    audit_log("alert_delete", status="success", details={"id": rule_id})


def workspace_snapshot() -> dict[str, Any]:
    return {
        "watchlist": get_watchlist_items(),
        "portfolio": get_portfolio_items(),
        "alerts": get_alert_rules(),
        "settings": {},
    }
