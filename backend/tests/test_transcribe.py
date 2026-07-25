"""transcribe route — container handling, limits, and language clamping.

No network. The OpenAI call is stubbed, because what can actually break here is
the plumbing around it: an extension that does not match the bytes is rejected
upstream with "file might be corrupted or unsupported", which is exactly the bug
this file exists to prevent recurring.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api import transcribe as module
from backend.api.main import app

client = TestClient(app)


class _Result:
    text = "  আমার দিনাজপুরে এক বিঘা জমি আছে।  "


@pytest.fixture
def captured(monkeypatch):
    """Swap the OpenAI client for a recorder, so the test can assert on what
    would have been sent."""
    seen = {}

    class _Transcriptions:
        def create(self, **kwargs):
            seen.update(kwargs)
            seen["filename"] = getattr(kwargs["file"], "name", None)
            return _Result()

    class _Audio:
        transcriptions = _Transcriptions()

    class _Client:
        audio = _Audio()

    monkeypatch.setattr(module, "_client", lambda: _Client())
    return seen


@pytest.mark.parametrize(
    "content_type,expected",
    [
        # MediaRecorder always appends a codecs parameter; the raw string never
        # matches a bare MIME key, which is why _base_type exists.
        ("audio/webm;codecs=opus", "speech.webm"),
        ("video/webm", "speech.webm"),          # Chromium's label for audio-only webm
        ("audio/mp4", "speech.mp4"),            # Safari
        ("audio/mpeg", "speech.mp3"),
        ("audio/ogg;codecs=opus", "speech.ogg"),
        ("application/octet-stream", "speech.webm"),  # unknown -> the common case
    ],
)
def test_extension_follows_the_container_the_browser_produced(captured, content_type, expected):
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip", b"x" * 2048, content_type)},
        data={"language": "bn"},
    )
    assert response.status_code == 200
    assert captured["filename"] == expected


def test_transcript_is_returned_trimmed(captured):
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip", b"x" * 2048, "audio/webm")},
        data={"language": "bn"},
    )
    assert response.json()["text"] == "আমার দিনাজপুরে এক বিঘা জমি আছে।"


def test_language_hint_is_passed_through_and_clamped(captured):
    client.post("/api/transcribe", files={"file": ("c", b"x" * 2048, "audio/webm")},
                data={"language": "en"})
    assert captured["language"] == "en"

    # Anything outside the supported set falls back to Bangla rather than being
    # forwarded — an unsupported code is a hard 400 upstream.
    client.post("/api/transcribe", files={"file": ("c", b"x" * 2048, "audio/webm")},
                data={"language": "de"})
    assert captured["language"] == "bn"


def test_model_is_not_whisper_1(captured):
    """whisper-1 transcribes Bangla into Devanagari and rejects language='bn'.
    Verified 2026-07-25 — see the note in transcribe.py."""
    client.post("/api/transcribe", files={"file": ("c", b"x" * 2048, "audio/webm")},
                data={"language": "bn"})
    assert captured["model"] == "gpt-4o-transcribe"
    assert captured["model"] != "whisper-1"


def test_empty_upload_is_rejected(captured):
    response = client.post("/api/transcribe", files={"file": ("c", b"", "audio/webm")})
    assert response.status_code == 400


def test_oversized_upload_is_rejected(captured):
    payload = b"x" * (module._MAX_BYTES + 1)
    response = client.post("/api/transcribe", files={"file": ("c", payload, "audio/webm")})
    assert response.status_code == 413


def test_upstream_failure_is_502_not_500(monkeypatch):
    """Our route was fine; the transcription provider failed. The distinction
    matters when reading logs at 4am."""
    class _Boom:
        class audio:
            class transcriptions:
                @staticmethod
                def create(**_):
                    raise RuntimeError("provider exploded")

    monkeypatch.setattr(module, "_client", lambda: _Boom())
    response = client.post("/api/transcribe", files={"file": ("c", b"x" * 2048, "audio/webm")})
    assert response.status_code == 502
