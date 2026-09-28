"""USSD menu state machine and its runtime/route."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.channels import ussd
from backend.channels.ussd import (SCREEN_UCS2, DIVISIONS, SOILS, UssdContext, agent_message, fits,
                                   paginate, step)
from backend.memory import store
from backend.tools.ask import DISTRICT_BN
from backend.tools.districts import DISTRICTS

PHONE = "01812345678"


def ctx(**kw):
    base = dict(brand="Brand", farm_id="ph-x", today=date(2026, 11, 1))
    base.update(kw)
    return UssdContext(**base)


def walk(inputs, c=None, state=None):
    c = c or ctx()
    screen, state, action = step(state, None, c)
    for text in inputs:
        screen, state, action = step(state, text, c)
    return screen, state, action


def keys_for(title, labels, index):
    """The keys a farmer presses on a paged menu to pick option `index`."""
    for p, page in enumerate(paginate(title, labels)):
        if index in page:
            return ["9"] * p + [str(page.index(index) + 1)]
    raise ValueError(index)


def to_district(division="Rajshahi", district="Rajshahi"):
    div = [d for d, _ in DIVISIONS].index(division)
    names = sorted(d for d, v in DISTRICTS.items() if v[0] == division)
    labels = [DISTRICT_BN.get(n, n) for n in names]
    return (keys_for("বিভাগ:", [lab for _, lab in DIVISIONS], div)
            + keys_for("জেলা:", labels, names.index(district)))


LOAM = keys_for("মাটি?", [lab for _, lab in SOILS], 0)
INTAKE = ["1"] + to_district() + ["2"] + LOAM + ["1", "1", "30000"]


def test_dial_shows_the_main_menu_first_page():
    screen, state, action = step(None, None, ctx())
    assert screen.text.splitlines()[:3] == ["Brand", "1. ফসল পরামর্শ", "2. ফসলের সমস্যা"]
    assert screen.text.endswith("9. আরও") and not screen.end and action is None


def test_main_menu_second_page_and_direct_keys():
    screen, state, _ = walk(["9"])
    assert screen.text.startswith("5. ") and screen.text.endswith("0. পিছনে")
    screen, state, _ = step(state, "0", ctx())
    assert screen.text.startswith("Brand")
    # A key from page 2 works from page 1 too (a farmer who knows the number).
    screen, state, _ = walk(["8"])
    assert state["at"] == "ask"


def test_full_intake_ends_with_a_plan_action_and_never_waits():
    screen, state, action = walk(INTAKE + ["1"])
    assert screen.end and "SMS" in screen.text
    assert action["kind"] == "plan"
    assert action["profile"] == {"district": "Rajshahi", "area": 2.0, "area_unit": "bigha",
                                 "soil_type": "loam", "water_source": "tubewell",
                                 "season": "rabi", "budget_bdt": 30000}


def test_agent_message_is_understood_by_the_loop_extractor():
    from backend.agent.loop import extract_known_fields
    profile = {"district": "Rajshahi", "area": 2.0, "soil_type": "clay_loam",
               "water_source": "rainfed", "season": "kharif2", "budget_bdt": 30000}
    found = extract_known_fields(agent_message(profile))
    assert found["soil_type"] == "clay_loam" and found["water_source"] == "rainfed"
    assert found["season"] == "kharif2" and found["budget_bdt"] == 30000
    assert found["area"] == 2.0 and found["area_unit"] == "bigha"


def test_bangla_keypad_digits_work():
    first = to_district()[0]
    screen, state, _ = walk(["১", first.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))])
    assert state["at"] in ("district", "division")


def test_bad_choice_repeats_the_screen_with_a_short_note():
    screen, state, _ = walk(["1", "x"])
    assert state["at"] == "division" and screen.text.startswith("ভুল!")
    assert fits(screen.text)


def test_invalid_area_is_refused():
    screen, state, _ = walk(["1"] + to_district() + ["abc"])
    assert state["at"] == "area" and screen.text.startswith("ভুল সংখ্যা!")


def test_long_district_lists_page_with_9_and_back_with_0():
    div = keys_for("বিভাগ:", [lab for _, lab in DIVISIONS], 0)  # Dhaka: 13 districts
    screen, state, _ = walk(["1"] + div)
    assert "9. আরও" in screen.text
    screen, state, _ = step(state, "9", ctx())
    assert state["dpage"] == 1
    screen, state, _ = step(state, "0", ctx())
    assert state["dpage"] == 0


def test_zero_goes_back_a_step():
    _, state, _ = walk(["1"] + to_district() + ["2"])
    assert state["at"] == "soil"
    _, state, _ = step(state, "0", ctx())
    assert state["at"] == "area"


def test_known_farmer_confirms_their_saved_details():
    profile = {"district": "Rajshahi", "area": 2, "soil_type": "loam", "water_source": "tubewell",
               "season": "rabi", "budget_bdt": 30000}
    c = ctx(profile=profile)
    screen, state, _ = walk(["1"], c)
    assert state["at"] == "reuse"
    screen, state, _ = walk(["1", "1"], c)
    assert "রাজশাহী 2বিঘা দোআঁশ নলকূপ রবি ৳30000" in screen.text
    screen, state, action = walk(["1", "1", "1"], c)
    assert action["kind"] == "plan" and action["profile"]["district"] == "Rajshahi"


def test_cancel_sends_nothing():
    screen, _, action = walk(INTAKE + ["2"])
    assert screen.end and action is None


def test_ask_a_question_goes_async():
    screen, _, action = walk(["8", "ধানে পোকা লেগেছে কী করব?"])
    assert screen.end and action == {"kind": "ask", "message": "ধানে পোকা লেগেছে কী করব?"}


def _prov():
    return {"value": None, "source_type": "kb", "source_id": "x", "source_title": "x",
            "locator": "x", "retrieved_at": "t", "confidence": "medium"}


def test_plan_screen_shows_upcoming_tasks_only():
    plan = {"farm_id": "f", "crop": "potato", "tasks": [
        {"date": "2026-10-01", "task": "পুরনো", "category": "sowing", "provenance": _prov()},
        {"date": "2026-11-15", "task": "আলু রোপণ", "category": "sowing", "provenance": _prov()},
    ]}
    screen, _, _ = walk(["3"], ctx(plan=plan))
    assert screen.end and "আলু" in screen.text and "15/11 আলু রোপণ" in screen.text and "পুরনো" not in screen.text


def test_plan_screen_without_a_plan():
    screen, _, _ = walk(["3"])
    assert screen.end and "প্ল্যান নেই" in screen.text


def test_alerts_screen_is_short_and_the_full_alert_goes_by_sms():
    alerts = [{"alert_id": "a", "task_date": "2026-11-20", "task": "সেচ", "status": "open",
               "provenance": {"value": 31.0}}]
    screen, _, action = walk(["4"], ctx(alerts=alerts))
    assert "20/11" in screen.text and "31 মিমি" in screen.text and fits(screen.text)
    assert action["kind"] == "sms" and "31 মিমি" in action["text"] and "Open-Meteo" in action["text"]


def test_last_answer_is_paged():
    text = "ক " * 150
    screen, state, _ = walk(["7"], ctx(last_answer=text))
    assert "9. আরও" in screen.text and fits(screen.text)
    screen, state, _ = step(state, "9", ctx(last_answer=text))
    assert state["lpage"] == 1


# --- screen budget ---------------------------------------------------------------------------


def _full_ctx():
    from backend.channels.triage_menu import SUBMENUS as TRIAGE
    from backend.market.ussd_menus import SUBMENUS
    profile = {"district": "Chattogram", "area": 2.5, "soil_type": "clay_loam", "water_source": "rainfed",
               "season": "kharif1", "budget_bdt": 100000}
    plan = {"crop": "boro_rice", "tasks": [
        {"date": "2026-10-10", "task": "বোরো চারা রোপণ", "category": "sowing"},
        {"date": "2026-11-05", "task": "ইউরিয়া সারের দ্বিতীয় কিস্তি উপরি প্রয়োগ করুন", "category": "fertilizer"},
        {"date": "2026-11-20", "task": "জমিতে 5-7 সেমি পানি রাখুন", "category": "irrigation"}]}
    alerts = [{"alert_id": "a", "task_date": "2026-11-20", "task": "ইউরিয়া সারের দ্বিতীয় কিস্তি", "status": "open",
               "provenance": {"value": 131.5}}]
    return ctx(brand="Agrosfeer", profile=profile, plan=plan, alerts=alerts, last_answer="ধান " * 120,
               submenus={**SUBMENUS, **TRIAGE})


def test_every_reachable_screen_fits_one_bangla_ussd_screen(monkeypatch):
    """Breadth-first over every key on every screen (plus numbers where asked):
    no screen — error variants included — exceeds 80 UCS-2 units (160 octets)."""
    import backend.market.inputs as mi
    import backend.market.produce as mp
    offer = {"product_id": "p", "dealer_name": "মেসার্স রহিম অ্যান্ড সন্স ট্রেডার্স", "pack_size": 50,
             "pack_unit": "কেজি", "price_bdt": 13500, "km": 42.5, "is_demo": True, "brand_name": "b"}
    monkeypatch.setattr(mi, "find_inputs", lambda g, d, **k: {"offers": [offer] * 3})
    monkeypatch.setattr(mp, "price_guide", lambda c: {"farm_gate": {"price_bdt_per_kg": 17.25, "date": "d"},
                                                      "wholesale_pattern": {"this_month_avg_bdt_per_kg": 21.75}})
    for profile_known in (True, False):
        c = _full_ctx()
        if not profile_known:
            c.profile = None
        screen, state, _ = step(None, None, c)
        seen, frontier = {screen.text}, [state]
        for _depth in range(10):
            nxt = []
            for st in frontier:
                for key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "x", "250", "100000", "*"]:
                    s, st2, _ = step(json.loads(json.dumps(st)), key, c)
                    assert fits(s.text), (len(s.text), s.text)
                    if s.text not in seen:
                        seen.add(s.text)
                        if not s.end:
                            nxt.append(st2)
            frontier = nxt[:600]
        assert len(seen) > 60  # the walk really covered the menus


def test_pager_never_exceeds_the_limit_even_for_long_labels():
    labels = ["খুব লম্বা একটি বিকল্পের নাম যা স্ক্রিনে ধরে না"] * 5
    for i, page in enumerate(paginate("শিরোনাম:", labels)):
        assert page and fits(ussd.paged("শিরোনাম:", labels, i).text)


def test_error_note_never_makes_a_screen_longer():
    text = ussd.paged("মাটি?", [lab for _, lab in SOILS], 0).text
    assert len(ussd.with_note(text, ussd.BAD)) <= len(text) <= SCREEN_UCS2


# --- resume after a dropped session ------------------------------------------------------


def test_unfinished_intake_is_offered_back_and_continues_where_it_stopped():
    _, dropped, _ = walk(["1"] + to_district() + ["2"])          # at soil when the call dropped
    c = ctx(resume=dropped)
    screen, state, _ = step(None, None, c)
    assert state["at"] == "resume" and "1. চালিয়ে যান" in screen.text
    screen, state, _ = step(state, "1", c)
    assert state["at"] == "soil" and state["profile"]["district"] == "Rajshahi"


def test_resume_can_be_declined():
    _, dropped, _ = walk(["1"] + to_district())
    screen, state, _ = walk(["2"], ctx(resume=dropped))
    assert state == {"at": "main"}


def test_finished_or_menu_states_are_not_offered():
    assert not ussd.resumable({"at": "main"})
    assert not ussd.resumable({"at": "done"})
    assert not ussd.resumable({"at": "inputs", "sub": "inputs", "step": "offer"})
    assert ussd.resumable({"at": "problem", "sub": "problem", "step": "organ"})


# --- runtime + route ---------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "ussd.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    monkeypatch.delenv("CHANNEL_EMULATOR_ENABLED", raising=False)
    monkeypatch.delenv("SMS_PROVIDER", raising=False)
    from backend.channels import sms
    sms.set_provider(None)
    actions = []

    async def fake_run_action(local, farm_id, action):
        actions.append(action)

    monkeypatch.setattr(ussd, "run_action", fake_run_action)
    from backend.api.main import app
    c = TestClient(app)
    c.actions = actions
    return c


def _send(client, session, text=None, init=False):
    r = client.post("/api/channels/emulator/ussd",
                    json={"session_id": session, "msisdn": PHONE, "text": text, "init": init})
    assert r.status_code == 200
    return r.json()


def test_emulator_ussd_round_trip_keeps_state_per_session(client):
    assert _send(client, "s1", init=True)["text"].splitlines()[1] == "1. ফসল পরামর্শ"
    for t in INTAKE:
        body = _send(client, "s1", t)
    body = _send(client, "s1", "1")
    assert body["end"] and body["mode"] == "simulator"
    assert client.actions and client.actions[0]["kind"] == "plan"


def test_redial_after_a_drop_offers_the_unfinished_walk_once(client):
    _send(client, "s1", init=True)
    for t in ["1"] + to_district() + ["2"]:
        _send(client, "s1", t)                                   # dropped at the soil screen
    body = _send(client, "s2", init=True)
    assert "চালিয়ে যান" in body["text"]
    body = _send(client, "s2", "1")
    assert body["text"].splitlines()[0] == "মাটি?"
    # finish on s2; a third dial starts fresh
    for t in LOAM + ["1", "1", "30000", "1"]:
        body = _send(client, "s2", t)
    assert body["end"]
    assert _send(client, "s3", init=True)["text"].splitlines()[1] == "1. ফসল পরামর্শ"


def test_a_stale_unfinished_walk_is_not_offered(client):
    import sqlite3
    _send(client, "s1", init=True)
    _send(client, "s1", "1")                                     # left at the division screen
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
    conn = sqlite3.connect(store._DB_PATH)
    conn.execute("UPDATE ussd_sessions SET updated_at=?", (old,))
    conn.commit()
    conn.close()
    assert "চালিয়ে যান" not in _send(client, "s2", init=True)["text"]


def test_bdapps_ussd_reply_shape_in_simulator_mode(client, monkeypatch):
    monkeypatch.setenv("BDAPPS_MODE", "simulator")
    r = client.post("/api/channels/ussd/bdapps", json={
        "message": "*123#", "ussdOperation": "mo-init", "requestId": "1", "sessionId": "99",
        "sourceAddress": "tel:8801812345678", "encoding": "440", "version": "1.0"})
    reply = r.json()["reply"]
    assert reply["mode"] == "simulator"
    sent = reply["would_send"]
    assert sent["ussdOperation"] == "mt-cont" and sent["encoding"] == "16"
    assert sent["password"] == "***" and sent["destinationAddress"] == "tel:8801812345678"
