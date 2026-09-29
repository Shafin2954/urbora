"""Keypad menu on the hotline — the USSD menu, spoken.

During a call the farmer may speak (→ the agent, voice/turn.py) or press keys.
Keys drive `backend/channels/ussd.py::step` unchanged — the same menus as
`*code#` and SMS menu mode — and each screen is turned into speech:
"1. ফসল পরামর্শ" is read as "ফসল পরামর্শের জন্য 1 চাপুন".

Number entry (বিঘা, টাকা, কেজি) ends with # or a pause; the bridge buffers the
digits and sends them together. * repeats the current screen.

A crop-problem report is answered on the call as well as by SMS: the answer is
a deterministic template (backend/kb/triage.py), so it is ready instantly, and a
farmer who cannot read the SMS still hears it. Agent work (advice, questions)
runs in the background and arrives by SMS, as from USSD.
"""

from __future__ import annotations

import asyncio
import re

from backend.memory import store

from .. import ussd
from ..identity import farm_id_for, mask, normalise

_OPTION = re.compile(r"^(\d)\.\s*(.+)$")
SPEAK_MORE = "আরও শুনতে 9 চাপুন।"
SPEAK_BACK = "পিছনে যেতে 0 চাপুন।"
NUMBER_HINT = "সংখ্যা চেপে শেষে # চাপুন।"
REPEAT_HINT = "আবার শুনতে * চাপুন।"


def speakable(screen_text: str) -> str:
    """A USSD screen for the ear. Options become 'label, N চাপুন'."""
    parts = []
    for line in screen_text.splitlines():
        m = _OPTION.match(line.strip())
        if not m:
            if line.strip() == "সংখ্যা লিখুন":
                parts.append(NUMBER_HINT)
            elif line.strip():
                parts.append(line.strip().rstrip("।:?") + ("?" if line.strip().endswith("?") else "।"))
            continue
        key, label = m.groups()
        if key == "9" and label == "আরও":
            parts.append(SPEAK_MORE)
        elif key == "0" and label in ("পিছনে", "মেনু"):
            parts.append(SPEAK_BACK)
        else:
            parts.append(f"{label}, {key} চাপুন।")
    return " ".join(parts)


def expects_number(state: dict) -> bool:
    """Screens where the farmer types a number rather than picking an option."""
    return state.get("at") in ("area", "budget") or state.get("step") in ("qty", "price", "packs")


def _key(call_id: str) -> str:
    return f"ivr-{call_id}"


async def keys(msisdn: str, call_id: str, pressed: str) -> dict:
    """One keypad input (a single key, or digits ended by #). Returns the text to
    speak, whether the menu ended, and whether the next screen wants a number."""
    local = normalise(msisdn)
    farm_id = farm_id_for(local)
    store.upsert_contact(farm_id, local, mask(local), "voice")
    state = store.get_ussd_state(_key(call_id))
    if state and state.get("at") == "done":
        state = None
    ctx = ussd.build_context(farm_id)
    entry = pressed.rstrip("#")

    if state is None:
        # The first key opens the menu; if it is a menu choice, apply it at once.
        screen, state, action = ussd.step(None, None, ctx)
        if entry and entry not in ("*", "0"):
            screen, state, action = ussd.step(state, entry, ctx)
    elif entry == "*":
        screen, action = ussd.Screen(state.get("_screen") or ussd.main_menu(ctx).text), None
    else:
        screen, state, action = ussd.step(state, entry, ctx)

    spoken = speakable(screen.text)
    answer = None
    if action and action.get("kind") == "problem":
        from backend.kb import triage
        req = action["request"]
        diag = triage.diagnose(req["crop"], req["stage"], req["organ"], req["symptom"], req["extent"],
                               req.get("weather") or "none", req.get("days_exact"))
        profile = store.get_farm(farm_id) or {}
        area = profile.get("area") if isinstance(profile.get("area"), (int, float)) else None
        answer = triage.answer_sms(diag, area)
        spoken = f"{answer} এই পরামর্শ SMS-এও পাঠানো হলো।"
    if action:
        task = asyncio.create_task(ussd.run_action(local, farm_id, action))
        ussd._background.add(task)
        task.add_done_callback(ussd._background.discard)
    # The last screen is kept with the state so * can repeat it on any menu.
    store.save_ussd_state(_key(call_id), farm_id, {"at": "done"} if screen.end else {**state, "_screen": screen.text})
    if not screen.end:
        spoken = f"{spoken} {REPEAT_HINT}"
    return {"text": spoken, "screen": screen.text, "end": screen.end,
            "expects_number": (not screen.end) and expects_number(state), "answer": answer}
