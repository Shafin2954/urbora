"""SMS providers and the one function that sends an SMS to a farm.

Three providers behind one interface, chosen by `SMS_PROVIDER`:

- `smsgate`   — a real Android phone running SMS Gateway for Android™
                (capcom6/android-sms-gateway, Apache-2.0) in Local Server mode:
                `POST http://<phone-ip>:8080/message`, Basic auth, body
                `{"textMessage":{"text":…},"phoneNumbers":[…]}`. Real SMS over
                the phone's SIM. Inbound SMS arrive as signed `sms:received`
                webhooks (see `verify_smsgate_signature`).
- `bdapps`    — bdapps `/sms/send` (encoding 16 = Bengali), through the same
                client and simulator twin checkout already uses.
- `simulator` — the default. Nothing leaves the machine; the message lands in
                `sms_log`, which the browser phone emulator reads as its inbox.
                Labelled `simulator` everywhere (CLAUDE.md rules 13 and 15).

Every outbound message is trimmed to `SMS_MAX_PARTS` segments (sms_text.fit),
logged with its segment count, and addressed by farm_id: callers never handle
a phone number, only the contacts table does.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.memory import store

from . import sms_text
from .identity import normalise


@dataclass
class SendResult:
    provider: str
    status: str                 # "sent" | "queued" | "failed"
    provider_ref: str | None = None
    detail: str | None = None


class SmsProvider(Protocol):
    name: str
    mode: str                   # "live" | "simulator"

    def send(self, local_msisdn: str, text: str) -> SendResult: ...


class SimulatorProvider:
    name = "simulator"
    mode = "simulator"

    def send(self, local_msisdn: str, text: str) -> SendResult:
        return SendResult(self.name, "sent")


class SmsGateProvider:
    """Android phone in Local Server mode (default port 8080, Basic auth)."""

    name = "smsgate"
    mode = "live"

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 15.0):
        if not (base_url and username and password):
            raise ValueError("SMSGate needs SMSGATE_URL, SMSGATE_USER and SMSGATE_PASSWORD.")
        self._url = base_url.rstrip("/")
        self._auth = (username, password)
        self._timeout = timeout

    def send(self, local_msisdn: str, text: str) -> SendResult:
        body = {"textMessage": {"text": text}, "phoneNumbers": [f"+88{local_msisdn}"]}
        try:
            r = httpx.post(f"{self._url}/message", json=body, auth=self._auth, timeout=self._timeout)
        except httpx.HTTPError as exc:
            return SendResult(self.name, "failed", detail=f"phone unreachable: {type(exc).__name__}")
        if r.status_code >= 300:
            return SendResult(self.name, "failed", detail=f"HTTP {r.status_code}: {r.text[:200]}")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return SendResult(self.name, "queued", provider_ref=data.get("id"), detail=data.get("state"))


class BdappsSmsProvider:
    name = "bdapps"

    def __init__(self) -> None:
        from backend.payments.service import build_client
        self._client = build_client()
        self.mode = self._client.mode

    def send(self, local_msisdn: str, text: str) -> SendResult:
        try:
            resp = self._client.sms_send(f"tel:88{local_msisdn}", text, encoding="16")
        except Exception as exc:  # noqa: BLE001
            return SendResult(self.name, "failed", detail=f"{type(exc).__name__}: {exc}")
        ok = resp.get("statusCode") == "S1000"
        return SendResult(self.name, "sent" if ok else "failed", provider_ref=resp.get("requestId"),
                          detail=resp.get("statusDetail"))


def build_provider(name: str | None = None) -> SmsProvider:
    name = (name or os.environ.get("SMS_PROVIDER", "simulator")).strip().lower()
    if name == "smsgate":
        return SmsGateProvider(os.environ.get("SMSGATE_URL", ""), os.environ.get("SMSGATE_USER", ""),
                               os.environ.get("SMSGATE_PASSWORD", ""))
    if name == "bdapps":
        return BdappsSmsProvider()
    return SimulatorProvider()


_provider: SmsProvider | None = None


def provider() -> SmsProvider:
    global _provider
    if _provider is None:
        _provider = build_provider()
    return _provider


def set_provider(p: SmsProvider | None) -> None:
    """Tests and the /api/channels config swap the provider here."""
    global _provider
    _provider = p


def max_parts() -> int:
    try:
        return max(1, int(os.environ.get("SMS_MAX_PARTS", "3")))
    except ValueError:
        return 3


def send_sms(farm_id: str, text: str, *, p: SmsProvider | None = None) -> SendResult:
    """Send `text` to the farm's registered number. Trims, sends, logs."""
    contact = store.get_contact(farm_id)
    if not contact:
        return SendResult("none", "failed", detail="no contact for this farm")
    body = sms_text.fit(text, max_parts())
    if not body:
        return SendResult("none", "failed", detail="empty message")
    prov = p or provider()
    result = prov.send(normalise(contact["msisdn"]), body)
    store.log_sms(farm_id, "out", body, sms_text.segments(body), result.provider,
                  result.status, result.provider_ref)
    return result


def record_inbound(farm_id: str, text: str, provider_name: str, ref: str | None = None) -> None:
    store.log_sms(farm_id, "in", text, sms_text.segments(text), provider_name, "received", ref)


def verify_smsgate_signature(raw_body: bytes, timestamp: str, signature: str, key: str) -> bool:
    """SMSGate signs webhooks: hex HMAC-SHA256(key, raw_body + timestamp)."""
    if not (timestamp and signature and key):
        return False
    expected = hmac.new(key.encode(), raw_body + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())
