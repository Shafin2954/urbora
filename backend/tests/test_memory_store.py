"""Tests for backend/memory/store.py — session + farm SQLite persistence.

Uses a temp DB path per test (monkeypatched) so tests never touch the real
backend/memory/memory.db and never leak state between runs.
"""

from __future__ import annotations

import backend.memory.store as store


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "test_memory.db")


def test_new_session_returns_empty_history(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    assert store.get_session_messages("sess-new") == []


def test_session_round_trip(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": "হ্যালো"}, {"role": "assistant", "content": "ok"}]
    store.save_session_messages("sess-1", messages)
    assert store.get_session_messages("sess-1") == messages


def test_session_update_overwrites_not_appends(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    store.save_session_messages("sess-2", [{"role": "user", "content": "a"}])
    store.save_session_messages("sess-2", [{"role": "user", "content": "a"},
                                            {"role": "assistant", "content": "b"}])
    assert len(store.get_session_messages("sess-2")) == 2


def test_farm_round_trip_and_missing_returns_none(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    assert store.get_farm("farm-missing") is None
    profile = {"farm_id": "farm-1", "district": "Rajshahi", "area_ha": 1.0}
    store.save_farm("farm-1", profile)
    assert store.get_farm("farm-1") == profile


def test_unicode_bangla_survives_round_trip(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": "রাজশাহীতে ১ হেক্টর জমি আছে"}]
    store.save_session_messages("sess-bn", messages)
    assert store.get_session_messages("sess-bn")[0]["content"] == messages[0]["content"]
