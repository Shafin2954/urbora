"""Marketplace tables, in the same SQLite file as the rest of memory.

Sharing `backend.memory.store._connect` (not a second DB) keeps one file to
back up, and lets tests redirect everything with one monkeypatch.

Every dealer, product, buyer and listing row carries `is_demo` (CLAUDE.md rule
16): seeded demo rows are labelled demo wherever they render.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone

from backend.memory import store

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS dealers (
        dealer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        district TEXT NOT NULL,
        upazila TEXT,
        msisdn TEXT NOT NULL,
        lat REAL, lon REAL,
        verified INTEGER NOT NULL DEFAULT 0,
        completed_orders INTEGER NOT NULL DEFAULT 0,
        token TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        dealer_id TEXT NOT NULL,
        generic TEXT NOT NULL,
        brand_name TEXT NOT NULL,
        pack_size REAL NOT NULL,
        pack_unit TEXT NOT NULL,
        price_bdt REAL NOT NULL,
        stock_packs INTEGER NOT NULL,
        price_source TEXT,
        updated_at TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id TEXT NOT NULL,
        dealer_id TEXT NOT NULL,
        totals_json TEXT NOT NULL,
        payment TEXT NOT NULL,
        status TEXT NOT NULL,
        channel TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS buyers (
        buyer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        district TEXT NOT NULL,
        msisdn TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0,
        completed_deals INTEGER NOT NULL DEFAULT 0,
        token TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS produce_listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id TEXT NOT NULL,
        crop TEXT NOT NULL,
        qty_kg REAL NOT NULL,
        asking_price_per_kg REAL,
        district TEXT NOT NULL,
        available_from TEXT NOT NULL,
        status TEXT NOT NULL,
        channel TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS offers (
        offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        buyer_id TEXT NOT NULL,
        price_per_kg REAL NOT NULL,
        qty_kg REAL NOT NULL,
        pickup_date TEXT,
        status TEXT NOT NULL,
        totals_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_token() -> str:
    return secrets.token_urlsafe(16)


def connect() -> sqlite3.Connection:
    conn = store._connect()
    for ddl in _SCHEMA:
        conn.execute(ddl)
    conn.row_factory = sqlite3.Row
    return conn


def rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def row(sql: str, params: tuple = ()) -> dict | None:
    found = rows(sql, params)
    return found[0] if found else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write; returns lastrowid (or rowcount for updates)."""
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid or cur.rowcount)
    finally:
        conn.close()


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)
