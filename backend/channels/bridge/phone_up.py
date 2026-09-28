"""Bring the Android phone up as the SMS gateway, over USB only.

One command, re-runnable, no Wi-Fi involved:

    python -m backend.channels.bridge.phone_up            # set up once, print a checklist
    python -m backend.channels.bridge.phone_up --watch    # keep it up across USB reconnects

What it does (docs.sms-gate.app, checked Sep 2026):

1. waits for the phone on ADB;
2. exempts SMS Gateway (`me.capcom.smsgateway`) from battery optimisation —
   Samsung kills the local server otherwise (local-server FAQ);
3. `adb forward tcp:8080 tcp:8080` — the laptop reaches the phone's Local
   Server at http://127.0.0.1:8080 (SMSGATE_URL);
4. `adb reverse tcp:8000 tcp:8000` — the phone reaches the backend at
   http://127.0.0.1:8000. SMSGate accepts plain-HTTP webhooks only for
   127.0.0.1, so this is the one URL that works without a TLS tunnel;
5. registers the webhooks (`sms:received`, `sms:sent`, `sms:delivered`,
   `sms:failed`) with fixed ids, so re-running replaces rather than duplicates.

Forwards vanish whenever the phone reconnects; `--watch` re-applies them.
Needs SMSGATE_USER / SMSGATE_PASSWORD (shown in the app under Local Server) in
.env.local. The password is never printed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import httpx

from .adb import find_adb

PACKAGE = "me.capcom.smsgateway"
PHONE_PORT = 8080
EVENTS = ("sms:received", "sms:sent", "sms:delivered", "sms:failed")
WEBHOOK_PATH = "/api/channels/sms/smsgate"


def webhook_registrations(backend_port: int) -> list[dict]:
    """The webhook bodies to POST to the phone's /webhooks, one per event."""
    url = f"http://127.0.0.1:{backend_port}{WEBHOOK_PATH}"
    return [{"id": f"agro-{event.split(':', 1)[1]}", "url": url, "event": event} for event in EVENTS]


class Phone:
    def __init__(self, adb: str, serial: str | None = None):
        self.base = [adb] + (["-s", serial] if serial else [])

    def run(self, *args: str, timeout: float = 15) -> subprocess.CompletedProcess:
        return subprocess.run(self.base + list(args), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)

    def online(self) -> bool:
        try:
            return self.run("get-state", timeout=5).stdout.strip() == "device"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def has_app(self) -> bool:
        return f"package:{PACKAGE}" in self.run("shell", "pm", "list", "packages", PACKAGE).stdout

    def keep_alive(self) -> None:
        self.run("shell", "dumpsys", "deviceidle", "whitelist", f"+{PACKAGE}")
        self.run("shell", "cmd", "appops", "set", PACKAGE, "RUN_ANY_IN_BACKGROUND", "allow")

    def tunnels(self, backend_port: int) -> bool:
        fwd = self.run("forward", f"tcp:{PHONE_PORT}", f"tcp:{PHONE_PORT}")
        rev = self.run("reverse", f"tcp:{backend_port}", f"tcp:{backend_port}")
        return fwd.returncode == 0 and rev.returncode == 0


def _ok(label: str, good: bool, fix: str = "") -> bool:
    print(f"  [{'ok' if good else '!!'}] {label}" + ("" if good or not fix else f"\n       -> {fix}"))
    return good


def setup(phone: Phone, backend_port: int, auth: tuple[str, str] | None) -> bool:
    print("SMS gateway over USB")
    if not _ok("phone connected on ADB", phone.online(),
               "plug in USB, enable USB debugging, accept the prompt; `adb devices` must say 'device'"):
        return False
    if not _ok("SMS Gateway app installed", phone.has_app(),
               "install from github.com/capcom6/android-sms-gateway/releases (package me.capcom.smsgateway)"):
        return False
    phone.keep_alive()
    _ok("battery optimisation off for the app", True)
    if not _ok("tunnels: laptop:8080 -> phone, phone:%d -> laptop" % backend_port, phone.tunnels(backend_port)):
        return False
    phone_api = f"http://127.0.0.1:{PHONE_PORT}"
    try:
        healthy = httpx.get(f"{phone_api}/health", timeout=5).status_code < 500
    except httpx.HTTPError:
        healthy = False
    if not _ok("app's Local Server answering", healthy,
               "open the app, turn on Local Server, tap Offline so it shows Online"):
        return False
    try:
        backend_up = httpx.get(f"http://127.0.0.1:{backend_port}/api/health", timeout=5).status_code == 200
    except httpx.HTTPError:
        backend_up = False
    _ok("backend running on this laptop", backend_up,
        f"start it: .venv/Scripts/python -m uvicorn backend.api.main:app --port {backend_port}")
    if not auth:
        return _ok("SMSGATE_USER / SMSGATE_PASSWORD set", False,
                   "copy them from the app's Local Server card into .env.local")
    registered = 0
    for body in webhook_registrations(backend_port):
        try:
            r = httpx.post(f"{phone_api}/webhooks", json=body, auth=auth, timeout=10)
            registered += r.status_code < 300
            if r.status_code == 401:
                break
        except httpx.HTTPError:
            pass
    if not _ok(f"webhooks registered ({registered}/{len(EVENTS)})", registered == len(EVENTS),
               "401 = wrong SMSGATE_USER/PASSWORD; they change when the app's server is reset"):
        return False
    if not os.environ.get("SMSGATE_SIGNING_KEY"):
        print("  [..] SMSGATE_SIGNING_KEY not set: webhooks are accepted unsigned. "
              "Copy it from the app (Settings -> Webhooks -> Signing Key) to verify them.")
    if os.environ.get("SMS_PROVIDER", "simulator") != "smsgate":
        print("  [..] SMS_PROVIDER is not 'smsgate': replies still go to the simulator. "
              "Set SMS_PROVIDER=smsgate in .env.local and restart the backend.")
    print("ready: text the phone's number from another phone to talk to the agent.")
    return True


def main(argv: list[str] | None = None) -> int:
    from backend.env import load
    load()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adb", default=find_adb())
    ap.add_argument("--serial", default=os.environ.get("ANDROID_SERIAL"))
    ap.add_argument("--backend-port", type=int, default=int(os.environ.get("BACKEND_PORT", "8000")))
    ap.add_argument("--watch", action="store_true", help="re-apply tunnels whenever the phone reconnects")
    args = ap.parse_args(argv)
    user, password = os.environ.get("SMSGATE_USER", ""), os.environ.get("SMSGATE_PASSWORD", "")
    auth = (user, password) if user and password else None
    phone = Phone(args.adb, args.serial)
    ready = setup(phone, args.backend_port, auth)
    if not args.watch:
        return 0 if ready else 1
    print("watching for reconnects (Ctrl+C to stop)")
    was_online = phone.online()
    try:
        while True:
            time.sleep(3)
            online = phone.online()
            if online and not was_online:
                print("phone reconnected; re-applying")
                setup(phone, args.backend_port, auth)
            elif was_online and not online:
                print("phone disconnected", file=sys.stderr)
            was_online = online
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
