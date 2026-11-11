"""SMS menu mode: the USSD menu walked over plain SMS."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.channels import flows, sms, sms_menu, ussd
from backend.channels.identity import farm_id_for
from backend.memory import store

PHONE = "01812345678"


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "m.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    sms.set_provider(None)
    agent_calls = []

    async def fake_turn(msisdn, text, channel, **kw):
        agent_calls.append(text)
        from backend.channels.adapter import ChannelReply
        return ChannelReply(session_id="s", farm_id=farm_id_for(msisdn), masked="***678", text="উত্তর")

    monkeypatch.setattr(flows, "run_channel_turn", fake_turn)
    yield agent_calls
    sms.set_provider(None)


def text_in(t):
    asyncio.run(flows.handle_inbound_sms(PHONE, t, "emulator"))
    return [m["body"] for m in store.list_sms(farm_id_for(PHONE)) if m["direction"] == "out"][0]


def test_menu_keyword_sends_the_main_menu_with_a_hint():
    body = text_in("মেনু")
    assert "1. ফসল পরামর্শ" in body and body.endswith(sms_menu.FIRST_HINT)
    assert text_in("9").startswith("5. ")


def test_a_whole_crop_problem_walk_by_sms_ends_with_the_answer(_db):
    text_in("menu")
    for k in ["2", "5", "3", "4", "2"]:          # problem → lentil → flowering → pod → holes
        text_in(k)
    last = text_in("2")                            # half the field
    assert "ফল ছিদ্রকারী পোকা" in last and "16123" in last
    outs = [m["body"] for m in store.list_sms(farm_id_for(PHONE)) if m["direction"] == "out"]
    assert not any("কয়েক মিনিটে" in b for b in outs)  # no "coming soon" before an instant answer
    assert _db == []                               # no agent call for any of it
    assert not sms_menu.is_open(farm_id_for(PHONE))


def test_free_text_leaves_the_menu_and_reaches_the_agent(_db):
    text_in("মেনু")
    assert text_in("ধানের পাতা হলুদ কেন?") == "উত্তর"
    assert _db == ["ধানের পাতা হলুদ কেন?"] and not sms_menu.is_open(farm_id_for(PHONE))


def test_digits_without_an_open_menu_go_to_the_agent(_db):
    text_in("2")
    assert _db == ["2"]


def test_an_idle_menu_expires(_db):
    text_in("মেনু")
    old = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(timespec="seconds")
    conn = sqlite3.connect(store._DB_PATH)
    conn.execute("UPDATE ussd_sessions SET updated_at=?", (old,))
    conn.commit()
    conn.close()
    text_in("1")
    assert _db == ["1"]


def test_a_dropped_ussd_walk_can_be_finished_by_sms():
    fid = farm_id_for(PHONE)
    store.save_ussd_state("ussd-dropped", fid, {"at": "problem", "sub": "problem", "step": "organ",
                                                "crop": "lentil", "stage": "flowering", "pg": 0})
    assert "চালিয়ে যান" in text_in("মেনু")
    assert text_in("1").startswith("কোথায় সমস্যা?")


def test_question_screen_takes_free_text_as_the_question(monkeypatch):
    seen = []

    async def fake_action(local, farm_id, action):
        seen.append(action)

    monkeypatch.setattr(ussd, "run_action", fake_action)
    text_in("মেনু")
    text_in("8")
    text_in("আমার আলুর পাতা কুঁকড়ে যাচ্ছে")
    assert seen == [{"kind": "ask", "message": "আমার আলুর পাতা কুঁকড়ে যাচ্ছে"}]


# --- the SMS loop guard (LOG.md 2026-09-29: the bot answered itself three times) --------


def test_our_own_sms_coming_back_is_not_answered(_db):
    body = text_in("মেনু")                          # we sent the menu...
    asyncio.run(flows.handle_inbound_sms(PHONE, body, "smsgate"))   # ...and it came back in
    assert _db == []
    assert store.list_sms(farm_id_for(PHONE))[0]["status"] == "ignored: echo of our own SMS"


def test_messages_from_the_service_numbers_are_not_answered(_db, monkeypatch):
    monkeypatch.setenv("CHANNEL_OWN_NUMBERS", "01999999884, 01812345678")
    asyncio.run(flows.handle_inbound_sms(PHONE, "ধানে পোকা", "smsgate"))
    assert _db == []


def test_a_phone_texting_faster_than_a_person_is_throttled(_db):
    for i in range(flows.RATE_LIMIT + 3):
        asyncio.run(flows.handle_inbound_sms(PHONE, f"প্রশ্ন নম্বর {i} আলুর দাম কত", "smsgate"))
    assert len(_db) == flows.RATE_LIMIT


def test_internal_tool_notes_never_reach_a_farmer():
    from backend.channels.adapter import scrub_internal
    from backend.tools.ask import ASK_NOTE
    assert scrub_internal(f"আপনার জেলা কোনটি? {ASK_NOTE}") == "আপনার জেলা কোনটি?"
    assert scrub_internal(ASK_NOTE) == ""
    assert scrub_internal("রাজশাহীতে আলু ভালো হয়। সেচ দিন।") == "রাজশাহীতে আলু ভালো হয়। সেচ দিন।"
