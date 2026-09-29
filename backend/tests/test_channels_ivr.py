"""Keypad menu on the hotline: DTMF detection and the spoken menu."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.channels import sms, ussd
from backend.channels.voice import ivr
from backend.channels.voice.audio import FRAME_SAMPLES, DtmfDetector, dtmf_key, dtmf_tone, resample
from backend.memory import store

PHONE = "01812345678"


def _keys(sig: np.ndarray) -> list[str]:
    d, out = DtmfDetector(), []
    for i in range(0, sig.size - FRAME_SAMPLES + 1, FRAME_SAMPLES):
        k = d.push(sig[i:i + FRAME_SAMPLES])
        if k:
            out.append(k)
    return out


def _sequence(keys: str) -> np.ndarray:
    gap = np.zeros(1600, dtype=np.int16)
    return np.concatenate([np.concatenate([dtmf_tone(k), gap]) for k in keys])


# --- detection ------------------------------------------------------------------------------


def test_every_phone_key_is_detected_once():
    assert _keys(_sequence("123456789*0#")) == list("123456789*0#")


def test_detection_survives_noise_and_the_telephone_band():
    rng = np.random.default_rng(1)
    sig = _sequence("2580")
    noisy = (sig + rng.normal(0, 1500, sig.size)).clip(-32768, 32767).astype(np.int16)
    narrow = resample(resample(noisy, 16000, 8000), 8000, 16000)
    assert _keys(narrow) == list("2580")


def test_the_same_key_twice_needs_a_gap():
    assert _keys(_sequence("11")) == ["1", "1"]
    assert _keys(dtmf_tone("5", ms=600)) == ["5"]  # a long press is one press


def test_speech_like_audio_and_noise_are_not_keys():
    t = np.arange(32000) / 16000
    voice = (sum(np.sin(2 * np.pi * 150 * h * t) / h for h in range(1, 25)) * 3000).astype(np.int16)
    noise = np.random.default_rng(2).normal(0, 4000, 32000).astype(np.int16)
    assert _keys(voice) == [] and _keys(noise) == []
    assert dtmf_key(np.zeros(FRAME_SAMPLES, dtype=np.int16)) is None


# --- the spoken menu ---------------------------------------------------------------------------


def test_screen_becomes_speech():
    spoken = ivr.speakable("Brand\n1. ফসল পরামর্শ\n2. ফসলের সমস্যা\n9. আরও")
    assert spoken == "Brand। ফসল পরামর্শ, 1 চাপুন। ফসলের সমস্যা, 2 চাপুন। আরও শুনতে 9 চাপুন।"
    assert "# চাপুন" in ivr.speakable("জমি কত বিঘা?\nসংখ্যা লিখুন\n0. পিছনে")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "ivr.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    sms.set_provider(None)
    yield
    sms.set_provider(None)


def _press(*seq, call="c1"):
    async def go():
        out = None
        for k in seq:
            out = await ivr.keys(PHONE, call, k)
        await asyncio.gather(*list(ussd._background))
        return out
    return asyncio.run(go())


def test_first_key_opens_the_menu_and_applies_the_choice(db):
    out = _press("2")                      # straight into the crop-problem menu
    assert "আমন ধান, 1 চাপুন" in out["text"] and not out["end"]


def test_a_problem_reported_by_keypad_is_answered_on_the_call_and_by_sms(db):
    from backend.channels.identity import farm_id_for
    out = _press("2", "5", "3", "4", "2", "2")  # lentil, flowering, pod, holes, half
    assert out["end"] and "ফল ছিদ্রকারী পোকা" in out["text"] and "SMS-এও" in out["text"]
    assert "ফল ছিদ্রকারী পোকা" in store.list_sms(farm_id_for(PHONE))[0]["body"]


def test_number_screens_ask_for_hash_terminated_digits(db):
    from backend.tests.test_channels_ussd import to_district
    out = _press(*(["1"] + to_district()))
    assert out["expects_number"] and "# চাপুন" in out["text"]
    out = _press("2#", call="c1")
    assert not out["expects_number"] and "মাটি" in out["text"]


def test_star_repeats_the_current_screen(db):
    first = _press("2")
    again = _press("*")
    assert again["screen"] == first["screen"]


# --- routes ------------------------------------------------------------------------------------


def test_keypad_routes(db, monkeypatch):
    from backend.api.main import app
    from backend.channels.voice import speech

    def no_tts(*a, **k):
        raise speech.SpeechError("no key")

    monkeypatch.setattr(speech, "synthesize", no_tts)
    client = TestClient(app)
    r = client.post("/api/channels/emulator/voice/keys", json={"msisdn": PHONE, "call_id": "e1", "keys": "1"})
    assert r.status_code == 200 and r.json()["tts_error"] == "no key" and r.json()["text"]
    assert client.post("/api/channels/emulator/voice/keys",
                       json={"msisdn": PHONE, "call_id": "e1", "keys": "1a"}).status_code == 422
    monkeypatch.setenv("BRIDGE_TOKEN", "t")
    assert client.post("/api/channels/bridge/voice/keys",
                       json={"msisdn": PHONE, "call_id": "b1", "keys": "1"}).status_code == 401
