"""SMS providers, webhook routes, emulator gating, alert job, ADB parser."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from backend.channels import alerts_job, flows, sms, sms_text
from backend.channels.bridge.adb import parse_call_log
from backend.channels.identity import farm_id_for
from backend.memory import store

PHONE = "01812345678"


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "sms.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    for var in ("SMS_PROVIDER", "CHANNEL_EMULATOR_ENABLED", "SMSGATE_SIGNING_KEY", "BRIDGE_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    sms.set_provider(None)
    yield
    sms.set_provider(None)


def _register(phone=PHONE):
    fid = farm_id_for(phone)
    store.upsert_contact(fid, phone, "***678", "sms")
    return fid


class Recorder:
    name, mode = "rec", "simulator"

    def __init__(self):
        self.sent = []

    def send(self, local, text):
        self.sent.append((local, text))
        return sms.SendResult(self.name, "sent", provider_ref=f"r{len(self.sent)}")


# --- send_sms ------------------------------------------------------------------

def test_send_sms_trims_to_budget_and_logs(monkeypatch):
    fid = _register()
    rec = Recorder()
    monkeypatch.setenv("SMS_MAX_PARTS", "2")
    res = sms.send_sms(fid, "ধান " * 200, p=rec)
    assert res.status == "sent"
    local, body = rec.sent[0]
    assert local == PHONE and sms_text.segments(body) <= 2
    logged = store.list_sms(fid)[0]
    assert logged["direction"] == "out" and logged["segments"] <= 2


def test_send_sms_refuses_an_unknown_farm():
    assert sms.send_sms("ph-nobody", "hi", p=Recorder()).status == "failed"


def test_default_provider_is_the_simulator():
    assert sms.build_provider().name == "simulator" and sms.build_provider().mode == "simulator"


def test_smsgate_needs_credentials():
    with pytest.raises(ValueError):
        sms.SmsGateProvider("", "", "")


def test_smsgate_request_shape(monkeypatch):
    captured = {}

    class Resp:
        status_code = 202
        headers = {"content-type": "application/json"}
        text = ""

        def json(self):
            return {"id": "abc", "state": "Pending"}

    def fake_post(url, json, auth, timeout):
        captured.update(url=url, json=json, auth=auth)
        return Resp()

    monkeypatch.setattr(sms.httpx, "post", fake_post)
    res = sms.SmsGateProvider("http://10.0.0.5:8080/", "u", "p").send(PHONE, "হ্যালো")
    assert captured["url"] == "http://10.0.0.5:8080/message"
    assert captured["json"] == {"textMessage": {"text": "হ্যালো"}, "phoneNumbers": ["+8801812345678"],
                                "withDeliveryReport": True, "ttl": 3600}
    assert captured["auth"] == ("u", "p")
    assert res.status == "queued" and res.provider_ref == "abc"


def test_smsgate_signature():
    body, ts, key = b'{"event":"sms:received"}', "1727400000", "secret"
    good = hmac.new(key.encode(), body + ts.encode(), hashlib.sha256).hexdigest()
    assert sms.verify_smsgate_signature(body, ts, good, key)
    assert not sms.verify_smsgate_signature(body, ts, "0" * 64, key)
    assert not sms.verify_smsgate_signature(body, "", good, key)


# --- routes --------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    from backend.api.main import app
    calls = []

    async def fake_handle(msisdn, text, provider_name, ref=None):
        calls.append((msisdn, text, provider_name, ref))

    monkeypatch.setattr(flows, "handle_inbound_sms", fake_handle)
    c = TestClient(app)
    c.calls = calls
    return c


def _webhook(event, payload, event_id="e1"):
    return json.dumps({"event": event, "id": event_id, "deviceId": "d", "webhookId": "w",
                       "payload": payload}).encode()


def test_smsgate_webhook_answers_in_background(client):
    raw = _webhook("sms:received", {"messageId": "m1", "message": "ধান?", "sender": "+8801812345678"})
    r = client.post("/api/channels/sms/smsgate", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 200
    assert client.calls == [("+8801812345678", "ধান?", "smsgate", "m1")]


def test_smsgate_webhook_rejects_a_bad_signature(client, monkeypatch):
    monkeypatch.setenv("SMSGATE_SIGNING_KEY", "k")
    raw = _webhook("sms:received", {"message": "x", "sender": PHONE})
    r = client.post("/api/channels/sms/smsgate", content=raw,
                    headers={"X-Timestamp": "1", "X-Signature": "bad"})
    assert r.status_code == 401 and client.calls == []


def test_smsgate_retry_of_the_same_event_is_answered_once(client):
    raw = _webhook("sms:received", {"messageId": "m1", "message": "ধান?", "sender": PHONE}, "ev-7")
    client.post("/api/channels/sms/smsgate", content=raw)
    r = client.post("/api/channels/sms/smsgate", content=raw)
    assert r.json().get("duplicate") is True
    assert len(client.calls) == 1


def test_smsgate_stale_sms_is_recorded_not_answered(client):
    fid = _register()
    raw = _webhook("sms:received", {"messageId": "m2", "message": "পুরনো", "sender": PHONE,
                                    "receivedAt": "2026-01-01T08:00:00.000+06:00"}, "ev-8")
    r = client.post("/api/channels/sms/smsgate", content=raw)
    assert r.json().get("stale") is True and client.calls == []
    assert store.list_sms(fid)[0]["body"] == "পুরনো"


def test_smsgate_signed_webhook_needs_a_fresh_timestamp(client, monkeypatch):
    import time as _time
    monkeypatch.setenv("SMSGATE_SIGNING_KEY", "k")
    raw = _webhook("sms:received", {"messageId": "m3", "message": "x", "sender": PHONE}, "ev-9")

    def sign(ts):
        return {"X-Timestamp": ts, "X-Signature": hmac.new(b"k", raw + ts.encode(), hashlib.sha256).hexdigest()}

    old = client.post("/api/channels/sms/smsgate", content=raw, headers=sign(str(int(_time.time()) - 3600)))
    assert old.status_code == 401 and client.calls == []
    fresh = client.post("/api/channels/sms/smsgate", content=raw, headers=sign(str(int(_time.time()))))
    assert fresh.status_code == 200 and len(client.calls) == 1


def test_delivery_status_never_moves_backwards(client):
    fid = _register()
    store.log_sms(fid, "out", "x", 2, "smsgate", "queued", "m10")
    client.post("/api/channels/sms/smsgate", content=_webhook("sms:delivered", {"messageId": "m10"}, "d1"))
    client.post("/api/channels/sms/smsgate", content=_webhook("sms:sent", {"messageId": "m10"}, "d2"))
    assert store.list_sms(fid)[0]["status"] == "delivered"


def test_phone_up_registers_every_event_on_loopback():
    from backend.channels.bridge.phone_up import EVENTS, webhook_registrations
    regs = webhook_registrations(8000)
    assert [r["event"] for r in regs] == list(EVENTS)
    assert len({r["id"] for r in regs}) == len(regs)
    # SMSGate accepts plain HTTP only for 127.0.0.1 (reached through adb reverse).
    assert all(r["url"] == "http://127.0.0.1:8000/api/channels/sms/smsgate" for r in regs)


def test_delivery_events_update_status(client):
    fid = _register()
    store.log_sms(fid, "out", "x", 1, "smsgate", "queued", "m9")
    client.post("/api/channels/sms/smsgate", content=_webhook("sms:delivered", {"messageId": "m9"}))
    assert store.list_sms(fid)[0]["status"] == "delivered"


def test_emulator_routes_exist_only_in_simulator_mode(client, monkeypatch):
    assert client.get("/api/channels/emulator/inbox", params={"msisdn": PHONE}).status_code == 200

    class Live(Recorder):
        mode = "live"

    sms.set_provider(Live())
    assert client.get("/api/channels/emulator/inbox", params={"msisdn": PHONE}).status_code == 404
    monkeypatch.setenv("CHANNEL_EMULATOR_ENABLED", "true")
    assert client.get("/api/channels/emulator/inbox", params={"msisdn": PHONE}).status_code == 200


def test_emulator_missed_call_sends_the_welcome_sms(client):
    r = client.post("/api/channels/emulator/missed-call", json={"msisdn": PHONE})
    assert r.status_code == 200
    inbox = client.get("/api/channels/emulator/inbox", params={"msisdn": PHONE}).json()["messages"]
    assert inbox and "প্রশ্ন লিখে SMS করুন" in inbox[-1]["body"]


def test_bridge_needs_its_token(client, monkeypatch):
    assert client.post("/api/channels/bridge/missed-call", json={"msisdn": PHONE}).status_code == 401
    monkeypatch.setenv("BRIDGE_TOKEN", "t")
    r = client.post("/api/channels/bridge/missed-call", json={"msisdn": PHONE}, headers={"X-Bridge-Token": "t"})
    assert r.status_code == 200


def test_monitor_lists_sessions_with_masked_numbers_only(client):
    fid = _register()
    store.save_channel_turn("sms-x-1", fid, "sms", "***678", "q", "a", [])
    body = client.get("/api/channels/sessions").json()
    assert body["sessions"][0]["masked"] == "***678"
    assert PHONE not in json.dumps(body)


# --- proactive alerts ----------------------------------------------------------------

def test_alert_is_texted_once_with_the_forecast_number(monkeypatch):
    fid = _register()
    store.save_plan(fid, {"farm_id": fid, "crop": "boro_rice", "tasks": []})
    alert = {"alert_id": "rain-1", "farm_id": fid, "task_date": "2026-12-25",
             "task": "ইউরিয়া প্রথম কিস্তি", "provenance": {"value": 23.4}}
    rec = Recorder()
    sms.set_provider(rec)
    first = alerts_job.scan_once(check=lambda f: {"alerts": [alert]})
    second = alerts_job.scan_once(check=lambda f: {"alerts": [alert]})
    assert first["sent"] == 1 and second == {"sent": 0, "already_sent": 1, "errors": 0}
    assert "25/12" in rec.sent[0][1] and "23.4 মিমি" in rec.sent[0][1]


def test_alert_scan_skips_farms_without_a_plan():
    _register()
    assert alerts_job.scan_once(check=lambda f: pytest.fail("should not check")) == {
        "sent": 0, "already_sent": 0, "errors": 0}


# --- ADB call-log parsing ------------------------------------------------------------

def test_parse_call_log_keeps_only_missed_calls():
    out = (
        "Row: 0 number=+8801812345678, date=1727400000000, type=3\n"
        "Row: 1 number=01712345678, date=1727300000000, type=1\n"
        "Row: 2 number=, date=1727200000000, type=3\n"
    )
    assert parse_call_log(out) == [("+8801812345678", 1727400000000)]
