"""Session + farm persistence — SQLite, WAL mode (NOTES #13, PLAN §1).

Minimal viable slice needed to make `/api/chat` actually work: a session's
conversation history must survive between HTTP requests (each POST is a fresh
process-level call with no shared Python object), so `backend.agent.loop.run_turn`
loads it here, appends the new turn, and saves it back.

`farms` exists for the Tier 1 "returning farmer" memory feature (PRD §4/§8) —
the profile is schema-only for now. Plans are persisted separately by farm id;
the loop also injects the request's authoritative farm id for fresh sessions.
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
        """CREATE TABLE IF NOT EXISTS plans (
            farm_id TEXT PRIMARY KEY,
            plan_json TEXT NOT NULL,
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
    conn.execute(
        """CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            alert_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    # --- channels (LOG.md) ---------------------------------------------------
    # contacts: the ONE place a phone number is stored, because an SMS reply
    # or alert needs it. Everything else keys on farm_id (a salted hash).
    conn.execute(
        """CREATE TABLE IF NOT EXISTS contacts (
            farm_id TEXT PRIMARY KEY,
            msisdn TEXT NOT NULL,
            masked TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'bn',
            first_channel TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )"""
    )
    # channel_turns: one row per agent turn taken over a phone channel, with
    # the already-redacted event trace, so the web monitor can replay it.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS channel_turns (
            turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            farm_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            masked TEXT NOT NULL,
            user_text TEXT NOT NULL,
            reply_text TEXT NOT NULL,
            events_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sms_log (
            sms_id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            body TEXT NOT NULL,
            segments INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_ref TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS alert_sms (
            alert_id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ussd_sessions (
            ussd_session_id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    # Crop-problem reports from the keypad menu: follow-up context for the
    # agent, and (aggregated by district/week, no numbers) a pest-surveillance signal.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS triage_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id TEXT NOT NULL,
            district TEXT,
            crop TEXT NOT NULL,
            stage TEXT NOT NULL,
            organ TEXT NOT NULL,
            symptom TEXT NOT NULL,
            extent TEXT NOT NULL,
            coverage TEXT NOT NULL,
            top_candidate TEXT,
            detail_json TEXT NOT NULL,
            sms TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    # Webhook deliveries already handled: SMSGate retries a webhook for ~2 days,
    # and a retried sms:received must not earn the farmer a second answer.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS webhook_seen (
            event_id TEXT PRIMARY KEY,
            seen_at TEXT NOT NULL
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


def save_plan(farm_id: str, plan: dict) -> None:
    """Persist the deterministic plan exactly as emitted to the client."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO plans (farm_id, plan_json, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(farm_id) DO UPDATE SET plan_json=excluded.plan_json, updated_at=excluded.updated_at",
            (farm_id, json.dumps(plan, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_plan(farm_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT plan_json FROM plans WHERE farm_id=?", (farm_id,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def save_alert(alert: dict) -> None:
    """Persist one deterministic weather-plan conflict by its stable id."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO alerts (alert_id, farm_id, alert_json, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(alert_id) DO UPDATE SET alert_json=excluded.alert_json, updated_at=excluded.updated_at",
            (alert["alert_id"], alert["farm_id"], json.dumps(alert, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_alerts(farm_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT alert_json FROM alerts WHERE farm_id=? ORDER BY updated_at DESC", (farm_id,)
        ).fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


# --- channels (LOG.md) -------------------------------------------------------


def upsert_contact(farm_id: str, msisdn: str, masked: str, channel: str) -> None:
    """Record (or refresh) the number a farm is reached on. First channel wins."""
    conn = _connect()
    try:
        now = _now()
        conn.execute(
            "INSERT INTO contacts (farm_id, msisdn, masked, first_channel, created_at, last_seen_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(farm_id) DO UPDATE SET "
            "msisdn=excluded.msisdn, masked=excluded.masked, last_seen_at=excluded.last_seen_at",
            (farm_id, msisdn, masked, channel, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_contact(farm_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT farm_id, msisdn, masked, language, first_channel, created_at, last_seen_at "
            "FROM contacts WHERE farm_id=?",
            (farm_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    keys = ("farm_id", "msisdn", "masked", "language", "first_channel", "created_at", "last_seen_at")
    return dict(zip(keys, row))


def list_contacts() -> list[dict]:
    """Every farm reachable by SMS (for the proactive alert job)."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT farm_id, msisdn, masked, language FROM contacts").fetchall()
    finally:
        conn.close()
    return [dict(zip(("farm_id", "msisdn", "masked", "language"), r)) for r in rows]


def save_channel_turn(
    session_id: str, farm_id: str, channel: str, masked: str,
    user_text: str, reply_text: str, events: list[dict],
) -> int:
    """Persist one phone-channel agent turn. `events` must already be redacted
    (they come from sse.tool_call/tool_result, which redact by construction)."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO channel_turns (session_id, farm_id, channel, masked, user_text, "
            "reply_text, events_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (session_id, farm_id, channel, masked, user_text, reply_text,
             json.dumps(events, ensure_ascii=False), _now()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_channel_sessions(limit: int = 30) -> list[dict]:
    """Most recent phone conversations, newest first (masked numbers only)."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT session_id, channel, masked, COUNT(*), MAX(created_at) FROM channel_turns "
            "GROUP BY session_id ORDER BY MAX(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    keys = ("session_id", "channel", "masked", "turns", "last_at")
    return [dict(zip(keys, r)) for r in rows]


def get_channel_turns(session_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT turn_id, channel, masked, user_text, reply_text, events_json, created_at "
            "FROM channel_turns WHERE session_id=? ORDER BY turn_id",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"turn_id": r[0], "channel": r[1], "masked": r[2], "user_text": r[3],
         "reply_text": r[4], "events": json.loads(r[5]), "created_at": r[6]}
        for r in rows
    ]


def log_sms(
    farm_id: str, direction: str, body: str, segments: int, provider: str,
    status: str, provider_ref: str | None = None,
) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO sms_log (farm_id, direction, body, segments, provider, provider_ref, "
            "status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (farm_id, direction, body, segments, provider, provider_ref, status, _now()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


# Delivery events arrive once per SMS part and out of order, so a status only
# moves forward: a late "sent" must not overwrite "delivered".
_SMS_STATUS_RANK = {"queued": 0, "sent": 1, "failed": 2, "cancelled": 2, "delivered": 3}


def update_sms_status(provider_ref: str, status: str) -> bool:
    conn = _connect()
    try:
        row = conn.execute("SELECT status FROM sms_log WHERE provider_ref=?", (provider_ref,)).fetchone()
        if not row or _SMS_STATUS_RANK.get(status, 0) <= _SMS_STATUS_RANK.get(row[0], 0):
            return False
        cur = conn.execute("UPDATE sms_log SET status=? WHERE provider_ref=?", (status, provider_ref))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_webhook_seen(event_id: str) -> bool:
    """Record a webhook delivery id. False if it was already handled."""
    conn = _connect()
    try:
        cur = conn.execute("INSERT OR IGNORE INTO webhook_seen (event_id, seen_at) VALUES (?,?)",
                           (event_id, _now()))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def recent_outbound_bodies(since_iso: str) -> list[str]:
    """Every SMS body we sent (to anyone) since a time — the SMS loop guard."""
    conn = _connect()
    try:
        return [r[0] for r in conn.execute(
            "SELECT body FROM sms_log WHERE direction='out' AND created_at >= ?", (since_iso,))]
    finally:
        conn.close()


def count_inbound(farm_id: str, since_iso: str) -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM sms_log WHERE farm_id=? AND direction='in' AND created_at >= ?",
                            (farm_id, since_iso)).fetchone()[0]
    finally:
        conn.close()


def list_sms(farm_id: str, limit: int = 50) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT sms_id, direction, body, segments, provider, status, created_at FROM sms_log "
            "WHERE farm_id=? ORDER BY sms_id DESC LIMIT ?",
            (farm_id, limit),
        ).fetchall()
    finally:
        conn.close()
    keys = ("sms_id", "direction", "body", "segments", "provider", "status", "created_at")
    return [dict(zip(keys, r)) for r in rows]


def get_ussd_state(ussd_session_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT state_json FROM ussd_sessions WHERE ussd_session_id=?", (ussd_session_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def save_ussd_state(ussd_session_id: str, farm_id: str, state: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO ussd_sessions (ussd_session_id, farm_id, state_json, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(ussd_session_id) DO UPDATE SET state_json=excluded.state_json, "
            "updated_at=excluded.updated_at",
            (ussd_session_id, farm_id, json.dumps(state, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_ussd_state_at(ussd_session_id: str) -> tuple[dict, str] | None:
    """A walk's state with its last-touched time (SMS menu mode expires idle walks)."""
    conn = _connect()
    try:
        row = conn.execute("SELECT state_json, updated_at FROM ussd_sessions WHERE ussd_session_id=?",
                           (ussd_session_id,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else None
    finally:
        conn.close()


def latest_ussd_state(farm_id: str, exclude: str | None = None) -> tuple[dict, str] | None:
    """The farm's most recently touched USSD walk (state, updated_at), other than `exclude`."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT state_json, updated_at FROM ussd_sessions WHERE farm_id=? AND ussd_session_id<>? "
            "ORDER BY updated_at DESC LIMIT 1",
            (farm_id, exclude or ""),
        ).fetchone()
        return (json.loads(row[0]), row[1]) if row else None
    finally:
        conn.close()


def close_other_ussd_states(farm_id: str, keep: str) -> None:
    """Mark every other walk of this farm finished, so none is offered for resume again."""
    conn = _connect()
    try:
        conn.execute("UPDATE ussd_sessions SET state_json=? WHERE farm_id=? AND ussd_session_id<>?",
                     (json.dumps({"at": "done"}), farm_id, keep))
        conn.commit()
    finally:
        conn.close()


def save_triage_report(farm_id: str, district: str | None, detail: dict, sms: str) -> int:
    cands = detail.get("candidates") or []
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO triage_reports (farm_id, district, crop, stage, organ, symptom, extent, coverage, "
            "top_candidate, detail_json, sms, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (farm_id, district, detail["crop"], detail["stage"], detail["organ"], detail["symptom"],
             detail["extent"], detail["coverage"], cands[0]["key"] if cands else None,
             json.dumps(detail, ensure_ascii=False), sms, _now()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def latest_triage_report(farm_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT detail_json, sms, created_at FROM triage_reports WHERE farm_id=? "
            "ORDER BY report_id DESC LIMIT 1", (farm_id,)).fetchone()
        return {"detail": json.loads(row[0]), "sms": row[1], "created_at": row[2]} if row else None
    finally:
        conn.close()


def triage_summary(since_iso: str) -> list[dict]:
    """Report counts per district × crop × top candidate since a time — no farm ids."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT district, crop, COALESCE(top_candidate, 'no_kb'), COUNT(*), MAX(created_at) "
            "FROM triage_reports WHERE created_at >= ? GROUP BY 1, 2, 3 ORDER BY 4 DESC",
            (since_iso,)).fetchall()
        return [{"district": r[0], "crop": r[1], "candidate": r[2], "reports": r[3], "latest": r[4]}
                for r in rows]
    finally:
        conn.close()


def mark_alert_sms_sent(alert_id: str, farm_id: str) -> bool:
    """Record that an alert was texted. False if it already had been."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO alert_sms (alert_id, farm_id, sent_at) VALUES (?,?,?)",
            (alert_id, farm_id, _now()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def alert_sms_sent(alert_id: str) -> bool:
    conn = _connect()
    try:
        return conn.execute("SELECT 1 FROM alert_sms WHERE alert_id=?", (alert_id,)).fetchone() is not None
    finally:
        conn.close()
