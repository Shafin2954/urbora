"""One spoken turn, and the hang-up that sends the SMS summary.

Transport-agnostic: the browser emulator posts a recorded clip; the modem
driver will post the VAD-segmented utterance from a real call. Both get back
the transcript, the reply text and the reply audio.

A call is one agent conversation (`session_stamp=call_id`), so follow-up
questions keep their context; the farm profile and plan are shared with every
other channel through the phone's farm id. Plan/finance produced during the
call are kept per call and texted at hang-up — the farmer should not have to
memorise figures they heard once.
"""

from __future__ import annotations

import asyncio
import base64
import logging

from backend.memory import store

from ..adapter import ChannelReply, Menu, run_channel_turn
from ..identity import farm_id_for, normalise
from . import speech

log = logging.getLogger("channels.voice")

NOT_HEARD = "দুঃখিত, আমি শুনতে পাইনি। আবার বলুন।"


def spoken_menu(menu: Menu) -> str:
    """A menu for the ear: 'দোআঁশ হলে 1 বলুন, এঁটেল হলে 2 বলুন।' The farmer
    may say the digit or the word; Menu.resolve accepts both."""
    if not menu.options:
        return menu.prompt
    choices = ", ".join(f"{label} হলে {i} বলুন" for i, (_, label) in enumerate(menu.options, 1))
    return f"{menu.prompt} {choices}।"


def spoken_text(reply: ChannelReply) -> str:
    parts = [reply.text.strip()] + ([spoken_menu(reply.menu)] if reply.menu else [])
    return " ".join(p for p in parts if p) or NOT_HEARD


def _call_key(call_id: str) -> str:
    return f"call-{call_id}"


def _remember(call_id: str, reply: ChannelReply) -> None:
    state = store.get_ussd_state(_call_key(call_id)) or {}
    if reply.plan:
        state["plan"] = reply.plan
    if reply.finance:
        state["finance"], state["finance_crop"] = reply.finance, reply.finance_crop
    state["farm_id"], state["session_id"] = reply.farm_id, reply.session_id
    store.save_ussd_state(_call_key(call_id), reply.farm_id, state)


async def voice_turn(msisdn: str, call_id: str, audio: bytes, content_type: str,
                     *, speak: bool = True) -> dict:
    local = normalise(msisdn)
    try:
        transcript, stt_used = await asyncio.to_thread(speech.transcribe, audio, content_type)
    except speech.SpeechError as exc:
        log.warning("STT failed: %s", exc)
        transcript, stt_used = "", speech.stt_provider()

    if transcript:
        reply = await run_channel_turn(local, transcript, "voice", session_stamp=call_id)
        _remember(call_id, reply)
        text = spoken_text(reply)
        menu = reply.menu.to_dict() if reply.menu else None
    else:
        text, menu = NOT_HEARD, None

    out = {"transcript": transcript, "reply_text": text, "menu": menu, "stt": stt_used,
           "audio_b64": None, "audio_type": None, "tts": None}
    if speak:
        try:
            audio_out, tts_used = await asyncio.to_thread(speech.synthesize, text)
            out.update(audio_b64=base64.b64encode(audio_out.data).decode("ascii"),
                       audio_type=audio_out.content_type, tts=tts_used)
        except speech.SpeechError as exc:
            # The text still reaches the screen; say why there is no audio.
            out["tts_error"] = str(exc)
    return out


def hang_up(msisdn: str, call_id: str) -> dict:
    """Text the farmer what the call produced, then forget the call state."""
    from backend.branding import BRAND_NAME

    from .. import sms, sms_text
    from ..adapter import cost_is_complete

    farm_id = farm_id_for(normalise(msisdn))
    state = store.get_ussd_state(_call_key(call_id)) or {}
    crop = (state.get("plan") or {}).get("crop") or state.get("finance_crop")
    body = sms_text.plan_summary_sms(BRAND_NAME, state.get("plan"), state.get("finance"), crop,
                                     cost_complete=cost_is_complete(crop), max_parts=sms.max_parts())
    if body is None:
        turns = store.get_channel_turns(state["session_id"]) if state.get("session_id") else []
        if turns:
            body = f"{BRAND_NAME}: কলের শেষ পরামর্শ\n{turns[-1]['reply_text']}"
    result = sms.send_sms(farm_id, body) if body else None
    store.save_ussd_state(_call_key(call_id), farm_id, {})
    return {"summary_sent": bool(result and result.status != "failed"), "body": body}
