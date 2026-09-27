"""Phone Link voice bridge: pure audio helpers + the bridge routes."""

from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.channels.voice import audio

SILENT = bytes(audio.FRAME_SAMPLES * 2)
LOUD = (np.ones(audio.FRAME_SAMPLES, dtype=np.int16) * 3000).tobytes()


def seg(**kw):
    return audio.Segmenter(lambda f: f == LOUD, **kw)


def test_resample_keeps_duration():
    x = np.arange(44100, dtype=np.int16)
    assert audio.resample(x, 44100, 16000).size == 16000
    assert audio.resample(x, 16000, 16000) is not None


def test_wav_round_trip_and_stereo_to_mono():
    pcm = (np.sin(np.linspace(0, 50, 1600)) * 8000).astype(np.int16)
    back, rate = audio.from_wav(audio.to_wav(pcm, 16000))
    assert rate == 16000 and np.array_equal(back, pcm)
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(np.array([100, 300] * 10, dtype=np.int16).tobytes())
    mono, _ = audio.from_wav(buf.getvalue())
    assert mono.size == 10 and int(mono[0]) == 200


def test_segmenter_needs_sustained_speech_to_start():
    s = seg(start_frames=4)
    for f in [LOUD, SILENT, LOUD, LOUD, SILENT]:
        assert s.push(f) is None
    assert not s._active


def test_segmenter_ends_after_silence_and_keeps_preroll():
    s = seg(start_frames=3, end_silence_ms=90, preroll_frames=2)
    out = None
    for f in [SILENT] * 5 + [LOUD] * 5 + [SILENT] * 3:
        out = s.push(f) or out
    assert out is not None
    n_frames = len(out) // (audio.FRAME_SAMPLES * 2)
    assert n_frames == 2 + 2 + 3  # preroll (incl. 1st voiced) + remaining voiced + silence
    assert s.push(SILENT) is None  # reset after an utterance


def test_segmenter_caps_long_speech():
    s = seg(start_frames=1, max_ms=300)
    outs = [s.push(LOUD) for _ in range(20)]
    assert any(o is not None for o in outs)


def test_frames_split_into_30ms():
    pcm = np.zeros(audio.FRAME_SAMPLES * 3 + 7, dtype=np.int16)
    assert len(audio.frames(pcm)) == 3


def test_parse_call_state_dual_sim():
    dump = ("  mCallState=0\n  mCallIncomingNumber=\n"
            "  mCallState=1\n  mCallIncomingNumber=+8801812345678\n")
    assert audio.parse_call_state(dump) == (audio.RINGING, "+8801812345678")
    assert audio.parse_call_state("mCallState=2\nmCallIncomingNumber=\n") == (audio.OFFHOOK, None)
    assert audio.parse_call_state("garbage") == (audio.IDLE, None)


# --- routes ------------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from backend.memory import store
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "bridge.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "t")
    monkeypatch.setenv("BRIDGE_TOKEN", "secret")
    from backend.api.main import app
    return TestClient(app)


def test_bridge_voice_routes_need_the_token(client):
    wav = audio.to_wav(np.zeros(1600, dtype=np.int16))
    r = client.post("/api/channels/bridge/voice/turn", data={"msisdn": "01812345678", "call_id": "c"},
                    files={"file": ("u.wav", wav, "audio/wav")})
    assert r.status_code == 401
    assert client.post("/api/channels/bridge/voice/say", json={"text": "x"}).status_code == 401


def test_bridge_turn_asks_for_wav(client, monkeypatch):
    from backend.channels.voice import turn
    seen = {}

    async def fake(msisdn, call_id, audio_bytes, content_type, *, speak=True, wav=False):
        seen.update(wav=wav, content_type=content_type, call_id=call_id)
        return {"transcript": "x", "reply_text": "y", "audio_b64": None}

    monkeypatch.setattr(turn, "voice_turn", fake)
    wav = audio.to_wav(np.zeros(1600, dtype=np.int16))
    r = client.post("/api/channels/bridge/voice/turn", headers={"X-Bridge-Token": "secret"},
                    data={"msisdn": "01812345678", "call_id": "pl-1"}, files={"file": ("u.wav", wav, "audio/wav")})
    assert r.status_code == 200 and seen == {"wav": True, "content_type": "audio/wav", "call_id": "pl-1"}


def test_bridge_say_returns_wav(client, monkeypatch):
    from backend.channels.voice import speech
    monkeypatch.setattr(speech, "synthesize", lambda text, provider=None, wav=False:
                        (speech.Audio(b"RIFFdata", "audio/wav" if wav else "audio/mpeg"), "sarvam"))
    r = client.post("/api/channels/bridge/voice/say", headers={"X-Bridge-Token": "secret"}, json={"text": "হ্যালো"})
    assert r.json()["audio_type"] == "audio/wav" and base64.b64decode(r.json()["audio_b64"]) == b"RIFFdata"
