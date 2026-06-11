from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import settings

_available = False
_last_error: str | None = None


def _sqlite_path() -> Path:
    url = settings.DATABASE_URL
    if not url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported in local persistence mode.")
    raw = url.replace("sqlite:///", "", 1)
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd().parent / path if Path.cwd().name == "backend" else Path.cwd() / path
    return path


def persistence_enabled() -> bool:
    return bool(settings.ENABLE_PERSISTENCE and settings.PERSISTENCE_MODE == "sqlite")


def persistence_status() -> dict[str, object]:
    return {
        "enabled": bool(settings.ENABLE_PERSISTENCE),
        "available": _available if persistence_enabled() else False,
        "mode": settings.PERSISTENCE_MODE,
        "database": "configured" if settings.DATABASE_URL else "not-configured",
        "last_error": _last_error,
        "stores": {
            "belief_snapshots": True,
            "ingestion_runs": True,
            "provider_health": True,
            "evidence_cache": True,
            "workspace": True,
            "audit_log": True,
        },
    }


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    if not persistence_enabled():
        raise RuntimeError("Persistence is disabled.")
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def mark_available(value: bool, error: str | None = None) -> None:
    global _available, _last_error
    _available = value
    _last_error = error
