"""One agent turn for a phone channel.

`run_turn` (backend/agent/loop.py) yields the same wire events the web app
receives over SSE. A phone cannot render them, so this module drains the stream
and keeps what a phone can use:

- the reply text (tokens, with the web-only chat-title marker stripped),
- a numbered menu when the agent asked a question with options (ask_farmer's
  chips/dropdown become "1. দোআঁশ  2. বেলে ..."),
- the plan / finance payloads, for the template-built SMS summary,
- the full event list, already redacted by sse.tool_call/tool_result, which is
  saved per turn so the web "live channels" monitor can replay it.

A numbered answer ("2") is mapped back to the option's Bangla label before it
reaches the agent — exactly what the web widget does (InputRequest.jsx sends
"দোআঁশ", not "2"), so the agent needs no second parsing path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.memory import store

from .identity import farm_id_for, mask, normalise, session_id_for

_TITLE_MARKER = re.compile(r"\s*\[\[CHAT_TITLE:[^\]]*\]\]\s*")
_MAX_MENU_OPTIONS = 9  # one keypad digit each


@dataclass
class Menu:
    """A question the farmer answers with a keypad digit or a typed value."""

    field: str
    prompt: str
    options: list[tuple[str, str]] = field(default_factory=list)  # (value, label_bn)
    free_entry: bool = False

    def render(self) -> str:
        lines = [self.prompt]
        for i, (_, label) in enumerate(self.options, start=1):
            lines.append(f"{i}. {label}")
        return "\n".join(lines)

    def resolve(self, answer: str) -> str:
        """Map "2" to the second option's label; any other text passes through."""
        a = answer.strip()
        if a.isdigit() and self.options:
            i = int(a)
            if 1 <= i <= len(self.options):
                return self.options[i - 1][1]
        return a

    def to_dict(self) -> dict:
        return {"field": self.field, "prompt": self.prompt,
                "options": [list(o) for o in self.options], "free_entry": self.free_entry}

    @classmethod
    def from_dict(cls, d: dict) -> "Menu":
        return cls(d["field"], d["prompt"], [tuple(o) for o in d.get("options", [])],
                   d.get("free_entry", False))


def menu_from_input_request(ir: dict) -> Menu:
    """ask_farmer's widget -> a keypad menu.

    Chips become numbered options. The 64-district dropdown is too long for a
    phone screen, so over SMS/voice the farmer types or says the district name
    (the USSD menu has its own division -> district pages instead). Number
    inputs are free entry, with the unit named in the prompt.
    """
    kind = ir.get("input_kind")
    prompt = ir.get("prompt_bn", "").strip()
    options = [(o["value"], o["label_bn"]) for o in (ir.get("options") or [])]
    if kind == "chips" and 0 < len(options) <= _MAX_MENU_OPTIONS:
        return Menu(ir.get("field", ""), prompt, options)
    if kind == "dropdown" and ir.get("field") == "district":
        return Menu("district", prompt + " (জেলার নাম লিখুন)", [], free_entry=True)
    if kind == "number_unit":
        return Menu(ir.get("field", ""), prompt + " (যেমন: 2 বিঘা)", [], free_entry=True)
    return Menu(ir.get("field", ""), prompt, [], free_entry=True)


@dataclass
class ChannelReply:
    session_id: str
    farm_id: str
    masked: str
    text: str = ""
    menu: Menu | None = None
    plan: dict | None = None
    finance: dict | None = None
    finance_crop: str | None = None
    alerts: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    error: str | None = None
    usage: dict | None = None

    def display_text(self) -> str:
        """What the phone shows / speaks: the reply, then the menu if any."""
        parts = [p for p in (self.text.strip(), self.menu.render() if self.menu else "") if p]
        return "\n".join(parts)


def _pending_key(farm_id: str) -> str:
    return f"menu-{farm_id}"


def pending_menu(farm_id: str) -> Menu | None:
    state = store.get_ussd_state(_pending_key(farm_id))
    return Menu.from_dict(state["menu"]) if state and state.get("menu") else None


def _set_pending_menu(farm_id: str, menu: Menu | None) -> None:
    store.save_ussd_state(_pending_key(farm_id), farm_id, {"menu": menu.to_dict() if menu else None})


async def run_channel_turn(
    msisdn: str,
    text: str,
    channel: str,
    *,
    session_stamp: str | None = None,
    language: str = "bn",
    client: Any = None,
) -> ChannelReply:
    """Run one agent turn for `msisdn` on `channel` ("sms" | "ussd" | "voice").

    Registers the contact, resolves a pending numbered menu, runs the agent,
    and persists the redacted turn. Never raises for an agent failure: the
    reply carries `error` and a Bangla apology instead.
    """
    from backend.agent.loop import run_turn  # lazy: keep import cost off the webhook path

    local = normalise(msisdn)
    farm_id = farm_id_for(local)
    masked = mask(local)
    session_id = session_id_for(local, channel, stamp=session_stamp)
    store.upsert_contact(farm_id, local, masked, channel)

    menu = pending_menu(farm_id)
    message = menu.resolve(text) if menu else text.strip()
    if menu:
        _set_pending_menu(farm_id, None)

    reply = ChannelReply(session_id=session_id, farm_id=farm_id, masked=masked)
    calls: dict[str, tuple[str, Any]] = {}
    chunks: list[str] = []
    try:
        async for event in run_turn(session_id, farm_id, message, client=client,
                                    language=language, channel=channel):
            kind = event.get("type")
            if kind == "token":
                chunks.append(event.get("text", ""))
                continue  # tokens are not trace; the reply text is saved once
            reply.events.append(event)
            if kind == "tool_call":
                calls[event.get("id", "")] = (event.get("name", ""), event.get("params"))
            elif kind == "plan_update":
                reply.plan = event.get("plan")
            elif kind == "finance_update":
                reply.finance = event.get("finance")
            elif kind == "alert":
                reply.alerts.append(event.get("alert"))
            elif kind == "input_request":
                reply.menu = menu_from_input_request(event)
            elif kind == "error":
                reply.error = event.get("message") or "agent error"
            elif kind == "done":
                reply.usage = {k: event.get(k) for k in ("in_tokens", "out_tokens", "cost_usd")}
    except Exception as exc:  # noqa: BLE001 — a phone must get an answer, not silence
        reply.error = f"{type(exc).__name__}: {exc}"

    for name, params in calls.values():
        if name == "finance_projection" and isinstance(params, dict):
            reply.finance_crop = params.get("crop")

    reply.text = _TITLE_MARKER.sub(" ", "".join(chunks)).strip()
    if reply.error and not reply.text:
        reply.text = "দুঃখিত, এখন উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
    if reply.menu:
        _set_pending_menu(farm_id, reply.menu)

    store.save_channel_turn(session_id, farm_id, channel, masked, message,
                            reply.display_text(), reply.events)
    return reply


def cost_is_complete(crop: str | None) -> bool:
    """False for crops whose cost rows are fertiliser-only (profit = ceiling)."""
    if not crop:
        return True
    try:
        from backend.finance.catalog import load_catalog
        return load_catalog().cost_basis(crop) == "complete"
    except Exception:  # noqa: BLE001 — unknown basis: label as a ceiling, never overclaim
        return False
