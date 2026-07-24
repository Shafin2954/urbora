"""Chat routes: the real /api/chat seam, and a dev harness for UI work.

/api/chat is B's route wrapping A's agent loop (PLAN.md §1: agent is A's,
routes are B's). The loop is imported lazily so that this file does not depend
on A's module existing yet — until it does, the endpoint degrades honestly with
an `error` event rather than pretending. The moment A pushes
`backend/agent/loop.py` exposing `run_turn`, this route starts working with no
change here.

/api/dev/harness exists because the chat UI has to be built before the agent
lands. Its events are contract-shaped but its content is deliberately, visibly
synthetic: it says it is a harness, in English, and contains no agronomic claim
of any kind. CLAUDE.md §2.2 forbids invented data and the frontend rules forbid
placeholder content — a harness that emitted plausible-looking Bangla farm
advice would violate both, and worse, would eventually be mistaken for working
software.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request

# THE CONTRACT (A, frozen H1). Imported, never redefined — a second definition
# of the request shape is how the two halves silently diverge.
from backend.schemas import ChatRequest

from . import sse

router = APIRouter()


def _load_agent():
    """Return A's `run_turn`, or None if the agent module isn't in the tree yet.

    Imported at call time, not module import time, so the API boots and every
    other route keeps working while A's side is still being built.
    """
    try:
        from backend.agent.loop import run_turn  # type: ignore
    except Exception:
        return None
    return run_turn


@router.post("/api/chat")
async def chat(payload: ChatRequest, request: Request):
    run_turn = _load_agent()

    async def events() -> AsyncIterator[dict]:
        if run_turn is None:
            # Honest degradation (CLAUDE.md §2.2): say what is missing, in the
            # trace, rather than emitting something that looks like an answer.
            yield sse.error(
                "Agent loop not wired yet (backend/agent/loop.py:run_turn not found). "
                "API, SSE transport and trace are live; the agent is A's next drop."
            )
            yield sse.done()
            return

        async for event in run_turn(
            session_id=payload.session_id,
            farm_id=payload.farm_id,
            message=payload.message,
        ):
            yield event

    return sse.sse_response(events(), request)


# --- dev harness ------------------------------------------------------------

# Every widget kind in the PLAN.md §2 contract, so the UI can be built and
# reviewed against all of them. Options are labelled as harness values; the
# real ones come from the agent at runtime.
_HARNESS_SCRIPT: list[tuple[float, Any]] = [
    (0.0, sse.token("UI harness — ")),
    (0.35, sse.token("not the agent. ")),
    (0.35, sse.token("Contract-shaped events only, no farm advice.")),
    (
        0.4,
        sse.tool_call(
            "harness_1",
            "_harness_echo",
            # Includes credential-shaped fields on purpose: the trace panel
            # must be seen redacting them during development, not first tested
            # the night bdapps goes in.
            {
                "note": "synthetic harness params",
                "applicationId": "APP_000123",
                "password": "9f8e7d6c5b4a39281706f5e4d3c2b1a0",
                "subscriberId": "tel:8801812345678",
                "lat": 24.3745,
                "lon": 88.6042,
            },
        ),
    ),
    (
        0.5,
        sse.tool_result(
            "harness_1",
            "_harness_echo",
            {"statusCode": "S1000", "note": "synthetic harness result"},
        ),
    ),
    (
        0.4,
        {
            "type": "input_request",
            "field": "area",
            "prompt_bn": "জমির পরিমাণ কত? (harness)",
            "input_kind": "number_unit",
            "options": None,
            "unit_options": ["bigha", "katha", "decimal", "acre"],
        },
    ),
    (0.3, sse.done(in_tokens=0, out_tokens=0, cost_usd=0.0)),
]


@router.post("/api/dev/harness")
async def dev_harness(request: Request):
    """Drives the chat UI with contract-shaped events. Never farmer content."""

    async def events() -> AsyncIterator[dict]:
        for delay, event in _HARNESS_SCRIPT:
            if delay:
                await asyncio.sleep(delay)
            yield event

    return sse.sse_response(events(), request)


@router.post("/api/dev/harness/widgets")
async def dev_harness_widgets(payload: ChatRequest, request: Request):
    """Emits input_request widgets for review.

    `message` selects a single kind by field name ("district", "soil_type",
    ...); anything else emits all five. Single-kind matters because each
    input_request replaces the previous one (PRD.md §8: at most one open
    question), so in an all-five run only the last widget is ever interactable.
    """

    requests = [
        {
            "type": "input_request",
            "field": "district",
            "prompt_bn": "আপনার জেলা কোনটি?",
            "input_kind": "dropdown",
            "options": [
                {"value": "rajshahi", "label_bn": "রাজশাহী"},
                {"value": "dhaka", "label_bn": "ঢাকা"},
                {"value": "rangpur", "label_bn": "রংপুর"},
                {"value": "khulna", "label_bn": "খুলনা"},
                {"value": "sylhet", "label_bn": "সিলেট"},
            ],
            "unit_options": None,
        },
        {
            "type": "input_request",
            "field": "soil_type",
            "prompt_bn": "আপনার জমির মাটি কী ধরনের?",
            "input_kind": "chips",
            "options": [
                {"value": "loam", "label_bn": "দোআঁশ"},
                {"value": "clay", "label_bn": "এঁটেল"},
                {"value": "sandy", "label_bn": "বেলে"},
            ],
            "unit_options": None,
        },
        {
            "type": "input_request",
            "field": "budget_bdt",
            "prompt_bn": "আপনার বাজেট কত টাকা?",
            "input_kind": "number",
            "options": None,
            "unit_options": None,
        },
        {
            "type": "input_request",
            "field": "area",
            "prompt_bn": "জমির পরিমাণ কত?",
            "input_kind": "number_unit",
            "options": None,
            "unit_options": ["bigha", "katha", "decimal", "acre"],
        },
        {
            "type": "input_request",
            "field": "name",
            "prompt_bn": "আপনার নাম কী?",
            "input_kind": "text",
            "options": None,
            "unit_options": None,
        },
    ]

    wanted = (payload.message or "").strip().lower()
    selected = [item for item in requests if item["field"].lower() == wanted]
    if selected:
        note = f"Widget harness — {selected[0]['input_kind']}."
    else:
        selected = requests
        note = "Widget harness — all kinds; only the last stays interactable."

    async def events() -> AsyncIterator[dict]:
        yield sse.token(note)
        for item in selected:
            await asyncio.sleep(0.2)
            yield item
        yield sse.done()

    return sse.sse_response(events(), request)
