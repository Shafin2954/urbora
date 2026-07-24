"""Session + farm persistence — SQLite, WAL mode (NOTES #13, PLAN §1).

Minimal viable slice needed to make `/api/chat` actually work: a session's
conversation history must survive between HTTP requests (each POST is a fresh
process-level call with no shared Python object), so `backend.agent.loop.run_turn`
loads it here, appends the new turn, and saves it back.

`farms` exists for the Tier 1 "returning farmer" memory feature (PRD §4/§8) —
schema only for now; the loop does not yet inject a stored FarmProfile into
context. Tracked honestly as not-yet-wired rather than half-built silently.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "memory.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            messages_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS farms (
            farm_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    return conn


def get_session_messages(session_id: str) -> list[dict]:
    """Return the session's stored conversation history (native provider
    message dicts), or [] for a brand-new session."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT messages_json FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        return json.loads(row[0]) if row else []
    finally:
        conn.close()


def save_session_messages(session_id: str, messages: list[dict]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (session_id, messages_json, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "messages_json=excluded.messages_json, updated_at=excluded.updated_at",
            (session_id, json.dumps(messages, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_farm(farm_id: str) -> dict | None:
    """Stored FarmProfile fields for `farm_id`, or None if never saved. Never
    fabricate a farm — a miss means the loop proceeds without seeded context."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT profile_json FROM farms WHERE farm_id=?", (farm_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def save_farm(farm_id: str, profile: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO farms (farm_id, profile_json, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(farm_id) DO UPDATE SET "
            "profile_json=excluded.profile_json, updated_at=excluded.updated_at",
            (farm_id, json.dumps(profile, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()
