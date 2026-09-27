"""Real phone calls through Windows Phone Link — no root, no modem, no card.

How it works (LOG4): Windows 11 Phone Link makes the laptop the Android
phone's Bluetooth hands-free device, so a call to the phone's SIM plays on the
PC and takes its microphone from the PC. Voicemeeter (free) turns those into
two virtual cables:

    caller's voice : Phone Link speaker -> "Voicemeeter Input" (VAIO strip) -> bus B1
                     -> this bridge listens on "Voicemeeter Out B1"
    agent's voice  : this bridge plays into "Voicemeeter AUX Input" (AUX strip) -> bus B2
                     -> Phone Link microphone = "Voicemeeter Out B2"

In Voicemeeter: VAIO strip -> B1 only; AUX strip -> B2 only (optionally both
-> A1 to listen in on headphones). Never route VAIO to B2 (the caller would
hear themselves) or AUX to B1 (the bridge would hear itself).

The call is half-duplex: while the agent thinks and speaks, caller audio is
ignored; after the reply the bridge listens again. The agent runs on the
backend through the token-protected /api/channels/bridge/voice/* routes, so
identity, memory, trace and the SMS summary are exactly the other channels'.

Run (repo root, backend already running, BRIDGE_TOKEN set on both sides):

    python -m backend.channels.voice.phonelink --list-devices
    python -m backend.channels.voice.phonelink --test-capture      # speak on a call; watch the meter
    python -m backend.channels.voice.phonelink --test-playback     # the caller should hear a Bangla line
    python -m backend.channels.voice.phonelink --auto-answer       # the real thing

Limits, stated plainly: one call at a time (one SIM); the caller's number comes
from ADB when Android reveals it, otherwise from --caller; Bluetooth call audio
is narrowband, which speech-to-text handles but does not love.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import os
import queue
import subprocess
import sys
import time
import uuid

import httpx
import numpy as np

from .audio import (FRAME_SAMPLES, IDLE, OFFHOOK, RINGING, SAMPLE_RATE, Segmenter, frames,
                    from_wav, parse_call_state, resample, to_wav)

DEFAULT_CAPTURE = "Voicemeeter Out B1"
DEFAULT_PLAYBACK = "Voicemeeter AUX Input"
GREETING = "আসসালামু আলাইকুম। {brand} কৃষি পরামর্শে স্বাগতম। আপনার জেলা, জমির পরিমাণ আর প্রশ্ন বলুন।"
FILLER = "একটু অপেক্ষা করুন, দেখছি।"
_HOSTAPI_PREFERENCE = ("Windows DirectSound", "MME", "Windows WASAPI")


def _mask(number: str | None) -> str:
    return f"***{number[-3:]}" if number else "unknown"


def find_device(name: str, kind: str) -> int:
    """Index of the first device whose name contains `name` and has `kind`
    ("input"/"output") channels, preferring DirectSound, then MME."""
    import sounddevice as sd
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    hits = [(i, d) for i, d in enumerate(sd.query_devices())
            if name.lower() in d["name"].lower() and d[key] > 0]
    if not hits:
        raise SystemExit(f"No {kind} device matching '{name}'. Run --list-devices.")

    def rank(hit):
        api = sd.query_hostapis(hit[1]["hostapi"])["name"]
        return _HOSTAPI_PREFERENCE.index(api) if api in _HOSTAPI_PREFERENCE else 99
    return sorted(hits, key=rank)[0][0]


class Adb:
    def __init__(self, adb: str = "adb", serial: str | None = None):
        self.base = [adb] + (["-s", serial] if serial else [])

    def _run(self, *args: str) -> str:
        out = subprocess.run(self.base + list(args), capture_output=True, text=True, timeout=10)
        return out.stdout

    def call_state(self) -> tuple[int, str | None]:
        state, number = parse_call_state(self._run("shell", "dumpsys", "telephony.registry"))
        if state != IDLE and not number:
            # Some phones hide the number from telephony.registry but show it in telecom.
            import re
            m = re.search(r"tel:(\+?\d{10,14})", self._run("shell", "dumpsys", "telecom"))
            number = m.group(1) if m else None
        return state, number

    def answer(self) -> None:
        self._run("shell", "input", "keyevent", "KEYCODE_CALL")


class Bridge:
    def __init__(self, backend: str, token: str, capture: int, playback: int,
                 caller: str | None, adb: Adb | None, auto_answer: bool):
        import sounddevice as sd
        import webrtcvad

        self.sd = sd
        self.http = httpx.Client(base_url=backend.rstrip("/"), headers={"X-Bridge-Token": token}, timeout=90)
        self.capture, self.playback = capture, playback
        self.caller, self.adb, self.auto_answer = caller, adb, auto_answer
        self.in_rate = int(sd.query_devices(capture)["default_samplerate"])
        self.q: queue.Queue[np.ndarray] = queue.Queue()
        vad = webrtcvad.Vad(2)
        self.segmenter = Segmenter(lambda f: vad.is_speech(f, SAMPLE_RATE))
        self.buffer = np.zeros(0, dtype=np.int16)
        self.say_cache: dict[str, tuple[np.ndarray, int]] = {}
        self.call_id: str | None = None
        self.number: str | None = None

    # --- audio --------------------------------------------------------------------

    def _on_audio(self, indata, _frames, _time, status) -> None:
        self.q.put(indata[:, 0].copy())

    def _drain(self) -> None:
        while not self.q.empty():
            self.q.get_nowait()
        self.buffer = np.zeros(0, dtype=np.int16)
        self.segmenter.reset()

    def play(self, pcm: np.ndarray, rate: int) -> None:
        self.sd.play(pcm, rate, device=self.playback, blocking=True)

    def say(self, text: str) -> None:
        if text not in self.say_cache:
            r = self.http.post("/api/channels/bridge/voice/say", json={"text": text})
            r.raise_for_status()
            self.say_cache[text] = from_wav(base64.b64decode(r.json()["audio_b64"]))
        self.play(*self.say_cache[text])

    # --- call lifecycle -----------------------------------------------------------------

    def start_call(self, number: str | None) -> None:
        from backend.branding import BRAND_NAME_BN
        self.number = number or self.caller
        if not self.number:
            print("call started but the caller's number is hidden and no --caller was given; "
                  "not answering as an unknown farmer", file=sys.stderr)
            return
        self.call_id = f"pl-{uuid.uuid4().hex[:12]}"
        print(f"call {self.call_id} from {_mask(self.number)}")
        self.say(GREETING.format(brand=BRAND_NAME_BN))
        self._drain()

    def end_call(self) -> None:
        if not self.call_id:
            return
        try:
            r = self.http.post("/api/channels/bridge/voice/hangup",
                               json={"msisdn": self.number, "call_id": self.call_id})
            print(f"call {self.call_id} ended; summary SMS sent: {r.json().get('summary_sent')}")
        except httpx.HTTPError as exc:
            print(f"hang-up report failed: {type(exc).__name__}", file=sys.stderr)
        self.call_id = self.number = None
        self._drain()

    def turn(self, utterance: bytes) -> None:
        wav = to_wav(np.frombuffer(utterance, dtype=np.int16))
        with cf.ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                self.http.post, "/api/channels/bridge/voice/turn",
                data={"msisdn": self.number, "call_id": self.call_id},
                files={"file": ("utterance.wav", wav, "audio/wav")},
            )
            self.say(FILLER)  # covers the agent's thinking time
            try:
                r = pending.result()
                r.raise_for_status()
                body = r.json()
            except (httpx.HTTPError, ValueError) as exc:
                print(f"turn failed: {exc}", file=sys.stderr)
                self.say("দুঃখিত, এখন উত্তর দিতে পারছি না। আবার বলুন।")
                return
        print(f"  heard: {body.get('transcript')!r}\n  said:  {body.get('reply_text')!r}")
        if body.get("audio_b64"):
            self.play(*from_wav(base64.b64decode(body["audio_b64"])))
        self._drain()

    # --- main loop ------------------------------------------------------------------------

    def feed(self) -> bytes | None:
        """Move captured audio through resampling and VAD; return a finished utterance."""
        try:
            chunk = self.q.get(timeout=0.1)
        except queue.Empty:
            return None
        self.buffer = np.concatenate([self.buffer, resample(chunk, self.in_rate, SAMPLE_RATE)])
        whole = (self.buffer.size // FRAME_SAMPLES) * FRAME_SAMPLES
        done = None
        for frame in frames(self.buffer[:whole]):
            done = self.segmenter.push(frame) or done
        self.buffer = self.buffer[whole:]
        return done

    def run(self, always_on: bool) -> None:
        with self.sd.InputStream(device=self.capture, samplerate=self.in_rate, channels=1,
                                 dtype="int16", blocksize=int(self.in_rate * 0.03), callback=self._on_audio):
            if always_on:
                self.start_call(self.caller)
            last_poll, answered = 0.0, False
            while True:
                if self.adb and time.monotonic() - last_poll > 0.5:
                    last_poll = time.monotonic()
                    state, number = self.adb.call_state()
                    if state == RINGING and self.auto_answer and not answered:
                        print(f"ringing from {_mask(number)}; answering")
                        self.adb.answer()
                        answered = True
                    elif state == OFFHOOK and not self.call_id:
                        self.start_call(number)
                    elif state == IDLE:
                        answered = False
                        if self.call_id:
                            self.end_call()
                utterance = self.feed()
                if utterance and self.call_id:
                    self.turn(utterance)


def _test_capture(device: int, seconds: float = 8.0) -> None:
    import sounddevice as sd
    rate = int(sd.query_devices(device)["default_samplerate"])
    print(f"listening on device {device} for {seconds:g}s — speak into the call")
    rec = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype="int16", device=device)
    for tick in range(int(seconds * 4)):
        time.sleep(0.25)
        level = int(np.abs(rec[: int((tick + 1) * rate / 4)]).max() / 327.67) if rec.size else 0
        print(f"\r  peak level so far: {level:3d}% ", end="")
    sd.wait()
    print("\n  0% means nothing arrives: check Phone Link's speaker -> Voicemeeter Input, VAIO -> B1.")


def main(argv: list[str] | None = None) -> int:
    from backend.env import load
    load()
    ap = argparse.ArgumentParser(description="Bridge real phone calls (Windows Phone Link) to the agent.")
    ap.add_argument("--backend", default=os.environ.get("BRIDGE_BACKEND_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--capture", default=os.environ.get("PHONELINK_CAPTURE", DEFAULT_CAPTURE))
    ap.add_argument("--playback", default=os.environ.get("PHONELINK_PLAYBACK", DEFAULT_PLAYBACK))
    ap.add_argument("--caller", default=os.environ.get("PHONELINK_DEFAULT_CALLER"),
                    help="number to use when Android hides the caller's number")
    ap.add_argument("--no-adb", action="store_true", help="do not watch call state over ADB")
    ap.add_argument("--auto-answer", action="store_true", help="answer ringing calls over ADB")
    ap.add_argument("--always-on", action="store_true", help="treat the audio as one ongoing call (testing)")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--test-capture", action="store_true")
    ap.add_argument("--test-playback", action="store_true")
    args = ap.parse_args(argv)

    import sounddevice as sd
    if args.list_devices:
        for i, d in enumerate(sd.query_devices()):
            kind = ("in " if d["max_input_channels"] else "") + ("out" if d["max_output_channels"] else "")
            print(f"{i:3d}  {kind:6s} {sd.query_hostapis(d['hostapi'])['name']:20s} {d['name']}")
        return 0
    capture, playback = find_device(args.capture, "input"), find_device(args.playback, "output")
    if args.test_capture:
        _test_capture(capture)
        return 0

    token = os.environ.get("BRIDGE_TOKEN", "")
    if not token:
        print("BRIDGE_TOKEN is not set (same value as the backend's).", file=sys.stderr)
        return 2
    from backend.channels.bridge.adb import find_adb
    adb = None if args.no_adb or args.always_on else Adb(find_adb(), os.environ.get("ANDROID_SERIAL"))
    bridge = Bridge(args.backend, token, capture, playback, args.caller, adb, args.auto_answer)
    if args.test_playback:
        from backend.branding import BRAND_NAME_BN
        bridge.say(GREETING.format(brand=BRAND_NAME_BN))
        return 0
    if args.always_on and not args.caller:
        print("--always-on needs --caller (whose farm this test call belongs to).", file=sys.stderr)
        return 2
    print(f"bridge: capture='{sd.query_devices(capture)['name']}', playback='{sd.query_devices(playback)['name']}', "
          f"backend={args.backend}. Ctrl+C to stop.")
    try:
        bridge.run(args.always_on)
    except KeyboardInterrupt:
        bridge.end_call()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
