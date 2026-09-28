"""Phone-channel routes: SMS webhooks, the browser phone emulator, the monitor.

- `POST /api/channels/sms/smsgate`   — webhook from the Android SMS gateway
  (SMSGate). Verified by HMAC when SMSGATE_SIGNING_KEY is set. Answers 200 at
  once; the agent turn and the reply SMS run in the background, because an SMS
  gateway retries a slow webhook and a farmer would get two answers.
- `POST /api/channels/sms/bdapps`    — bdapps MO SMS (reference §4.2 shape).
- `POST /api/channels/emulator/sms`  — the browser phone emulator sends an SMS.
- `GET  /api/channels/emulator/inbox` — the emulator's inbox. Emulator routes
  exist only while the emulator is enabled (default: when SMS_PROVIDER is the
  simulator), because reading an inbox by phone number must never be possible
  against real farmers' messages.
- `GET  /api/channels/status`        — which providers are live vs simulated.
- `GET  /api/channels/sessions[/{id}]` — recent phone conversations and their
  redacted traces, for the live-channels monitor. Masked numbers only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend.channels import flows, sms
from backend.channels.identity import InvalidMsisdnError, farm_id_for, mask, normalise
from backend.memory import store

router = APIRouter(prefix="/api/channels", tags=["channels"])
log = logging.getLogger("channels")


def emulator_enabled() -> bool:
    flag = os.environ.get("CHANNEL_EMULATOR_ENABLED", "").strip().lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    return sms.provider().mode == "simulator"


def _require_emulator() -> None:
    if not emulator_enabled():
        raise HTTPException(404, "emulator disabled")


async def _answer_sms(msisdn: str, text: str, provider_name: str, ref: str | None) -> None:
    try:
        await flows.handle_inbound_sms(msisdn, text, provider_name, ref)
    except Exception:  # noqa: BLE001 — a background failure must be logged, not lost
        log.exception("inbound SMS handling failed")


@router.get("/status")
async def status() -> dict:
    p = sms.provider()
    return {
        "sms": {"provider": p.name, "mode": p.mode},
        "ussd": {"mode": "simulator"},
        "emulator_enabled": emulator_enabled(),
    }


SIGNATURE_WINDOW_S = 300      # SMSGate docs: reject timestamps more than ±5 min off
STALE_SMS_S = 15 * 60         # a retried SMS older than this gets no answer


def _received_age_s(received_at: str | None) -> float | None:
    if not received_at:
        return None
    try:
        when = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        return None
    return (datetime.now(timezone.utc) - when).total_seconds()


@router.post("/sms/smsgate")
async def smsgate_webhook(request: Request, background: BackgroundTasks) -> dict:
    """SMSGate webhook (docs.sms-gate.app/features/webhooks). It retries a failed
    delivery for ~2 days, so every event id is handled once and a stale SMS is
    recorded but not answered (a reply two days late is worse than none)."""
    raw = await request.body()
    key = os.environ.get("SMSGATE_SIGNING_KEY", "")
    if key:
        ts = request.headers.get("X-Timestamp", "")
        if not sms.verify_smsgate_signature(raw, ts, request.headers.get("X-Signature", ""), key):
            raise HTTPException(401, "bad signature")
        if not ts.isdigit() or abs(time.time() - int(ts)) > SIGNATURE_WINDOW_S:
            raise HTTPException(401, "stale signature")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "not JSON")
    event = body.get("event")
    payload = body.get("payload") or {}
    if body.get("id") and not store.mark_webhook_seen(f"smsgate:{body['id']}"):
        return {"ok": True, "duplicate": True}
    if event == "sms:received":
        sender, text = payload.get("sender") or payload.get("phoneNumber"), payload.get("message", "")
        if not sender:
            return {"ok": True}
        age = _received_age_s(payload.get("receivedAt"))
        if age is not None and age > STALE_SMS_S:
            log.warning("SMS from %s is %.0f min old (webhook retry); recorded, not answered",
                        mask(sender), age / 60)
            try:
                sms.record_inbound(farm_id_for(sender), text, "smsgate", payload.get("messageId"))
            except InvalidMsisdnError:
                pass
            return {"ok": True, "stale": True}
        background.add_task(_answer_sms, sender, text, "smsgate", payload.get("messageId"))
    elif event in ("sms:sent", "sms:delivered", "sms:failed", "sms:cancelled"):
        ref = payload.get("messageId") or body.get("id")
        if ref:
            store.update_sms_status(ref, event.split(":", 1)[1])
    return {"ok": True}


@router.post("/sms/bdapps")
async def bdapps_mo(request: Request, background: BackgroundTasks) -> dict:
    body = await request.json()
    address = str(body.get("sourceAddress", "")).removeprefix("tel:")
    background.add_task(_answer_sms, address, body.get("message", ""), "bdapps", body.get("requestId"))
    return {"statusCode": "S1000", "statusDetail": "Success"}


class EmulatorSms(BaseModel):
    msisdn: str
    text: str


@router.post("/emulator/sms")
async def emulator_sms(payload: EmulatorSms) -> dict:
    _require_emulator()
    try:
        normalise(payload.msisdn)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))
    # Not a BackgroundTask: the emulator polls its inbox, and a task tied to
    # the request would be cancelled if the browser navigates away.
    asyncio.create_task(_answer_sms(payload.msisdn, payload.text, "emulator", None))
    return {"accepted": True}


class EmulatorMissedCall(BaseModel):
    msisdn: str


@router.post("/emulator/missed-call")
async def emulator_missed_call(payload: EmulatorMissedCall) -> dict:
    _require_emulator()
    result = flows.handle_missed_call(payload.msisdn)
    if result is None:
        raise HTTPException(422, "not a Bangladeshi mobile number")
    return {"status": result.status}


@router.get("/emulator/inbox")
async def emulator_inbox(msisdn: str) -> dict:
    _require_emulator()
    try:
        farm_id = farm_id_for(msisdn)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))
    return {"mode": "simulator", "messages": list(reversed(store.list_sms(farm_id)))}


@router.get("/sessions")
async def sessions(limit: int = 30) -> dict:
    return {"sessions": store.list_channel_sessions(min(max(limit, 1), 100))}


@router.get("/sessions/{session_id}")
async def session_detail(session_id: str) -> dict:
    turns = store.get_channel_turns(session_id)
    if not turns:
        raise HTTPException(404, "no such session")
    return {"session_id": session_id, "turns": turns}


# --- laptop-side bridge + alert scan ------------------------------------------


def _require_bridge_token(request: Request) -> None:
    """The ADB bridge runs on the laptop the phone is plugged into and may call
    a backend elsewhere (e.g. the hosted demo), so it authenticates."""
    token = os.environ.get("BRIDGE_TOKEN", "")
    if not token or request.headers.get("X-Bridge-Token", "") != token:
        raise HTTPException(401, "bridge token required")


class MissedCall(BaseModel):
    msisdn: str


@router.post("/bridge/missed-call")
async def bridge_missed_call(payload: MissedCall, request: Request) -> dict:
    _require_bridge_token(request)
    result = flows.handle_missed_call(payload.msisdn)
    if result is None:
        raise HTTPException(422, "not a Bangladeshi mobile number")
    return {"status": result.status}


@router.post("/alerts/scan")
async def alerts_scan(request: Request) -> dict:
    """Run one proactive-alert pass now (demo / cron). Emulator mode or token."""
    if not emulator_enabled():
        _require_bridge_token(request)
    from backend.channels import alerts_job
    return await asyncio.to_thread(alerts_job.scan_once)


# --- USSD ----------------------------------------------------------------------


class EmulatorUssd(BaseModel):
    session_id: str
    msisdn: str
    text: str | None = None
    init: bool = False


@router.post("/emulator/ussd")
async def emulator_ussd(payload: EmulatorUssd) -> dict:
    """The browser phone dials *code# (init) and answers menus."""
    _require_emulator()
    from backend.channels.ussd import ussd_request
    try:
        screen = await ussd_request(payload.session_id, payload.msisdn, payload.text, payload.init)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))
    return {"mode": "simulator", "text": screen.text, "end": screen.end}


def _bdapps_ussd_send(session_id: str, address: str, message: str, end: bool) -> dict:
    """bdapps MT reply (reference §5.1). Live only when BDAPPS_MODE=live; in
    simulator mode the exact body is returned for inspection, not sent."""
    body = {
        "applicationId": os.environ.get("BDAPPS_APP_ID", ""),
        "password": os.environ.get("BDAPPS_PASSWORD", ""),
        "message": message,
        "sessionId": session_id,
        "ussdOperation": "mt-fin" if end else "mt-cont",
        "destinationAddress": address,
        "encoding": "16",
        "version": "1.0",
    }
    if os.environ.get("BDAPPS_MODE", "simulator").strip().lower() != "live":
        return {"mode": "simulator", "would_send": {**body, "password": "***"}}
    import httpx
    base = os.environ.get("BDAPPS_BASE_URL", "https://developer.bdapps.com").rstrip("/")
    r = httpx.post(f"{base}/ussd/send", json=body, timeout=10)
    return {"mode": "live", "status": r.status_code}


@router.post("/ussd/bdapps")
async def bdapps_ussd(request: Request) -> dict:
    """bdapps USSD MO: `mo-init` when the farmer dials, `mo-cont` per reply."""
    from backend.channels.ussd import ussd_request
    body = await request.json()
    address = str(body.get("sourceAddress", ""))
    session_id = str(body.get("sessionId", ""))
    is_init = body.get("ussdOperation") == "mo-init"
    try:
        screen = await ussd_request(session_id, address.removeprefix("tel:"), body.get("message"), is_init)
    except InvalidMsisdnError:
        return {"statusCode": "E1325", "statusDetail": "unusable address"}
    sent = await asyncio.to_thread(_bdapps_ussd_send, session_id, address, screen.text, screen.end)
    return {"statusCode": "S1000", "statusDetail": "Success", "reply": sent}


# --- voice ---------------------------------------------------------------------


_MAX_CLIP_BYTES = 10 * 1024 * 1024


@router.get("/voice/status")
async def voice_status() -> dict:
    from backend.channels.voice import speech
    return speech.status()


@router.post("/emulator/voice/turn")
async def emulator_voice_turn(
    msisdn: str = Form(...), call_id: str = Form(...), file: UploadFile = File(...),
) -> dict:
    """One push-to-talk turn from the browser phone's call screen."""
    _require_emulator()
    from backend.channels.voice.turn import voice_turn
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "empty recording")
    if len(audio) > _MAX_CLIP_BYTES:
        raise HTTPException(413, "recording too long")
    try:
        return await voice_turn(msisdn, call_id, audio, file.content_type or "audio/webm")
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))


class HangUp(BaseModel):
    msisdn: str
    call_id: str


@router.post("/emulator/voice/hangup")
async def emulator_voice_hangup(payload: HangUp) -> dict:
    _require_emulator()
    from backend.channels.voice.turn import hang_up
    try:
        return await asyncio.to_thread(hang_up, payload.msisdn, payload.call_id)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))


# --- Phone Link voice bridge (backend/channels/voice/phonelink.py) --------------


@router.post("/bridge/voice/turn")
async def bridge_voice_turn(request: Request, msisdn: str = Form(...), call_id: str = Form(...),
                            file: UploadFile = File(...)) -> dict:
    """One utterance from a real phone call bridged through Windows Phone Link.
    Reply audio is plain WAV so the bridge can play it with no decoder."""
    _require_bridge_token(request)
    from backend.channels.voice.turn import voice_turn
    audio = await file.read()
    if not audio or len(audio) > _MAX_CLIP_BYTES:
        raise HTTPException(400, "empty or oversized utterance")
    try:
        return await voice_turn(msisdn, call_id, audio, file.content_type or "audio/wav", wav=True)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))


@router.post("/bridge/voice/hangup")
async def bridge_voice_hangup(payload: HangUp, request: Request) -> dict:
    _require_bridge_token(request)
    from backend.channels.voice.turn import hang_up
    try:
        return await asyncio.to_thread(hang_up, payload.msisdn, payload.call_id)
    except InvalidMsisdnError as exc:
        raise HTTPException(422, str(exc))


class Say(BaseModel):
    text: str


@router.post("/bridge/voice/say")
async def bridge_voice_say(payload: Say, request: Request) -> dict:
    """Fixed lines the bridge speaks (greeting, 'একটু অপেক্ষা করুন'), as WAV."""
    _require_bridge_token(request)
    import base64
    from backend.channels.voice import speech
    try:
        audio, used = await asyncio.to_thread(speech.synthesize, payload.text[:500], None, True)
    except speech.SpeechError as exc:
        raise HTTPException(502, str(exc))
    return {"audio_b64": base64.b64encode(audio.data).decode("ascii"), "audio_type": audio.content_type,
            "tts": used}
