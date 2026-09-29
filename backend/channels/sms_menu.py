"""SMS menu mode — the USSD menu, over plain SMS.

A real USSD short code needs operator provisioning; plain SMS works on every
phone today through the Android gateway. So the farmer texts "মেনু" (or
"menu") and gets the same numbered menu as `*code#`, replies with a digit, and
walks the same screens: advice intake, crop problem, plan, weather, buying,
selling. It is `backend/channels/ussd.py::step` unchanged — same state
machine, same actions, same answers by SMS — only the transport differs.

While a menu walk is open (last reply < 15 min, not finished), digit replies go
to the menu; any other text leaves the menu and goes to the agent as a normal
question. An unfinished USSD walk from the last 30 min is offered back here
too, so a farmer whose USSD session timed out can finish by SMS.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from backend.memory import store

from . import sms, ussd

TRIGGERS = {"মেনু", "মেন্যু", "menu", "m", "ম"}
IDLE_LIMIT = timedelta(minutes=15)
INSTANT_ACTIONS = ("problem", "sms")   # answered by template at once
FIRST_HINT = "উত্তরে শুধু নম্বর লিখে পাঠান।"
_REPLY = re.compile(r"^[\d০-৯]{1,7}$|^\*$")


def _key(farm_id: str) -> str:
    return f"smsmenu-{farm_id}"


def _open_state(farm_id: str) -> dict | None:
    found = store.get_ussd_state_at(_key(farm_id))
    if not found:
        return None
    state, updated_at = found
    if state.get("at") == "done":
        return None
    try:
        when = datetime.fromisoformat(updated_at)
    except ValueError:
        return None
    return state if datetime.now(timezone.utc) - when <= IDLE_LIMIT else None


def is_open(farm_id: str) -> bool:
    return _open_state(farm_id) is not None


def is_trigger(text: str) -> bool:
    return text.strip().lower() in TRIGGERS


async def try_handle(local_msisdn: str, farm_id: str, text: str) -> bool:
    """Handle `text` as a menu step if it starts or continues a menu walk.
    False = not a menu message; the caller sends it to the agent."""
    text = (text or "").strip()
    state = _open_state(farm_id)
    starting = is_trigger(text)
    if not starting:
        if state is None:
            return False
        # Free text only where the menu asks for it (the question screen);
        # anything else leaves the menu and goes to the agent.
        if state.get("at") != "ask" and not _REPLY.match(text):
            store.save_ussd_state(_key(farm_id), farm_id, {"at": "done"})
            return False

    resume = ussd._find_resume(farm_id, _key(farm_id)) if starting else None
    ctx = ussd.build_context(farm_id, resume)
    screen, new_state, action = ussd.step(None if starting else state, None if starting else text, ctx)
    store.save_ussd_state(_key(farm_id), farm_id, {"at": "done"} if screen.end else new_state)
    if resume is not None and new_state.get("at") == "resume":
        store.close_other_ussd_states(farm_id, keep=_key(farm_id))
    body = f"{screen.text}\n{FIRST_HINT}" if starting else screen.text
    # "উত্তর কয়েক মিনিটে SMS-এ আসবে" is noise when the answer is a template sent
    # this same second (crop problem, alert); keep it for agent answers, which take a while.
    if not (screen.end and action and action.get("kind") in INSTANT_ACTIONS):
        sms.send_sms(farm_id, body)
    if action:
        await ussd.run_action(local_msisdn, farm_id, action)
    return True
