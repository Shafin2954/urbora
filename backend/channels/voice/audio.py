"""Pure audio helpers for the Phone Link bridge (no sound devices here, so
everything is unit-testable): utterance segmentation, resampling, WAV
encode/decode, and parsing the phone's call state from ADB.
"""

from __future__ import annotations

import io
import re
import wave
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

SAMPLE_RATE = 16000          # what VAD and speech-to-text want
FRAME_MS = 30                # webrtcvad accepts 10/20/30 ms frames
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


def resample(x: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Linear-interpolation resample of mono int16 audio. Good enough for
    telephone-band speech (the call itself is ~8 kHz narrowband)."""
    if src_rate == dst_rate or x.size == 0:
        return x.astype(np.int16, copy=False)
    n_out = int(round(x.size * dst_rate / src_rate))
    t_out = np.linspace(0, x.size - 1, n_out)
    return np.interp(t_out, np.arange(x.size), x.astype(np.float32)).astype(np.int16)


def to_wav(pcm: np.ndarray, rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.astype(np.int16).tobytes())
    return buf.getvalue()


def from_wav(data: bytes) -> tuple[np.ndarray, int]:
    """WAV bytes -> (mono int16 samples, rate). Stereo is averaged to mono."""
    with wave.open(io.BytesIO(data), "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"expected 16-bit PCM WAV, got {8 * width}-bit")
    pcm = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1).astype(np.int16)
    return pcm, rate


@dataclass
class Segmenter:
    """Cuts a stream of 30 ms frames into utterances.

    An utterance starts after `start_frames` voiced frames in a row and ends
    after `end_silence_ms` of silence, or at `max_ms` (a farmer describing a
    field can talk for a while; the agent still needs a turn). A short
    pre-roll is kept so the first syllable is not clipped.
    """

    is_speech: Callable[[bytes], bool]
    start_frames: int = 4
    end_silence_ms: int = 900
    max_ms: int = 20000
    preroll_frames: int = 8
    _pre: list[bytes] = field(default_factory=list)
    _cur: list[bytes] = field(default_factory=list)
    _voiced_run: int = 0
    _silence_run: int = 0
    _active: bool = False

    def reset(self) -> None:
        self._pre, self._cur = [], []
        self._voiced_run = self._silence_run = 0
        self._active = False

    def push(self, frame: bytes) -> bytes | None:
        """Feed one 30 ms 16 kHz int16 frame; returns a finished utterance
        (raw PCM bytes) or None."""
        voiced = self.is_speech(frame)
        if not self._active:
            self._pre = (self._pre + [frame])[-self.preroll_frames:]
            self._voiced_run = self._voiced_run + 1 if voiced else 0
            if self._voiced_run >= self.start_frames:
                self._active, self._cur, self._silence_run = True, list(self._pre), 0
            return None
        self._cur.append(frame)
        self._silence_run = 0 if voiced else self._silence_run + 1
        done = (self._silence_run * FRAME_MS >= self.end_silence_ms
                or len(self._cur) * FRAME_MS >= self.max_ms)
        if not done:
            return None
        utterance = b"".join(self._cur)
        self.reset()
        return utterance


def frames(pcm: np.ndarray) -> list[bytes]:
    """Split 16 kHz int16 audio into whole 30 ms frames (the tail is dropped)."""
    n = pcm.size // FRAME_SAMPLES
    return [pcm[i * FRAME_SAMPLES:(i + 1) * FRAME_SAMPLES].tobytes() for i in range(n)]


# --- phone call state over ADB --------------------------------------------------

IDLE, RINGING, OFFHOOK = 0, 1, 2
_STATE = re.compile(r"mCallState=(\d)")
_NUMBER = re.compile(r"mCallIncomingNumber=([+\d]*)")


def parse_call_state(dumpsys: str) -> tuple[int, str | None]:
    """`adb shell dumpsys telephony.registry` -> (state, incoming number).

    Takes the highest state across SIM slots (a dual-SIM phone prints one
    block per slot). The number is None when Android redacts it."""
    states = [int(m) for m in _STATE.findall(dumpsys)] or [IDLE]
    numbers = [n for n in _NUMBER.findall(dumpsys) if n]
    return max(states), (numbers[0] if numbers else None)
