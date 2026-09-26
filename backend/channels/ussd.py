"""USSD menus — a pure state machine that never waits on the LLM.

A USSD screen must answer within seconds and an agent turn takes 10–40s, so
this module does three things only:

1. serves **stored** data instantly (the saved plan's next tasks, open weather
   alerts, the last SMS answer, paged);
2. collects the six intake fields through numbered menus — the same fields
   `ask_farmer` asks for on the web — and saves them to the farm profile, which
   every channel shares;
3. returns an **action** ("plan" or "ask") that the runtime runs in the
   background, delivering the agent's answer by SMS.

`step()` is pure: state in, (screen, state, action) out. The runtime
(`ussd_request`) loads/saves state and runs actions. Bangla keypad digits
(০–৯) are accepted everywhere a digit is.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from backend.tools.ask import DISTRICT_BN
from backend.tools.districts import DISTRICTS

from .sms_text import CROP_BN

log = logging.getLogger("channels.ussd")

PAGE_CHARS = 120          # long text is paged at this many characters
DISTRICTS_PER_PAGE = 7    # keys 1–7; 8 = next page; 0 = back

DIVISIONS: list[tuple[str, str]] = [
    ("Dhaka", "ঢাকা"), ("Chattogram", "চট্টগ্রাম"), ("Rajshahi", "রাজশাহী"), ("Khulna", "খুলনা"),
    ("Barishal", "বরিশাল"), ("Sylhet", "সিলেট"), ("Rangpur", "রংপুর"), ("Mymensingh", "ময়মনসিংহ"),
]
# Canonical values match backend/agent/loop.py's intake extractor.
SOILS = [("loam", "দোআঁশ"), ("clay_loam", "এঁটেল দোআঁশ"), ("sandy_loam", "বেলে দোআঁশ"),
         ("clay", "এঁটেল"), ("sandy", "বেলে"), ("silt", "পলি মাটি")]
WATERS = [("tubewell", "নলকূপ"), ("canal", "খাল"), ("rainfed", "বৃষ্টি নির্ভর")]
SEASONS = [("rabi", "রবি"), ("kharif1", "খরিপ-১"), ("kharif2", "খরিপ-২")]
INTAKE_FIELDS = ("district", "area", "soil_type", "water_source", "season", "budget_bdt")

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


@dataclass
class Screen:
    text: str
    end: bool = False


@dataclass
class UssdContext:
    brand: str
    farm_id: str
    profile: dict | None = None
    plan: dict | None = None
    alerts: list[dict] = field(default_factory=list)
    last_answer: str | None = None
    today: date = field(default_factory=date.today)
    # Marketplace sub-menus plug in here (backend/market/ussd_menus.py):
    # name -> handler(state, input, ctx) -> (Screen, state, action|None)
    submenus: dict[str, Callable[..., tuple[Screen, dict, dict | None]]] = field(default_factory=dict)


def _digits(text: str | None) -> str:
    return (text or "").strip().translate(_BN_DIGITS)


def _label(options: list[tuple[str, str]], value: str | None) -> str:
    return next((lab for val, lab in options if val == value), value or "")


def _pick(options: list[tuple[str, str]], text: str) -> str | None:
    t = _digits(text)
    if t.isdigit() and 1 <= int(t) <= len(options):
        return options[int(t) - 1][0]
    return None


def _options_text(title: str, options: list[tuple[str, str]], back: bool = True) -> str:
    lines = [title] + [f"{i}. {lab}" for i, (_, lab) in enumerate(options, 1)]
    if back:
        lines.append("0. পিছনে")
    return "\n".join(lines)


def profile_complete(profile: dict | None) -> bool:
    return bool(profile) and all(profile.get(f) not in (None, "") for f in INTAKE_FIELDS)


def profile_line(profile: dict) -> str:
    area = profile.get("area")
    return ", ".join([
        DISTRICT_BN.get(profile.get("district", ""), profile.get("district", "")),
        f"{area:g} বিঘা" if isinstance(area, (int, float)) else f"{area} বিঘা",
        _label(SOILS, profile.get("soil_type")),
        _label(WATERS, profile.get("water_source")),
        _label(SEASONS, profile.get("season")),
        f"৳{int(profile.get('budget_bdt') or 0):,}",
    ])


def agent_message(profile: dict) -> str:
    """The Bangla request the agent receives after USSD intake. Uses the words
    the deterministic extractor in loop.py already maps to canonical fields."""
    return (
        f"আমার জেলা {DISTRICT_BN.get(profile['district'], profile['district'])}, "
        f"জমি {profile['area']:g} বিঘা, মাটি {_label(SOILS, profile['soil_type'])}, "
        f"সেচ {_label(WATERS, profile['water_source'])}, মৌসুম {_label(SEASONS, profile['season'])}, "
        f"বাজেট {int(profile['budget_bdt'])} টাকা। কোন ফসল চাষ করব? "
        "পরিকল্পনা ও খরচের হিসাব দিন।"
    )


def _page(text: str, page: int) -> tuple[str, bool]:
    chunks = [text[i:i + PAGE_CHARS] for i in range(0, len(text), PAGE_CHARS)] or [""]
    page = max(0, min(page, len(chunks) - 1))
    return chunks[page], page < len(chunks) - 1


# --- screens -------------------------------------------------------------------


def main_menu(ctx: UssdContext, note: str = "") -> Screen:
    lines = ([note] if note else []) + [
        ctx.brand,
        "1. নতুন পরামর্শ",
        "2. আমার প্ল্যান",
        "3. আবহাওয়া সতর্কতা",
        "4. উপকরণ কিনুন",
        "5. ফসল বিক্রি",
        "6. প্রশ্ন করুন",
        "7. শেষ উত্তর",
    ]
    return Screen("\n".join(lines))


def _plan_screen(ctx: UssdContext) -> Screen:
    plan = ctx.plan
    if not plan or not plan.get("tasks"):
        return Screen("এখনো কোনো প্ল্যান নেই। মূল মেনু থেকে 1 চাপুন।", end=True)
    upcoming = [t for t in plan["tasks"] if date.fromisoformat(t["date"]) >= ctx.today][:3]
    if not upcoming:
        return Screen("প্ল্যানের সব কাজ শেষ। নতুন পরামর্শের জন্য 1 চাপুন।", end=True)
    head = f"আমার প্ল্যান: {CROP_BN.get(plan.get('crop', ''), plan.get('crop', ''))}"
    rows = [f"{date.fromisoformat(t['date']).day}/{date.fromisoformat(t['date']).month} {t['task']}"
            for t in upcoming]
    return Screen("\n".join([head] + rows), end=True)


def _alerts_screen(ctx: UssdContext) -> Screen:
    from .alerts_job import alert_sms_text
    open_alerts = [a for a in ctx.alerts if a.get("status", "open") == "open"
                   and date.fromisoformat(a["task_date"]) >= ctx.today]
    if not open_alerts:
        return Screen("এখন কোনো আবহাওয়া সতর্কতা নেই।", end=True)
    return Screen(alert_sms_text(sorted(open_alerts, key=lambda a: a["task_date"])[0]), end=True)


def _render(at: str, state: dict, ctx: UssdContext) -> Screen:
    if at == "main":
        return main_menu(ctx)
    if at == "reuse":
        return Screen(f"আগের তথ্য:\n{profile_line(ctx.profile or {})}\n1. এটাই ব্যবহার করুন\n2. নতুন করে দিন\n0. পিছনে")
    if at == "division":
        return Screen(_options_text("বিভাগ বাছুন:", DIVISIONS))
    if at == "district":
        names = sorted(d for d, v in DISTRICTS.items() if v[0] == state["division"])
        start = state.get("dpage", 0) * DISTRICTS_PER_PAGE
        page = names[start:start + DISTRICTS_PER_PAGE]
        lines = ["জেলা বাছুন:"] + [f"{i}. {DISTRICT_BN.get(n, n)}" for i, n in enumerate(page, 1)]
        if start + DISTRICTS_PER_PAGE < len(names):
            lines.append("8. আরও")
        lines.append("0. পিছনে")
        return Screen("\n".join(lines))
    if at == "area":
        return Screen("জমি কত বিঘা? সংখ্যা লিখুন\n0. পিছনে")
    if at == "soil":
        return Screen(_options_text("মাটি কেমন?", SOILS))
    if at == "water":
        return Screen(_options_text("সেচের পানি:", WATERS))
    if at == "season":
        return Screen(_options_text("কোন মৌসুম?", SEASONS))
    if at == "budget":
        return Screen("বাজেট কত টাকা? সংখ্যা লিখুন\n0. পিছনে")
    if at == "confirm":
        return Screen(f"{profile_line(state['profile'])}\n1. পরামর্শ পাঠান\n2. বাতিল")
    if at == "ask":
        return Screen("আপনার প্রশ্ন লিখুন:\n0. পিছনে")
    if at == "last":
        text, more = _page(ctx.last_answer or "", state.get("lpage", 0))
        return Screen(text + ("\n9. আরও" if more else "") + "\n0. মূল মেনু")
    return main_menu(ctx)


def _go(at: str, state: dict, ctx: UssdContext, note: str = "") -> tuple[Screen, dict, None]:
    state = {**state, "at": at}
    screen = _render(at, state, ctx)
    if note:
        screen = Screen(f"{note}\n{screen.text}", screen.end)
    return screen, state, None


def step(state: dict | None, text: str | None, ctx: UssdContext) -> tuple[Screen, dict, dict | None]:
    """Advance one screen. `state is None` (or text None) = the farmer just dialled."""
    if not state or text is None:
        return main_menu(ctx), {"at": "main"}, None
    at = state.get("at", "main")
    inp = _digits(text)
    bad = "ভুল বাছাই।"

    if at in ctx.submenus or state.get("sub"):
        name = state.get("sub") or at
        return ctx.submenus[name](state, text, ctx)

    if at == "main":
        if inp == "1":
            if profile_complete(ctx.profile):
                return _go("reuse", state, ctx)
            return _go("division", {"at": "division", "profile": {}}, ctx)
        if inp == "2":
            return _plan_screen(ctx), state, None
        if inp == "3":
            return _alerts_screen(ctx), state, None
        if inp in ("4", "5"):
            name = "inputs" if inp == "4" else "produce"
            if name in ctx.submenus:
                return ctx.submenus[name]({"at": name, "sub": name}, None, ctx)
            return Screen("এই সেবা এখনো চালু হয়নি।", end=True), state, None
        if inp == "6":
            return _go("ask", state, ctx)
        if inp == "7":
            if not ctx.last_answer:
                return Screen("এখনো কোনো উত্তর নেই।", end=True), state, None
            return _go("last", {**state, "lpage": 0}, ctx)
        return _go("main", state, ctx, bad)

    if inp == "0" and at in ("reuse", "division", "area", "soil", "water", "season", "budget", "ask", "last"):
        back = {"reuse": "main", "division": "main", "area": "district", "soil": "area",
                "water": "soil", "season": "water", "budget": "season", "ask": "main", "last": "main"}[at]
        if back == "district":
            return _go("district", {**state, "dpage": 0}, ctx)
        return _go(back, state, ctx)

    profile = dict(state.get("profile") or {})

    if at == "reuse":
        if inp == "1":
            return _go("confirm", {**state, "profile": dict(ctx.profile or {})}, ctx)
        if inp == "2":
            return _go("division", {**state, "profile": {}}, ctx)
        return _go("reuse", state, ctx, bad)

    if at == "division":
        div = _pick(DIVISIONS, inp)
        return _go("district", {**state, "division": div, "dpage": 0}, ctx) if div else _go(at, state, ctx, bad)

    if at == "district":
        names = sorted(d for d, v in DISTRICTS.items() if v[0] == state["division"])
        start = state.get("dpage", 0) * DISTRICTS_PER_PAGE
        page = names[start:start + DISTRICTS_PER_PAGE]
        if inp == "0":
            if state.get("dpage", 0) > 0:
                return _go("district", {**state, "dpage": state["dpage"] - 1}, ctx)
            return _go("division", state, ctx)
        if inp == "8" and start + DISTRICTS_PER_PAGE < len(names):
            return _go("district", {**state, "dpage": state.get("dpage", 0) + 1}, ctx)
        if inp.isdigit() and 1 <= int(inp) <= len(page):
            profile["district"] = page[int(inp) - 1]
            return _go("area", {**state, "profile": profile}, ctx)
        return _go(at, state, ctx, bad)

    if at == "area":
        try:
            area = float(inp)
        except ValueError:
            area = -1
        if not 0 < area <= 1000:
            return _go(at, state, ctx, "সঠিক সংখ্যা দিন।")
        profile.update(area=area, area_unit="bigha")
        return _go("soil", {**state, "profile": profile}, ctx)

    for at_name, options, fld, nxt in (("soil", SOILS, "soil_type", "water"),
                                       ("water", WATERS, "water_source", "season"),
                                       ("season", SEASONS, "season", "budget")):
        if at == at_name:
            val = _pick(options, inp)
            if not val:
                return _go(at, state, ctx, bad)
            profile[fld] = val
            return _go(nxt, {**state, "profile": profile}, ctx)

    if at == "budget":
        if not inp.isdigit() or int(inp) <= 0:
            return _go(at, state, ctx, "সঠিক সংখ্যা দিন।")
        profile["budget_bdt"] = int(inp)
        return _go("confirm", {**state, "profile": profile}, ctx)

    if at == "confirm":
        if inp == "1":
            action = {"kind": "plan", "profile": profile, "message": agent_message(profile)}
            return Screen("ধন্যবাদ! আপনার পরামর্শ কয়েক মিনিটের মধ্যে SMS-এ আসবে।", end=True), state, action
        if inp == "2":
            return Screen("বাতিল করা হয়েছে।", end=True), state, None
        return _go(at, state, ctx, bad)

    if at == "ask":
        question = (text or "").strip()
        if not question:
            return _go(at, state, ctx, bad)
        return (Screen("প্রশ্ন পেয়েছি। উত্তর কয়েক মিনিটের মধ্যে SMS-এ আসবে।", end=True), state,
                {"kind": "ask", "message": question})

    if at == "last":
        if inp == "9":
            return _go("last", {**state, "lpage": state.get("lpage", 0) + 1}, ctx)
        return _go(at, state, ctx, bad)

    return main_menu(ctx), {"at": "main"}, None


# --- runtime --------------------------------------------------------------------

_background: set[asyncio.Task] = set()


def _state_key(ussd_session_id: str) -> str:
    return f"ussd-{ussd_session_id}"


def build_context(farm_id: str) -> UssdContext:
    from backend.branding import BRAND_NAME
    from backend.memory import store
    last = next((m["body"] for m in store.list_sms(farm_id, 20) if m["direction"] == "out"), None)
    submenus: dict[str, Any] = {}
    try:
        from backend.market.ussd_menus import SUBMENUS
        submenus = dict(SUBMENUS)
    except ImportError:
        pass
    return UssdContext(
        brand=BRAND_NAME, farm_id=farm_id, profile=store.get_farm(farm_id),
        plan=store.get_plan(farm_id), alerts=store.get_alerts(farm_id),
        last_answer=last, submenus=submenus,
    )


async def run_action(local_msisdn: str, farm_id: str, action: dict) -> None:
    """Run a USSD-requested agent turn and deliver the answer by SMS."""
    from backend.memory import store

    from . import flows, sms
    from .adapter import run_channel_turn

    try:
        if action["kind"] == "plan":
            store.save_farm(farm_id, {**(store.get_farm(farm_id) or {}), **action["profile"]})
        if action["kind"] in ("plan", "ask"):
            reply = await run_channel_turn(local_msisdn, action["message"], "ussd")
            sms.send_sms(farm_id, reply.display_text())
            flows.send_summary(reply)
        elif action["kind"] == "market":
            from backend.market.ussd_menus import run_market_action
            run_market_action(local_msisdn, farm_id, action)
    except Exception:  # noqa: BLE001 — the screen already closed; log, don't lose it silently
        log.exception("USSD action failed")


async def ussd_request(ussd_session_id: str, msisdn: str, text: str | None, is_init: bool) -> Screen:
    """One USSD round trip: returns the screen to show, and schedules any
    agent work in the background so the screen never waits on it."""
    from backend.memory import store

    from .identity import farm_id_for, mask, normalise

    local = normalise(msisdn)
    farm_id = farm_id_for(local)
    store.upsert_contact(farm_id, local, mask(local), "ussd")
    key = _state_key(ussd_session_id)
    state = None if is_init else store.get_ussd_state(key)
    screen, new_state, action = step(state, None if is_init else text, build_context(farm_id))
    store.save_ussd_state(key, farm_id, new_state)
    if action:
        task = asyncio.create_task(run_action(local, farm_id, action))
        _background.add(task)
        task.add_done_callback(_background.discard)
    return screen
