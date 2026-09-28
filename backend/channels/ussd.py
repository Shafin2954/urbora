"""USSD menus — a pure state machine that never waits on the LLM.

A USSD screen must answer within seconds and an agent turn takes 10–40s, so
this module does three things only:

1. serves **stored** data instantly (the saved plan's next tasks, open weather
   alerts, the last SMS answer, paged);
2. collects the six intake fields through numbered menus — the same fields
   `ask_farmer` asks for on the web — and saves them to the farm profile, which
   every channel shares;
3. returns an **action** ("plan", "ask", "problem", "sms", "market") that the
   runtime runs in the background, delivering the result by SMS.

Screen budget (CHANNELS_RESEARCH.md §1): one USSD screen is 160 octets — 182
GSM-7 characters, but only **80 UCS-2 units for Bangla** (vowel signs count
separately). Every screen, error variants included, is built to fit
`screen_limit()`; `paged()` splits any option list that would not. The same
keys mean the same thing on every screen: **9 = আরও (more), 0 = পিছনে (back)**.

Sessions time out (≈180 s, 30–60 s per screen), and a full intake is longer
than one session, so an unfinished walk is saved per farm and offered back on
the next dial (`UssdContext.resume`).

`step()` is pure: state in, (screen, state, action) out. The runtime
(`ussd_request`) loads/saves state and runs actions. Bangla keypad digits
(০–৯) are accepted everywhere a digit is.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from backend.tools.ask import DISTRICT_BN
from backend.tools.districts import DISTRICTS

from .sms_text import CROP_BN, _units, encoding

log = logging.getLogger("channels.ussd")

SCREEN_UCS2 = 80          # 160 octets / 2 — any screen containing Bangla
SCREEN_GSM7 = 182         # 160 octets of packed 7-bit — plain ASCII screens
MAX_OPTIONS = 8           # keys 1–8; 9 = more, 0 = back
RESUME_WINDOW = timedelta(minutes=30)
SLOW_REQUEST_S = 1.0      # log any request slower than this; gateways drop at ~10–15 s

BAD = "ভুল!"
MORE = "9. আরও"
BACK = "0. পিছনে"

DIVISIONS: list[tuple[str, str]] = [
    ("Dhaka", "ঢাকা"), ("Chattogram", "চট্টগ্রাম"), ("Rajshahi", "রাজশাহী"), ("Khulna", "খুলনা"),
    ("Barishal", "বরিশাল"), ("Sylhet", "সিলেট"), ("Rangpur", "রংপুর"), ("Mymensingh", "ময়মনসিংহ"),
]
# Canonical values match backend/agent/loop.py's intake extractor.
SOILS = [("loam", "দোআঁশ"), ("clay_loam", "এঁটেল দোআঁশ"), ("sandy_loam", "বেলে দোআঁশ"),
         ("clay", "এঁটেল"), ("sandy", "বেলে"), ("silt", "পলি মাটি")]
WATERS = [("tubewell", "নলকূপ"), ("canal", "খাল"), ("rainfed", "বৃষ্টি নির্ভর")]
_WATER_SHORT = {"rainfed": "বৃষ্টি"}   # the one-line profile summary must fit a screen
SEASONS = [("rabi", "রবি"), ("kharif1", "খরিপ-১"), ("kharif2", "খরিপ-২")]
INTAKE_FIELDS = ("district", "area", "soil_type", "water_source", "season", "budget_bdt")
INTAKE_STATES = ("division", "district", "area", "soil", "water", "season", "budget", "confirm")

# Main menu: (key, label, target). Two pages; every key works from either page.
MAIN_ITEMS: list[tuple[str, str, str]] = [
    ("1", "ফসল পরামর্শ", "advice"),
    ("2", "ফসলের সমস্যা", "problem"),
    ("3", "আমার প্ল্যান", "plan"),
    ("4", "আবহাওয়া", "alerts"),
    ("5", "সার-বালাইনাশক কিনুন", "inputs"),
    ("6", "ফসল বিক্রি", "produce"),
    ("7", "শেষ উত্তর", "last"),
    ("8", "প্রশ্ন লিখুন", "ask"),
]
MAIN_PAGE_1 = 4           # items 1–4 on the first page, 5–8 behind "9. আরও"

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
    # An unfinished walk from a dropped session, offered back on dial.
    resume: dict | None = None
    # Sub-menus plug in here (backend/market/ussd_menus.py, triage_menu.py):
    # name -> handler(state, input, ctx) -> (Screen, state, action|None)
    submenus: dict[str, Callable[..., tuple[Screen, dict, dict | None]]] = field(default_factory=dict)


# --- screen budget -----------------------------------------------------------------


def screen_limit(text: str) -> int:
    return SCREEN_GSM7 if encoding(text) == "gsm7" else SCREEN_UCS2


def fits(text: str) -> bool:
    return _units(text) <= screen_limit(text)


def clip(text: str, tail: str = "") -> str:
    """Cut `text` (at a word if possible) so that text + tail fits one screen."""
    joined = f"{text}\n{tail}" if tail else text
    if fits(joined):
        return joined
    room = SCREEN_UCS2 - len(tail) - (2 if tail else 1)
    cut = text[:room]
    if " " in cut[room // 2:]:
        cut = cut[:cut.rfind(" ")]
    cut = cut.rstrip(" ,।") + "…"
    return f"{cut}\n{tail}" if tail else cut


def with_note(text: str, note: str) -> str:
    """An error/notice screen: the note replaces the first (title) line, so an
    error variant is never longer than the screen it repeats."""
    lines = text.split("\n")
    return "\n".join([note] + lines[1:]) if len(lines) > 1 else note


def paginate(title: str, labels: list[str], back: bool = True) -> list[list[int]]:
    """Split option indexes into pages that each fit one screen, rendered with
    the title, keys 1..k, "9. আরও" (reserved on every page) and "0. পিছনে"."""
    pages: list[list[int]] = []
    cur: list[int] = []
    for i in range(len(labels)):
        trial = cur + [i]
        if cur and (len(trial) > MAX_OPTIONS or not fits(_page_text(title, labels, trial, True, back))):
            pages.append(cur)
            cur = [i]
        else:
            cur = trial
    if cur or not pages:
        pages.append(cur)
    return pages


def _page_text(title: str, labels: list[str], idx: list[int], more: bool, back: bool) -> str:
    lines = [title] + [f"{k}. {labels[i]}" for k, i in enumerate(idx, 1)]
    if more:
        lines.append(MORE)
    if back:
        lines.append(BACK)
    return "\n".join(lines)


def paged(title: str, labels: list[str], page: int, back: bool = True) -> Screen:
    pages = paginate(title, labels, back)
    page = max(0, min(page, len(pages) - 1))
    return Screen(_page_text(title, labels, pages[page], page < len(pages) - 1, back))


def pick_paged(title: str, labels: list[str], page: int, inp: str, back: bool = True):
    """Interpret a key on a paged menu: ("pick", index) | ("page", n) | ("back", None) | ("bad", None)."""
    pages = paginate(title, labels, back)
    page = max(0, min(page, len(pages) - 1))
    if inp == "9" and page < len(pages) - 1:
        return "page", page + 1
    if inp == "0":
        return ("page", page - 1) if page > 0 else ("back", None)
    if inp.isdigit() and 1 <= int(inp) <= len(pages[page]):
        return "pick", pages[page][int(inp) - 1]
    return "bad", None


# --- helpers -----------------------------------------------------------------------


def _digits(text: str | None) -> str:
    return (text or "").strip().translate(_BN_DIGITS)


def _label(options: list[tuple[str, str]], value: str | None) -> str:
    return next((lab for val, lab in options if val == value), value or "")


def profile_complete(profile: dict | None) -> bool:
    return bool(profile) and all(profile.get(f) not in (None, "") for f in INTAKE_FIELDS)


def profile_line(profile: dict) -> str:
    """One compact line: district, area, soil, water, season, budget."""
    area = profile.get("area")
    return " ".join([
        DISTRICT_BN.get(profile.get("district", ""), profile.get("district", "")),
        f"{area:g}বিঘা" if isinstance(area, (int, float)) else f"{area}বিঘা",
        _label(SOILS, profile.get("soil_type")),
        _WATER_SHORT.get(profile.get("water_source", ""), _label(WATERS, profile.get("water_source"))),
        _label(SEASONS, profile.get("season")),
        f"৳{int(profile.get('budget_bdt') or 0)}",
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


def _chunks(text: str, size: int) -> list[str]:
    """Split long text into pages of at most `size` units, at spaces when possible."""
    out, rest = [], text.strip()
    while len(rest) > size:
        cut = rest.rfind(" ", size // 2, size)
        cut = cut if cut > 0 else size
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return out + [rest] if rest or not out else out


# --- screens -------------------------------------------------------------------


def main_menu(ctx: UssdContext, page: int = 0) -> Screen:
    if page == 0:
        lines = [ctx.brand] + [f"{k}. {lab}" for k, lab, _ in MAIN_ITEMS[:MAIN_PAGE_1]] + [MORE]
    else:
        lines = [f"{k}. {lab}" for k, lab, _ in MAIN_ITEMS[MAIN_PAGE_1:]] + [BACK]
    return Screen("\n".join(lines))


def _plan_screen(ctx: UssdContext) -> Screen:
    plan = ctx.plan
    if not plan or not plan.get("tasks"):
        return Screen("এখনো কোনো প্ল্যান নেই। মূল মেনু থেকে 1 চাপুন।", end=True)
    upcoming = [t for t in plan["tasks"] if date.fromisoformat(t["date"]) >= ctx.today]
    if not upcoming:
        return Screen("প্ল্যানের সব কাজ শেষ। নতুন পরামর্শের জন্য 1 চাপুন।", end=True)
    lines = [f"প্ল্যান: {CROP_BN.get(plan.get('crop', ''), plan.get('crop', ''))}"]
    for t in upcoming[:3]:
        d = date.fromisoformat(t["date"])
        row = f"{d.day}/{d.month} {t['task']}"
        if not fits("\n".join(lines + [row])):
            if len(lines) == 1:  # even one task is too long: shorten it
                lines.append(clip(row))
            break
        lines.append(row)
    return Screen("\n".join(lines), end=True)


def _alerts_screen(ctx: UssdContext) -> tuple[Screen, dict | None]:
    """A short screen; the full alert (forecast mm, source, what to do) goes by SMS."""
    from .alerts_job import alert_sms_text
    open_alerts = [a for a in ctx.alerts if a.get("status", "open") == "open"
                   and date.fromisoformat(a["task_date"]) >= ctx.today]
    if not open_alerts:
        return Screen("এখন কোনো আবহাওয়া সতর্কতা নেই।", end=True), None
    first = sorted(open_alerts, key=lambda a: a["task_date"])[0]
    d = date.fromisoformat(first["task_date"])
    rain = (first.get("provenance") or {}).get("value")
    rain_txt = f"{rain:g} মিমি বৃষ্টি" if isinstance(rain, (int, float)) else "ভারী বৃষ্টি"
    screen = Screen(clip(f"{d.day}/{d.month}: {rain_txt}র পূর্বাভাস। '{first['task']}' পিছিয়ে দিন।",
                         "বিস্তারিত SMS-এ আসছে।"), end=True)
    return screen, {"kind": "sms", "text": alert_sms_text(first)}


LAST_TAIL = f"{MORE}\n0. মেনু"


def _last_pages(ctx: UssdContext) -> list[str]:
    return _chunks(ctx.last_answer or "", SCREEN_UCS2 - len(LAST_TAIL) - 1)


def _render(at: str, state: dict, ctx: UssdContext) -> Screen:
    if at == "main":
        return main_menu(ctx, state.get("mpage", 0))
    if at == "resume":
        return Screen("আগের কাজ অসমাপ্ত।\n1. চালিয়ে যান\n2. নতুন শুরু")
    if at == "reuse":
        return Screen(f"আগের তথ্যে পরামর্শ?\n1. হ্যাঁ, দেখান\n2. নতুন তথ্য দিন\n{BACK}")
    if at == "division":
        return paged("বিভাগ:", [lab for _, lab in DIVISIONS], state.get("dvpage", 0))
    if at == "district":
        return paged("জেলা:", _district_labels(state["division"]), state.get("dpage", 0))
    if at == "area":
        return Screen(f"জমি কত বিঘা?\nসংখ্যা লিখুন\n{BACK}")
    if at == "soil":
        return paged("মাটি?", [lab for _, lab in SOILS], state.get("spage", 0))
    if at == "water":
        return paged("সেচের পানি?", [lab for _, lab in WATERS], 0)
    if at == "season":
        return paged("কোন মৌসুম?", [lab for _, lab in SEASONS], 0)
    if at == "budget":
        return Screen(f"বাজেট কত টাকা?\nসংখ্যা লিখুন\n{BACK}")
    if at == "confirm":
        return Screen(clip(profile_line(state["profile"]), "1. পাঠান\n2. বাতিল"))
    if at == "ask":
        return Screen(f"আপনার প্রশ্ন লিখুন:\n{BACK}")
    if at == "last":
        pages = _last_pages(ctx)
        i = max(0, min(state.get("lpage", 0), len(pages) - 1))
        return Screen(pages[i] + ("\n" + LAST_TAIL if i < len(pages) - 1 else "\n0. মেনু"))
    return main_menu(ctx)


def _district_names(division: str) -> list[str]:
    return sorted(d for d, v in DISTRICTS.items() if v[0] == division)


def _district_labels(division: str) -> list[str]:
    return [DISTRICT_BN.get(n, n) for n in _district_names(division)]


def _go(at: str, state: dict, ctx: UssdContext, note: str = "") -> tuple[Screen, dict, None]:
    state = {**state, "at": at}
    screen = _render(at, state, ctx)
    if note:
        screen = Screen(with_note(screen.text, note), screen.end)
    return screen, state, None


def _enter(target: str, state: dict, ctx: UssdContext) -> tuple[Screen, dict, dict | None]:
    """Open a main-menu item."""
    if target == "advice":
        if profile_complete(ctx.profile):
            return _go("reuse", {"at": "reuse"}, ctx)
        return _go("division", {"at": "division", "profile": {}}, ctx)
    if target == "plan":
        return _plan_screen(ctx), state, None
    if target == "alerts":
        screen, action = _alerts_screen(ctx)
        return screen, state, action
    if target in ("inputs", "produce", "problem"):
        if target in ctx.submenus:
            return ctx.submenus[target]({"at": target, "sub": target}, None, ctx)
        return Screen("এই সেবা এখনো চালু হয়নি।", end=True), state, None
    if target == "ask":
        return _go("ask", {"at": "ask"}, ctx)
    if target == "last":
        if not ctx.last_answer:
            return Screen("এখনো কোনো উত্তর নেই।", end=True), state, None
        return _go("last", {"at": "last", "lpage": 0}, ctx)
    return main_menu(ctx), {"at": "main"}, None


RESUMABLE_SUBMENUS = ("problem",)   # long walks only; a 3-screen purchase is quicker to redo


def resumable(state: dict | None) -> bool:
    """A walk worth offering back after a dropped session."""
    if not state:
        return False
    if state.get("at") == "resume":
        return resumable(state.get("saved"))
    return state.get("at") in INTAKE_STATES or state.get("sub") in RESUMABLE_SUBMENUS


def step(state: dict | None, text: str | None, ctx: UssdContext) -> tuple[Screen, dict, dict | None]:
    """Advance one screen. `state is None` (or text None) = the farmer just dialled."""
    if not state or text is None:
        if resumable(ctx.resume):
            return _go("resume", {"at": "resume", "saved": ctx.resume}, ctx)
        return main_menu(ctx), {"at": "main"}, None
    at = state.get("at", "main")
    inp = _digits(text)

    if at == "resume":
        if inp == "1":
            saved = dict(state["saved"])
            if saved.get("sub") in ctx.submenus:
                return ctx.submenus[saved["sub"]](saved, "#resume", ctx)
            return _go(saved.get("at", "main"), saved, ctx)
        if inp == "2":
            return main_menu(ctx), {"at": "main"}, None
        return _go(at, state, ctx, BAD)

    if at in ctx.submenus or state.get("sub"):
        name = state.get("sub") or at
        return ctx.submenus[name](state, text, ctx)

    if at == "main":
        if inp == "9" and state.get("mpage", 0) == 0:
            return _go("main", {"at": "main", "mpage": 1}, ctx)
        if inp == "0" and state.get("mpage", 0) == 1:
            return _go("main", {"at": "main", "mpage": 0}, ctx)
        target = next((t for k, _, t in MAIN_ITEMS if k == inp), None)
        if target:
            return _enter(target, state, ctx)
        return _go("main", state, ctx, BAD)

    if inp == "0" and at in ("reuse", "area", "water", "season", "budget", "ask", "last"):
        back = {"reuse": "main", "area": "district", "water": "soil", "season": "water",
                "budget": "season", "ask": "main", "last": "main"}[at]
        if back == "main":
            return main_menu(ctx), {"at": "main"}, None
        return _go(back, state, ctx)

    profile = dict(state.get("profile") or {})

    if at == "reuse":
        if inp == "1":
            return _go("confirm", {**state, "profile": dict(ctx.profile or {})}, ctx)
        if inp == "2":
            return _go("division", {**state, "profile": {}}, ctx)
        return _go("reuse", state, ctx, BAD)

    if at == "division":
        kind, val = pick_paged("বিভাগ:", [lab for _, lab in DIVISIONS], state.get("dvpage", 0), inp)
        if kind == "pick":
            return _go("district", {**state, "division": DIVISIONS[val][0], "dpage": 0}, ctx)
        if kind == "page":
            return _go("division", {**state, "dvpage": val}, ctx)
        if kind == "back":
            return main_menu(ctx), {"at": "main"}, None
        return _go(at, state, ctx, BAD)

    if at == "district":
        names = _district_names(state["division"])
        kind, val = pick_paged("জেলা:", _district_labels(state["division"]), state.get("dpage", 0), inp)
        if kind == "pick":
            profile["district"] = names[val]
            return _go("area", {**state, "profile": profile}, ctx)
        if kind == "page":
            return _go("district", {**state, "dpage": val}, ctx)
        if kind == "back":
            return _go("division", state, ctx)
        return _go(at, state, ctx, BAD)

    if at == "area":
        try:
            area = float(inp)
        except ValueError:
            area = -1
        if not 0 < area <= 1000:
            return _go(at, state, ctx, "ভুল সংখ্যা! কত বিঘা?")
        profile.update(area=area, area_unit="bigha")
        return _go("soil", {**state, "profile": profile, "spage": 0}, ctx)

    for at_name, options, fld, nxt, title, page_key in (
            ("soil", SOILS, "soil_type", "water", "মাটি?", "spage"),
            ("water", WATERS, "water_source", "season", "সেচের পানি?", None),
            ("season", SEASONS, "season", "budget", "কোন মৌসুম?", None)):
        if at == at_name:
            kind, val = pick_paged(title, [lab for _, lab in options],
                                   state.get(page_key, 0) if page_key else 0, inp)
            if kind == "pick":
                profile[fld] = options[val][0]
                return _go(nxt, {**state, "profile": profile}, ctx)
            if kind == "page" and page_key:
                return _go(at, {**state, page_key: val}, ctx)
            if kind == "back":
                prev = {"soil": "area", "water": "soil", "season": "water"}[at]
                return _go(prev, state, ctx)
            return _go(at, state, ctx, BAD)

    if at == "budget":
        if not inp.isdigit() or int(inp) <= 0:
            return _go(at, state, ctx, "ভুল সংখ্যা! কত টাকা?")
        profile["budget_bdt"] = int(inp)
        return _go("confirm", {**state, "profile": profile}, ctx)

    if at == "confirm":
        if inp == "1":
            action = {"kind": "plan", "profile": profile, "message": agent_message(profile)}
            return Screen("ধন্যবাদ! পরামর্শ কয়েক মিনিটে SMS-এ আসবে।", end=True), state, action
        if inp == "2":
            return Screen("বাতিল করা হয়েছে।", end=True), state, None
        return _go(at, state, ctx, BAD)

    if at == "ask":
        question = (text or "").strip()
        if not question:
            return _go(at, state, ctx, BAD)
        return (Screen("প্রশ্ন পেয়েছি। উত্তর কয়েক মিনিটে SMS-এ আসবে।", end=True), state,
                {"kind": "ask", "message": question})

    if at == "last":
        if inp == "9" and state.get("lpage", 0) < len(_last_pages(ctx)) - 1:
            return _go("last", {**state, "lpage": state.get("lpage", 0) + 1}, ctx)
        return _go(at, state, ctx, BAD)

    return main_menu(ctx), {"at": "main"}, None


# --- runtime --------------------------------------------------------------------

_background: set[asyncio.Task] = set()


def _state_key(ussd_session_id: str) -> str:
    return f"ussd-{ussd_session_id}"


def build_context(farm_id: str, resume: dict | None = None) -> UssdContext:
    from backend.branding import BRAND_NAME
    from backend.memory import store
    last = next((m["body"] for m in store.list_sms(farm_id, 20) if m["direction"] == "out"), None)
    submenus: dict[str, Any] = {}
    try:
        from backend.market.ussd_menus import SUBMENUS
        submenus.update(SUBMENUS)
    except ImportError:
        pass
    try:
        from .triage_menu import SUBMENUS as TRIAGE
        submenus.update(TRIAGE)
    except ImportError:
        pass
    return UssdContext(
        brand=BRAND_NAME, farm_id=farm_id, profile=store.get_farm(farm_id),
        plan=store.get_plan(farm_id), alerts=store.get_alerts(farm_id),
        last_answer=last, resume=resume, submenus=submenus,
    )


async def run_action(local_msisdn: str, farm_id: str, action: dict) -> None:
    """Run a USSD-requested action in the background; results go out by SMS."""
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
        elif action["kind"] == "sms":
            sms.send_sms(farm_id, action["text"])
        elif action["kind"] == "problem":
            from .triage_menu import run_problem_action
            await run_problem_action(local_msisdn, farm_id, action)
        elif action["kind"] == "market":
            from backend.market.ussd_menus import run_market_action
            run_market_action(local_msisdn, farm_id, action)
    except Exception:  # noqa: BLE001 — the screen already closed; log, don't lose it silently
        log.exception("USSD action failed")


def _find_resume(farm_id: str, current_key: str) -> dict | None:
    """The farm's latest unfinished walk from another session, if recent."""
    from backend.memory import store
    found = store.latest_ussd_state(farm_id, exclude=current_key)
    if not found:
        return None
    state, updated_at = found
    if state.get("at") == "resume":   # dropped again on the offer itself
        state = state.get("saved") or {}
    try:
        when = datetime.fromisoformat(updated_at)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - when > RESUME_WINDOW:
        return None
    return state if resumable(state) else None


async def ussd_request(ussd_session_id: str, msisdn: str, text: str | None, is_init: bool) -> Screen:
    """One USSD round trip: returns the screen to show, and schedules any
    agent work in the background so the screen never waits on it."""
    from backend.memory import store

    from .identity import farm_id_for, mask, normalise

    started = time.monotonic()
    local = normalise(msisdn)
    farm_id = farm_id_for(local)
    store.upsert_contact(farm_id, local, mask(local), "ussd")
    key = _state_key(ussd_session_id)
    state = None if is_init else store.get_ussd_state(key)
    resume = _find_resume(farm_id, key) if is_init else None
    screen, new_state, action = step(state, None if is_init else text, build_context(farm_id, resume))
    if resume is not None and new_state.get("at") == "resume":
        # The saved walk now lives in this session; the old one is never offered twice.
        store.close_other_ussd_states(farm_id, keep=key)
    # A finished screen closes the walk, so it is never offered for resume.
    store.save_ussd_state(key, farm_id, {"at": "done"} if screen.end else new_state)
    if action:
        task = asyncio.create_task(run_action(local, farm_id, action))
        _background.add(task)
        task.add_done_callback(_background.discard)
    elapsed = time.monotonic() - started
    if elapsed > SLOW_REQUEST_S:
        log.warning("USSD request took %.2f s (gateway limit ~10 s)", elapsed)
    return screen
