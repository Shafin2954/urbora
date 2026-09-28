"""Voice line: speech providers (request shapes), voice turn, hang-up summary."""

from __future__ import annotations

import asyncio
import base64

import pytest

from backend.channels import sms
from backend.channels.adapter import Menu
from backend.channels.identity import farm_id_for
from backend.channels.voice import speech, turn
from backend.memory import store

PHONE = "01812345678"


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "voice.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    for var in ("VOICE_STT", "VOICE_TTS", "SARVAM_API_KEY", "AZURE_SPEECH_KEY", "SMS_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    sms.set_provider(None)
    yield
    sms.set_provider(None)


class Resp:
    def __init__(self, status=200, json_body=None, content=b""):
        self.status_code, self._json, self.content, self.text = status, json_body or {}, content, ""

    def json(self):
        return self._json


# --- provider selection + request shapes ------------------------------------------

def test_sarvam_is_preferred_when_its_key_exists(monkeypatch):
    assert speech.stt_provider() == "openai" and speech.tts_provider() == "openai"
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    assert speech.stt_provider() == "sarvam" and speech.tts_provider() == "sarvam"
    monkeypatch.setenv("VOICE_STT", "openai")
    assert speech.stt_provider() == "openai"


def test_sarvam_stt_request(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    seen = {}

    def fake_post(url, headers, data, files, timeout):
        seen.update(url=url, headers=headers, data=data, files=files)
        return Resp(json_body={"transcript": " রাজশাহীতে 2 বিঘা "})

    monkeypatch.setattr(speech.httpx, "post", fake_post)
    text, used = speech.transcribe(b"abc", "audio/webm;codecs=opus")
    assert text == "রাজশাহীতে 2 বিঘা" and used == "sarvam"
    assert seen["url"] == "https://api.sarvam.ai/speech-to-text"
    assert seen["headers"] == {"api-subscription-key": "k"}
    assert seen["data"]["language_code"] == "bn-IN"
    assert seen["files"]["file"][0] == "speech.webm"


def test_sarvam_v4_sends_keyterms(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    monkeypatch.setenv("SARVAM_STT_MODEL", "saaras:v4")
    seen = {}
    monkeypatch.setattr(speech.httpx, "post",
                        lambda url, headers, data, files, timeout: seen.update(data=data) or Resp(json_body={"transcript": "x"}))
    speech.transcribe(b"a", "audio/wav")
    assert "বোরো" in seen["data"]["keyterms"] and "mode" not in seen["data"]


def test_sarvam_tts_decodes_base64_wav(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    wav = b"RIFF....WAVE"
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, json=json)
        return Resp(json_body={"audios": [base64.b64encode(wav).decode()]})

    monkeypatch.setattr(speech.httpx, "post", fake_post)
    audio, used = speech.synthesize("নমস্কার")
    assert audio.data == wav and audio.content_type == "audio/wav" and used == "sarvam"
    assert seen["json"]["language_code"] == "bn-IN" and seen["json"]["text"] == "নমস্কার"


def test_azure_tts_escapes_text_into_ssml(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "k")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "southeastasia")
    seen = {}

    def fake_post(url, headers, content, timeout):
        seen.update(url=url, content=content.decode())
        return Resp(content=b"mp3")

    monkeypatch.setattr(speech.httpx, "post", fake_post)
    audio, used = speech.synthesize("<খরচ> & লাভ", provider="azure")
    assert used == "azure" and audio.content_type == "audio/mpeg"
    assert "&lt;খরচ&gt; &amp; লাভ" in seen["content"] and "bn-BD-NabanitaNeural" in seen["content"]
    assert seen["url"].startswith("https://southeastasia.tts.speech.microsoft.com/")


def test_missing_keys_raise_speech_errors():
    with pytest.raises(speech.SpeechError):
        speech.transcribe(b"a", "audio/wav", provider="sarvam")
    with pytest.raises(speech.SpeechError):
        speech.transcribe(b"", "audio/wav")


# --- turns ---------------------------------------------------------------------------

def test_spoken_menu_reads_the_options_aloud():
    m = Menu("soil_type", "মাটি কেমন?", [("loam", "দোআঁশ"), ("clay", "এঁটেল")])
    assert turn.spoken_menu(m) == "মাটি কেমন? দোআঁশ হলে 1 বলুন, এঁটেল হলে 2 বলুন।"


def _plan():
    prov = {"value": None, "source_type": "kb", "source_id": "x", "source_title": "x",
            "locator": "x", "retrieved_at": "t", "confidence": "medium"}
    return {"farm_id": "f", "crop": "potato", "tasks": [
        {"date": "2099-11-15", "task": "আলু রোপণ", "category": "sowing", "details": "", "provenance": prov}]}


def test_voice_turn_then_hang_up_texts_the_plan(monkeypatch):
    from backend.agent import loop
    from backend.api import sse

    monkeypatch.setattr(speech, "transcribe", lambda audio, ct, provider=None: ("আলু চাষ করব", "sarvam"))
    monkeypatch.setattr(speech, "synthesize",
                        lambda text, provider=None, wav=False: (speech.Audio(b"wav", "audio/wav"), "sarvam"))
    seen = {}

    async def fake_run_turn(session_id, farm_id, message, client=None, language="bn", channel="web"):
        seen.update(session_id=session_id, message=message, channel=channel)
        yield sse.token("আলুর জন্য পরিকল্পনা তৈরি হয়েছে।")
        yield {"type": "plan_update", "plan": _plan()}
        yield sse.done()

    monkeypatch.setattr(loop, "run_turn", fake_run_turn)
    out = asyncio.run(turn.voice_turn(PHONE, "call-1", b"clip", "audio/webm"))
    assert seen["channel"] == "voice" and seen["message"] == "আলু চাষ করব"
    assert seen["session_id"].startswith("voice-") and seen["session_id"].endswith("-call-1")
    assert out["transcript"] == "আলু চাষ করব" and out["reply_text"].startswith("আলুর জন্য")
    assert base64.b64decode(out["audio_b64"]) == b"wav"

    result = turn.hang_up(PHONE, "call-1")
    assert result["summary_sent"] and "15/11 আলু রোপণ" in result["body"]
    inbox = store.list_sms(farm_id_for(PHONE))
    assert inbox[0]["body"] == result["body"]
    # Call state is cleared: a second hang-up has nothing to send.
    assert turn.hang_up(PHONE, "call-1")["summary_sent"] is False


def test_unheard_audio_asks_again_without_calling_the_agent(monkeypatch):
    from backend.agent import loop

    monkeypatch.setattr(speech, "transcribe", lambda audio, ct, provider=None: ("", "sarvam"))
    monkeypatch.setattr(loop, "run_turn", lambda *a, **k: pytest.fail("agent must not run"))
    out = asyncio.run(turn.voice_turn(PHONE, "c2", b"x", "audio/webm", speak=False))
    assert out["reply_text"] == turn.NOT_HEARD and out["audio_b64"] is None


def test_tts_failure_still_returns_the_text(monkeypatch):
    from backend.agent import loop
    from backend.api import sse

    monkeypatch.setattr(speech, "transcribe", lambda audio, ct, provider=None: ("হ্যালো", "openai"))

    def broken(text, provider=None, wav=False):
        raise speech.SpeechError("no key")

    monkeypatch.setattr(speech, "synthesize", broken)

    async def fake(session_id, farm_id, message, client=None, language="bn", channel="web"):
        yield sse.token("নমস্কার")

    monkeypatch.setattr(loop, "run_turn", fake)
    out = asyncio.run(turn.voice_turn(PHONE, "c3", b"x", "audio/webm"))
    assert out["reply_text"] == "নমস্কার" and out["tts_error"] == "no key"
