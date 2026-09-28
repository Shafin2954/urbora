"""Missed-call bridge: an Android phone on USB debugging -> the welcome SMS.

A missed call costs the farmer nothing, which is why "give a missed call" is a
common Bangladeshi pattern for opting in. This process polls the phone's call
log over ADB and reports each NEW missed call to the backend, which answers by
SMS (backend/channels/flows.py::handle_missed_call).

It does not touch call audio: Android does not expose the in-call audio path to
apps or to ADB (CAPTURE_AUDIO_OUTPUT is privileged). Real voice calls go
through a USB 4G modem instead — see backend/channels/voice/.

Run, on the laptop the phone is plugged into:

    adb devices                      # the phone must show as "device"
    python -m backend.channels.bridge.adb --backend http://127.0.0.1:8000

Needs BRIDGE_TOKEN in the environment (the same value the backend has). The
call log is read with `content query`, which the adb shell user may read on
stock Android; if your phone refuses, the error is printed, not hidden.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time

import httpx

_ROW = re.compile(r"number=([^,]*),.*?date=(\d+),.*?type=(\d+)")
MISSED = "3"  # android.provider.CallLog.Calls.MISSED_TYPE


def find_adb() -> str:
    """`adb` from ADB env, PATH, or the default Android SDK location on Windows."""
    import shutil
    from pathlib import Path
    if os.environ.get("ADB"):
        return os.environ["ADB"]
    if shutil.which("adb"):
        return "adb"
    sdk = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    return str(sdk) if sdk.is_file() else "adb"


def parse_call_log(output: str) -> list[tuple[str, int]]:
    """`content query` rows -> [(number, epoch_ms)] for missed calls only."""
    calls = []
    for line in output.splitlines():
        m = _ROW.search(line)
        if m and m.group(3) == MISSED and m.group(1).strip():
            calls.append((m.group(1).strip(), int(m.group(2))))
    return calls


def read_missed_calls(adb: str = "adb", serial: str | None = None) -> list[tuple[str, int]]:
    cmd = [adb] + (["-s", serial] if serial else []) + [
        "shell", "content", "query", "--uri", "content://call_log/calls",
        "--projection", "number:date:type", "--sort", "date DESC",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"adb exited {out.returncode}")
    return parse_call_log(out.stdout)


def main(argv: list[str] | None = None) -> int:
    from backend.env import load
    load()  # BRIDGE_TOKEN etc. from .env.local
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", default=os.environ.get("BRIDGE_BACKEND_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between call-log polls")
    ap.add_argument("--adb", default=find_adb())
    ap.add_argument("--serial", default=os.environ.get("ANDROID_SERIAL"))
    args = ap.parse_args(argv)

    token = os.environ.get("BRIDGE_TOKEN", "")
    if not token:
        print("BRIDGE_TOKEN is not set; the backend will refuse the bridge.", file=sys.stderr)
        return 2

    # Only calls that arrive after the bridge starts count; old missed calls
    # in the log are not replayed as fresh opt-ins.
    since_ms = int(time.time() * 1000)
    print(f"watching missed calls -> {args.backend} (Ctrl+C to stop)")
    while True:
        try:
            calls = read_missed_calls(args.adb, args.serial)
        except Exception as exc:  # noqa: BLE001 — keep polling; say why each time
            print(f"call log unreadable: {exc}", file=sys.stderr)
            time.sleep(args.interval)
            continue
        for number, when in sorted(calls, key=lambda c: c[1]):
            if when <= since_ms:
                continue
            since_ms = when
            try:
                r = httpx.post(f"{args.backend.rstrip('/')}/api/channels/bridge/missed-call",
                               json={"msisdn": number}, headers={"X-Bridge-Token": token}, timeout=20)
                print(f"missed call ***{number[-3:]} -> {r.status_code} {r.text[:80]}")
            except httpx.HTTPError as exc:
                print(f"backend unreachable: {type(exc).__name__}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
