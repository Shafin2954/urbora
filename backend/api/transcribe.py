"""Speech-to-text for the composer microphone (competition.md Tier 2, voice).

    POST /api/transcribe    multipart audio -> {"text": ...}
    GET  /api/transcribe/status

Why this exists at all
----------------------
The first version of the microphone used the browser's own Web Speech API. It
needed no backend and no key, which was the appeal. It also does not work: Brave
keeps the `webkitSpeechRecognition` constructor but blocks the Google relay it
depends on, so `start()` succeeds and the very next event is a `network` error —
the mic lights up for a second and dies. Firefox has never shipped the API at
all. Bangla dictation was therefore a browser-and-vendor lottery, and the
browser this project is actually demoed in loses it.

So recognition moved server-side, onto OpenAI transcription via the SDK that is
already a pinned dependency and already has a key configured. The client records
with `MediaRecorder`, which every current browser supports, and posts the blob
here. One code path, every browser, and far better Bengali than either the
browser recogniser or whisper-1 managed (see the model note below).

The cost is real and worth stating: dictation now needs the network and the
backend, where the old path ran on-device. It also sends the farmer's voice clip
to OpenAI — the same provider already receiving every message they type, so it
widens no boundary that was not already crossed, but the README says so plainly.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()

# Roughly a minute of Opus at typical MediaRecorder bitrates. A farmer asking a
# question does not need more, and an unbounded upload is a free denial of
# service against a hackathon laptop.
_MAX_BYTES = 8 * 1024 * 1024

# gpt-4o-transcribe, NOT whisper-1. Verified against synthesized Bangla speech
# on 2026-07-25, and the difference is not marginal:
#
#   whisper-1              "अमर दिनजपूरे एक बिगा जमी अछे"   <- DEVANAGARI. It
#                          transcribed Bangla into Hindi script, and it rejects
#                          language="bn" outright with unsupported_language.
#   gpt-4o-mini-transcribe "আমার দিনেচপুরে ... রবি মাক্সুমে"  <- right script,
#                          but mangles the district name and "মৌসুম".
#   gpt-4o-transcribe      "আমার দিনাজপুরে এক বিঘা জমি আছে। এই রবি মৌসুমে কোন
#                          ফসল চাষ করবো?"                    <- exact.
#
# A district name is the single most load-bearing word a farmer says here — it
# picks the coordinates, the yield history and the weather. Getting it wrong is
# worse than not hearing it at all.
_MODEL = "gpt-4o-transcribe"

# Accuracy improves markedly when the model is told the language instead of
# guessing — and guessing is exactly where Bangla loses. (whisper-1 could not
# accept this hint at all, which is part of why it is not the model here.)
_LANGS = {"bn", "en"}

# Containers the transcription endpoint accepts, keyed by the MIME type a
# browser (or curl, in a test) will actually send.
_EXTENSION_FOR = {
    "audio/webm": "webm",
    "video/webm": "webm",      # what Chromium labels an audio-only webm as
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}


def _base_type(content_type: str | None) -> str:
    """'audio/webm;codecs=opus' -> 'audio/webm'. MediaRecorder always appends a
    codecs parameter, and the raw string never matches a bare MIME key."""
    return (content_type or "").split(";")[0].strip().lower()


def _client():
    """Build the OpenAI client the same way the agent loop does, so both read
    the same key from the same place and fail the same way if it is missing."""
    from backend.agent.config import AgentConfig  # noqa: PLC0415
    from openai import OpenAI  # noqa: PLC0415

    cfg = AgentConfig.from_env()
    return OpenAI(api_key=cfg.api_key)


@router.get("/api/transcribe/status")
async def transcribe_status() -> dict:
    """Whether dictation is usable on this deployment — the UI hides the
    microphone rather than offering a button that will fail."""
    try:
        _client()
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "model": _MODEL, "detail": f"{type(exc).__name__}: {exc}"}
    return {"available": True, "model": _MODEL, "detail": None}


@router.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("bn"),
) -> dict:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="empty recording")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"recording larger than {_MAX_BYTES // (1024 * 1024)} MB")

    lang = language if language in _LANGS else "bn"

    # The decoder is picked from the filename extension, so it has to match the
    # bytes. MediaRecorder emits audio/webm on Chromium and audio/mp4 on Safari,
    # and the container it chose arrives in the part's content type — trust that
    # rather than assuming one. Guessing wrong is not a soft failure: the API
    # rejects the upload outright with "file might be corrupted or unsupported".
    buffer = io.BytesIO(payload)
    buffer.name = f"speech.{_EXTENSION_FOR.get(_base_type(file.content_type), 'webm')}"

    try:
        result = _client().audio.transcriptions.create(
            model=_MODEL,
            file=buffer,
            language=lang,
            # Bangla agricultural vocabulary that transcription otherwise tends
            # to mangle into similar-sounding everyday words. This is a decoding
            # hint, not training data — it cannot put words in the farmer's mouth.
            prompt=(
                "কৃষি, ফসল, ধান, বোরো, আমন, আলু, সরিষা, মসুর, সার, ইউরিয়া, টিএসপি, "
                "সেচ, বিঘা, কাঠা, শতক, জমি, বাজেট, মৌসুম, রবি, খরিফ, পোকা, রোগ"
                if lang == "bn"
                else "agriculture, crop, paddy, boro, aman, potato, mustard, lentil, "
                     "urea, TSP, irrigation, bigha, katha, decimal, budget, season, rabi"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        # 502, not 500: our route is fine, the upstream transcription failed.
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc

    return {"text": (getattr(result, "text", "") or "").strip(), "language": lang, "model": _MODEL}
