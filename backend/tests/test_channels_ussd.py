"""USSD menu state machine and its runtime/route."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.channels import ussd
from backend.channels.ussd import Screen, UssdContext, agent_message, step
from backend.memory import store
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


def _rajshahi_digit():
    names = sorted(d for d, v in DISTRICTS.items() if v[0] == "Rajshahi")
    return str(names.index("Rajshahi") + 1)


def test_dial_shows_the_main_menu():
    screen, state, action = step(None, None, ctx())
    assert screen.text.startswith("Brand\n1. নতুন পরামর্শ") and not screen.end and action is None


def test_full_intake_ends_with_a_plan_action_and_never_waits():
    screen, state, action = walk(["1", "3", _rajshahi_digit(), "2", "1", "1", "1", "30000", "1"])
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
    screen, state, _ = walk(["১", "৩"])
    assert state["at"] == "district" and state["division"] == "Rajshahi"


def test_bad_choice_repeats_the_screen_with_a_note():
    screen, state, _ = walk(["1", "9"])
    assert state["at"] == "division" and screen.text.startswith("ভুল বাছাই।")


def test_invalid_area_is_refused():
    screen, state, _ = walk(["1", "3", _rajshahi_digit(), "abc"])
    assert state["at"] == "area" and screen.text.startswith("সঠিক সংখ্যা দিন।")


def test_dhaka_districts_page_and_page_back():
    screen, state, _ = walk(["1", "1"])
    assert "8. আরও" in screen.text
    screen, state, _ = step(state, "8", ctx())
    assert state["dpage"] == 1 and "8. আরও" not in screen.text
    screen, state, _ = step(state, "0", ctx())
    assert state["dpage"] == 0


def test_zero_goes_back_a_step():
    _, state, _ = walk(["1", "3", _rajshahi_digit(), "2"])
    assert state["at"] == "soil"
    _, state, _ = step(state, "0", ctx())
    assert state["at"] == "area"


def test_known_farmer_is_offered_their_saved_details():
    profile = {"district": "Rajshahi", "area": 2, "soil_type": "loam", "water_source": "tubewell",
               "season": "rabi", "budget_bdt": 30000}
    c = ctx(profile=profile)
    screen, state, _ = walk(["1"], c)
    assert "রাজশাহী, 2 বিঘা, দোআঁশ, নলকূপ, রবি, ৳30,000" in screen.text
    screen, state, action = walk(["1", "1", "1"], c)
    assert action["kind"] == "plan" and action["profile"]["district"] == "Rajshahi"


def test_cancel_sends_nothing():
    screen, _, action = walk(["1", "3", _rajshahi_digit(), "2", "1", "1", "1", "30000", "2"])
    assert screen.end and action is None


def test_ask_a_question_goes_async():
    screen, _, action = walk(["6", "ধানে পোকা লেগেছে কী করব?"])
    assert screen.end and action == {"kind": "ask", "message": "ধানে পোকা লেগেছে কী করব?"}


def _prov():
    return {"value": None, "source_type": "kb", "source_id": "x", "source_title": "x",
            "locator": "x", "retrieved_at": "t", "confidence": "medium"}


def test_plan_screen_shows_upcoming_tasks_only():
    plan = {"farm_id": "f", "crop": "potato", "tasks": [
        {"date": "2026-10-01", "task": "পুরনো", "category": "sowing", "provenance": _prov()},
        {"date": "2026-11-15", "task": "আলু রোপণ", "category": "sowing", "provenance": _prov()},
    ]}
    screen, _, _ = walk(["2"], ctx(plan=plan))
    assert screen.end and "আলু" in screen.text and "15/11 আলু রোপণ" in screen.text and "পুরনো" not in screen.text


def test_plan_screen_without_a_plan():
    screen, _, _ = walk(["2"])
    assert screen.end and "প্ল্যান নেই" in screen.text


def test_alerts_screen_quotes_the_forecast():
    alerts = [{"alert_id": "a", "task_date": "2026-11-20", "task": "সেচ", "status": "open",
               "provenance": {"value": 31.0}}]
    screen, _, _ = walk(["3"], ctx(alerts=alerts))
    assert "20/11" in screen.text and "31 মিমি" in screen.text


def test_last_answer_is_paged():
    text = "ক" * 300
    screen, state, _ = walk(["7"], ctx(last_answer=text))
    assert "9. আরও" in screen.text
    screen, state, _ = step(state, "9", ctx(last_answer=text))
    assert state["lpage"] == 1


def test_every_screen_fits_a_phone():
    """Menus stay short: no screen in the intake walk exceeds 182 characters."""
    c = ctx()
    screen, state, _ = step(None, None, c)
    for text in ["1", "1", "8", "1", "2", "1", "1", "1", "30000"]:
        assert len(screen.text) <= 182, screen.text
        screen, state, _ = step(state, text, c)


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


def test_emulator_ussd_round_trip_keeps_state_per_session(client):
    def send(text=None, init=False):
        r = client.post("/api/channels/emulator/ussd",
                        json={"session_id": "s1", "msisdn": PHONE, "text": text, "init": init})
        assert r.status_code == 200
        return r.json()

    assert send(init=True)["text"].splitlines()[1] == "1. নতুন পরামর্শ"
    for t in ["1", "3", _rajshahi_digit(), "2", "1", "1", "1", "30000"]:
        body = send(t)
    body = send("1")
    assert body["end"] and body["mode"] == "simulator"
    assert client.actions and client.actions[0]["kind"] == "plan"


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
