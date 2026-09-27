"""Bangla speech-to-text and text-to-speech, provider-swappable.

Choice of provider is evidence-led (LOG4 [23:20]):

- STT: **Sarvam** by default when `SARVAM_API_KEY` is set. A Sep-2026 Bangla
  benchmark (riverbornai, 1,001 clips) measured Sarvam at 6.9% CER against
  28.7% for `gpt-4o-transcribe`, which stays as the fallback because it is the
  model the July build verified on our district-name sentence. Force either
  with `VOICE_STT=sarvam|openai`.
- TTS: `VOICE_TTS=sarvam|azure|openai`. Azure's `bn-BD` voices carry a Dhaka
  accent; Sarvam's Bulbul is Indian Bengali. The choice is a listening test,
  recorded in README — this module only makes it a config switch.

All calls are plain HTTPS (httpx); no provider SDK is added.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from html import escape

import httpx

SARVAM_BASE = "https://api.sarvam.ai"
TIMEOUT = 30.0

# Words the recogniser should expect on this line: the five crops, inputs,
# units, seasons. Sent as Sarvam v4 `keyterms` / OpenAI `prompt`. A decoding
# hint, never text put into the farmer's mouth.
KEYTERMS_BN = [
    "বোরো", "আমন", "আলু", "সরিষা", "মসুর", "ধান", "ইউরিয়া", "টিএসপি", "এমওপি",
    "সেচ", "নলকূপ", "বিঘা", "কাঠা", "শতাংশ", "রবি", "খরিপ", "দোআঁশ", "এঁটেল",
    "বেলে", "রাজশাহী", "দিনাজপুর", "বগুড়া", "রংপুর", "ময়মনসিংহ",
]


class SpeechError(RuntimeError):
    pass


@dataclass
class Audio:
    data: bytes
    content_type: str


def _ext(content_type: str) -> str:
    base = (content_type or "").split(";")[0].strip().lower()
    return {
        "audio/webm": "webm", "video/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4",
        "audio/x-m4a": "m4a", "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
        "audio/x-wav": "wav", "audio/flac": "flac",
    }.get(base, "webm")


def stt_provider() -> str:
    forced = os.environ.get("VOICE_STT", "").strip().lower()
    if forced in ("sarvam", "openai"):
        return forced
    return "sarvam" if os.environ.get("SARVAM_API_KEY") else "openai"


def tts_provider() -> str:
    forced = os.environ.get("VOICE_TTS", "").strip().lower()
    if forced in ("sarvam", "azure", "openai"):
        return forced
    if os.environ.get("SARVAM_API_KEY"):
        return "sarvam"
    if os.environ.get("AZURE_SPEECH_KEY"):
        return "azure"
    return "openai"


# --- STT --------------------------------------------------------------------


def _stt_sarvam(audio: bytes, content_type: str) -> str:
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key:
        raise SpeechError("SARVAM_API_KEY is not set")
    model = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
    data = {"model": model, "language_code": "bn-IN"}
    if model.endswith("v3"):
        data["mode"] = "transcribe"
    if model.endswith("v4"):
        data["keyterms"] = ",".join(KEYTERMS_BN)
    files = {"file": (f"speech.{_ext(content_type)}", audio, content_type or "audio/webm")}
    r = httpx.post(f"{SARVAM_BASE}/speech-to-text", headers={"api-subscription-key": key},
                   data=data, files=files, timeout=TIMEOUT)
    if r.status_code >= 300:
        raise SpeechError(f"Sarvam STT HTTP {r.status_code}: {r.text[:200]}")
    return (r.json().get("transcript") or "").strip()


def _stt_openai(audio: bytes, content_type: str) -> str:
    from backend.agent.config import AgentConfig
    from openai import OpenAI

    buf = io.BytesIO(audio)
    buf.name = f"speech.{_ext(content_type)}"
    try:
        result = OpenAI(api_key=AgentConfig.from_env().api_key).audio.transcriptions.create(
            model="gpt-4o-transcribe", file=buf, language="bn", prompt=", ".join(KEYTERMS_BN),
        )
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(f"OpenAI STT: {type(exc).__name__}: {exc}") from exc
    return (getattr(result, "text", "") or "").strip()


def transcribe(audio: bytes, content_type: str, provider: str | None = None) -> tuple[str, str]:
    """-> (transcript, provider used)."""
    if not audio:
        raise SpeechError("empty recording")
    p = provider or stt_provider()
    text = _stt_sarvam(audio, content_type) if p == "sarvam" else _stt_openai(audio, content_type)
    return text, p


# --- TTS --------------------------------------------------------------------


def _tts_sarvam(text: str) -> Audio:
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key:
        raise SpeechError("SARVAM_API_KEY is not set")
    body = {"text": text[:2500], "language_code": "bn-IN",
            "model": os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3")}
    if os.environ.get("SARVAM_TTS_SPEAKER"):
        body["speaker"] = os.environ["SARVAM_TTS_SPEAKER"]
    r = httpx.post(f"{SARVAM_BASE}/text-to-speech", headers={"api-subscription-key": key},
                   json=body, timeout=TIMEOUT)
    if r.status_code >= 300:
        raise SpeechError(f"Sarvam TTS HTTP {r.status_code}: {r.text[:200]}")
    audios = r.json().get("audios") or []
    if not audios:
        raise SpeechError("Sarvam TTS returned no audio")
    return Audio(base64.b64decode(audios[0]), "audio/wav")


def _tts_azure(text: str, wav: bool = False) -> Audio:
    key, region = os.environ.get("AZURE_SPEECH_KEY", ""), os.environ.get("AZURE_SPEECH_REGION", "")
    if not (key and region):
        raise SpeechError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required")
    voice = os.environ.get("AZURE_TTS_VOICE", "bn-BD-NabanitaNeural")
    ssml = (f"<speak version='1.0' xml:lang='bn-BD'><voice name='{voice}'>"
            f"{escape(text)}</voice></speak>")
    r = httpx.post(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm" if wav else "audio-24khz-48kbitrate-mono-mp3"},
        content=ssml.encode("utf-8"), timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise SpeechError(f"Azure TTS HTTP {r.status_code}")
    return Audio(r.content, "audio/wav" if wav else "audio/mpeg")


def _tts_openai(text: str, wav: bool = False) -> Audio:
    from backend.agent.config import AgentConfig
    from openai import OpenAI

    try:
        resp = OpenAI(api_key=AgentConfig.from_env().api_key).audio.speech.create(
            model=os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            voice=os.environ.get("OPENAI_TTS_VOICE", "alloy"), input=text[:4000],
            response_format="wav" if wav else "mp3",
        )
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(f"OpenAI TTS: {type(exc).__name__}: {exc}") from exc
    return Audio(resp.read(), "audio/wav" if wav else "audio/mpeg")


def synthesize(text: str, provider: str | None = None, wav: bool = False) -> tuple[Audio, str]:
    """-> (audio, provider used). `wav=True` forces plain WAV (the Phone Link
    bridge plays it straight to a sound device with no decoder)."""
    p = provider or tts_provider()
    if p == "sarvam":
        return _tts_sarvam(text), p  # Sarvam always returns WAV
    if p == "azure":
        return _tts_azure(text, wav), p
    return _tts_openai(text, wav), p


def status() -> dict:
    return {"stt": stt_provider(), "tts": tts_provider(),
            "sarvam_key": bool(os.environ.get("SARVAM_API_KEY")),
            "azure_key": bool(os.environ.get("AZURE_SPEECH_KEY"))}
