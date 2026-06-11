from __future__ import annotations

from app.core.logging import logger
from app.db.session import db_connection, mark_available, persistence_enabled


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS belief_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        created_at TEXT NOT NULL,
        score INTEGER NOT NULL,
        velocity REAL NOT NULL,
        coherence REAL NOT NULL,
        fragility REAL NOT NULL,
        source_agreement REAL NOT NULL,
        source_mix_json TEXT NOT NULL,
        freshness_summary_json TEXT NOT NULL,
        provider_results_json TEXT NOT NULL,
        evidence_bundle_json TEXT NOT NULL,
        narratives_json TEXT NOT NULL,
        explanation_json TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        mode TEXT NOT NULL,
        is_fallback INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_belief_snapshots_symbol_created ON belief_snapshots(symbol, created_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS ingestion_runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        duration_ms REAL NOT NULL,
        symbols_requested_json TEXT NOT NULL,
        symbols_succeeded_json TEXT NOT NULL,
        symbols_failed_json TEXT NOT NULL,
        provider_results_summary_json TEXT NOT NULL,
        cache_updates INTEGER NOT NULL,
        fallback_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        errors_json TEXT NOT NULL,
        triggered_by TEXT,
        trigger_type TEXT NOT NULL,
        request_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_health_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        circuit_state TEXT NOT NULL,
        success_count INTEGER NOT NULL,
        failure_count INTEGER NOT NULL,
        consecutive_failures INTEGER NOT NULL,
        average_latency_ms REAL NOT NULL,
        last_latency_ms REAL NOT NULL,
        last_error_code TEXT,
        last_error_message_redacted TEXT,
        last_result_source TEXT,
        last_result_count INTEGER NOT NULL,
        fallback_used INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_cache_records (
        cache_key TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        provider TEXT NOT NULL,
        mode TEXT NOT NULL,
        cached_at TEXT,
        expires_at TEXT,
        age_seconds REAL,
        ttl_seconds INTEGER,
        stale INTEGER NOT NULL DEFAULT 0,
        served_stale INTEGER NOT NULL DEFAULT 0,
        source_mix_json TEXT NOT NULL,
        freshness_summary_json TEXT NOT NULL,
        item_count INTEGER NOT NULL,
        last_accessed_at TEXT,
        hit_count INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workspace_settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT,
        created_at TEXT NOT NULL,
        notes TEXT,
        pinned INTEGER NOT NULL DEFAULT 0,
        source TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        quantity REAL NOT NULL,
        average_cost_optional REAL,
        created_at TEXT NOT NULL,
        notes TEXT,
        is_demo INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        metric TEXT NOT NULL,
        operator TEXT NOT NULL,
        threshold REAL NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        last_triggered_at TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS operation_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        operation TEXT NOT NULL,
        triggered_by TEXT,
        request_id TEXT,
        symbol TEXT,
        symbols_json TEXT NOT NULL,
        status TEXT NOT NULL,
        details_json TEXT NOT NULL,
        error_code TEXT
    )
    """,
]


def init_db() -> None:
    if not persistence_enabled():
        mark_available(False, None)
        return
    try:
        with db_connection() as conn:
            for statement in SCHEMA:
                conn.execute(statement)
        mark_available(True, None)
    except Exception as exc:
        logger.warning("SQLite persistence unavailable: %s", type(exc).__name__)
        mark_available(False, type(exc).__name__)
