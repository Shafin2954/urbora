"""USSD main menu 2 — "ফসলের সমস্যা": report a crop problem by keypad.

crop → stage → where → what it looks like → how much of the field
[→ last week's weather, only when a rule depends on it]. A farmer with a saved
plan is offered a shortcut: "আলু, বপনের 34 দিন? 1. হ্যাঁ" skips crop and stage
and uses the exact day count.

The diagnosis is `backend/kb/triage.py` — a deterministic, KB-bounded table —
and the answer SMS is built from it by template, so it goes out in the
background within seconds and costs no LLM call. A follow-up SMS question then
reaches the agent with the triage attached as context (adapter.py).

Same handler contract as the marketplace menus; every screen goes through the
shared pager (≤80 units, 9 = more, 0 = back).
"""

from __future__ import annotations

import uuid
from datetime import date

from backend.kb import triage

from .ussd import BAD, Screen, main_menu, paged, pick_paged, with_note

TITLES = {"crop": "কোন ফসল?", "stage": "গাছের অবস্থা?", "organ": "কোথায় সমস্যা?",
          "symptom": "কেমন দেখায়?", "extent": "কত জমিতে?", "weather": "গত সপ্তাহে?"}
ORDER = ["crop", "stage", "organ", "symptom", "extent", "weather"]
DONE = Screen("পেয়েছি। উত্তর কয়েক মিনিটে SMS-এ আসবে।", end=True)


def _options(step: str, state: dict) -> list[tuple[str, str]]:
    crop = state.get("crop")
    if step == "crop":
        return triage.CROPS
    if step == "stage":
        return [(k, lab) for k, lab, _, _ in triage.STAGES[crop]]
    if step == "organ":
        return [(o, triage.ORGAN_BN[o]) for o in triage.organs(crop)]
    if step == "symptom":
        return [(s, triage.SYMPTOM_BN[s]) for s in triage.symptoms(crop, state["organ"])]
    if step == "extent":
        return triage.EXTENTS
    return triage.WEATHER


def _screen(step: str, state: dict) -> Screen:
    if step == "shortcut":
        s = state["shortcut"]
        basis = "রোপণের" if s["crop"] in triage.RICE else "বপনের"
        return Screen(f"{triage.CROP_BN[s['crop']]}, {basis} {s['days']} দিন?\n1. হ্যাঁ\n2. অন্য ফসল\n0. পিছনে")
    return paged(TITLES[step], [lab for _, lab in _options(step, state)], state.get("pg", 0))


def _needs_weather(state: dict) -> bool:
    return any(r.needs_weather and r.crop == state["crop"] and r.organ == state["organ"]
               and state["symptom"] in r.symptoms for r in triage.RULES)


def _next(step: str, state: dict) -> str | None:
    i = ORDER.index(step) + 1
    while i < len(ORDER):
        nxt = ORDER[i]
        if nxt == "stage" and state.get("days_exact") is not None:
            i += 1
            continue
        if nxt == "weather" and not _needs_weather(state):
            return None
        return nxt
    return None


def _prev(step: str, state: dict) -> str | None:
    i = ORDER.index(step) - 1
    if i >= 0 and ORDER[i] in ("crop", "stage") and state.get("days_exact") is not None:
        return None  # the shortcut filled crop and stage: back leaves the menu
    return ORDER[i] if i >= 0 else None


def plan_shortcut(ctx) -> dict | None:
    """The saved plan's crop and days since sowing/transplanting, if in a known stage."""
    plan = ctx.plan or {}
    crop = plan.get("crop")
    if crop not in triage.STAGES:
        return None
    sown = sorted(t["date"] for t in plan.get("tasks") or [] if t.get("category") == "sowing")
    if not sown:
        return None
    days = (ctx.today - date.fromisoformat(sown[0])).days
    last = triage.STAGES[crop][-1][3]
    if not 0 <= days <= last:
        return None
    stage_key = next(k for k, _, lo, hi in triage.STAGES[crop] if lo <= days <= hi)
    return {"crop": crop, "days": days, "stage": stage_key}


def _go(step: str, state: dict) -> tuple[Screen, dict, None]:
    state = {**state, "step": step, "pg": 0}
    return _screen(step, state), state, None


def _finish(state: dict) -> tuple[Screen, dict, dict]:
    request = {k: state.get(k) for k in ("crop", "stage", "organ", "symptom", "extent")}
    request["weather"] = state.get("weather") or "none"
    request["days_exact"] = state.get("days_exact")
    return DONE, {"at": "main"}, {"kind": "problem", "request": request}


def problem(state: dict, text: str | None, ctx) -> tuple[Screen, dict, dict | None]:
    if text is None:
        base = {"at": "problem", "sub": "problem"}
        shortcut = plan_shortcut(ctx)
        if shortcut:
            return _go("shortcut", {**base, "shortcut": shortcut})
        return _go("crop", base)

    step = state.get("step", "crop")
    if text == "#resume":  # a dropped session picked up again: show the same screen
        return _screen(step, state), state, None
    inp = (text or "").strip().translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))

    if step == "shortcut":
        s = state["shortcut"]
        if inp == "1":
            return _go("organ", {**state, "crop": s["crop"], "stage": s["stage"], "days_exact": s["days"]})
        if inp == "2":
            return _go("crop", state)
        if inp == "0":
            return main_menu(ctx), {"at": "main"}, None
        return Screen(with_note(_screen(step, state).text, BAD)), state, None

    options = _options(step, state)
    kind, val = pick_paged(TITLES[step], [lab for _, lab in options], state.get("pg", 0), inp)
    if kind == "page":
        state = {**state, "pg": val}
        return _screen(step, state), state, None
    if kind == "back":
        prev = _prev(step, state)
        if prev is None:
            return main_menu(ctx), {"at": "main"}, None
        return _go(prev, state)
    if kind == "bad":
        return Screen(with_note(_screen(step, state).text, BAD)), state, None

    chosen = options[val][0]
    state = {**state, step: chosen}
    if step == "crop":  # a new crop invalidates the rest of the walk
        state = {k: v for k, v in state.items() if k not in ("stage", "organ", "symptom", "days_exact")}
        state["crop"] = chosen
    nxt = _next(step, state)
    if nxt is None:
        return _finish(state)
    return _go(nxt, state)


SUBMENUS = {"problem": problem}


async def run_problem_action(local_msisdn: str, farm_id: str, action: dict) -> None:
    """Diagnose from the table, text the farmer, record the report and a trace."""
    from backend.api import sse
    from backend.memory import store

    from . import sms
    from .identity import mask, session_id_for

    req = action["request"]
    diag = triage.diagnose(req["crop"], req["stage"], req["organ"], req["symptom"], req["extent"],
                           req.get("weather") or "none", req.get("days_exact"))
    profile = store.get_farm(farm_id) or {}
    area = profile.get("area") if profile.get("area_unit", "bigha") == "bigha" else None
    body = triage.answer_sms(diag, area if isinstance(area, (int, float)) else None)
    sms.send_sms(farm_id, body, parts=5)
    detail = diag.to_dict()
    store.save_triage_report(farm_id, profile.get("district"), detail, body)
    # Traced like any tool (CLAUDE.md rule 5), so the monitor shows how the answer was made.
    call_id = f"triage-{uuid.uuid4().hex[:12]}"
    events = [sse.tool_call(call_id, "crop_triage", req), sse.tool_result(call_id, "crop_triage", detail)]
    store.save_channel_turn(session_id_for(local_msisdn, "ussd"), farm_id, "ussd", mask(local_msisdn),
                            "ফসলের সমস্যা (মেনু)", body, events)
