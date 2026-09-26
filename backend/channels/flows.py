"""What happens when a farmer texts, gives a missed call, or finishes a call.

Kept separate from the HTTP routes so the same flow runs from a webhook, the
browser phone emulator, the ADB missed-call bridge, or a test.
"""

from __future__ import annotations

import logging

from backend.branding import BRAND_NAME

from . import sms, sms_text
from .adapter import ChannelReply, cost_is_complete, run_channel_turn
from .identity import farm_id_for, mask, normalise

log = logging.getLogger("channels")

WELCOME_SMS = (
    f"{BRAND_NAME}: কৃষি পরামর্শ\n"
    "প্রশ্ন লিখে SMS করুন, যেমন: রাজশাহীতে 2 বিঘা, রবি মৌসুমে কী চাষ করব?\n"
    "অথবা কল করুন।"
)


def send_summary(reply: ChannelReply) -> sms.SendResult | None:
    """If the turn produced a plan or a finance projection, text the farmer a
    template summary (numbers from tool payloads only)."""
    crop = (reply.plan or {}).get("crop") or reply.finance_crop
    body = sms_text.plan_summary_sms(
        BRAND_NAME, reply.plan, reply.finance, crop,
        cost_complete=cost_is_complete(crop), max_parts=sms.max_parts(),
    )
    return sms.send_sms(reply.farm_id, body) if body else None


async def handle_inbound_sms(msisdn: str, text: str, provider_name: str,
                             ref: str | None = None) -> ChannelReply | None:
    """An SMS arrived from a farmer: answer it by SMS."""
    try:
        local = normalise(msisdn)
    except ValueError:
        log.warning("inbound SMS from an unusable address; ignored")
        return None
    farm_id = farm_id_for(local)
    text = (text or "").strip()

    # Marketplace keywords are handled before the agent sees the message.
    from backend.market import sms_commands
    reply_text = sms_commands.try_handle(local, text)
    if reply_text is not None:
        from backend.memory import store
        store.upsert_contact(farm_id, local, mask(local), "sms")
        sms.record_inbound(farm_id, text, provider_name, ref)
        sms.send_sms(farm_id, reply_text)
        return None

    reply = await run_channel_turn(local, text, "sms")
    sms.record_inbound(farm_id, text, provider_name, ref)
    sms.send_sms(farm_id, reply.display_text())
    send_summary(reply)
    return reply


def handle_missed_call(msisdn: str) -> sms.SendResult | None:
    """A missed call is free for the farmer: answer it with the welcome SMS."""
    from backend.memory import store
    try:
        local = normalise(msisdn)
    except ValueError:
        return None
    farm_id = farm_id_for(local)
    store.upsert_contact(farm_id, local, mask(local), "missed_call")
    return sms.send_sms(farm_id, WELCOME_SMS)
