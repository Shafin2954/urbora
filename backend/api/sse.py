"""SSE wire format + stream plumbing.

Wire format decision (B, H0): every event goes out as a single `data:` line
holding one JSON object, and the discriminator lives *inside* that JSON as
`type` — exactly the shape docs/archive/hackathon/PLAN.md §2 specifies. We do NOT use the SSE
`event:` field. One channel, one handler, one switch on `payload.type` in the
client; adding a second naming system on the wire would only give us two places
to typo an event name.

Trace redaction (docs/NOTES.md #19) lives in redact.py and is applied *inside* the
`tool_call` / `tool_result` constructors below. That is deliberate: there is no
way to build one of those events without redacting, so no caller can forget.
Raw bdapps request bodies carry `password` and `applicationId`, and the trace
panel shows params verbatim — the two only coexist safely if masking is
structural rather than remembered.

A's agent loop, however, yields the *raw* pydantic event models by design
(schemas.py: "tool_call / tool_result carry RAW params & results — the emitter
(B) redacts"). Those never pass through the constructors, so `format_sse` is
the second, final choke point: nothing reaches the wire without going through
it, and it masks any trace event that has not already been masked.

It distinguishes the two by the `redacted` field, which only our constructors
add. That marker is load-bearing rather than cosmetic: redaction is NOT
idempotent for phone numbers — masking `***678` a second time yields `***`,
because it has three digits left — so "just redact everything again at the
edge" would quietly destroy the last-3-digits affordance that lets a human
confirm which SIM was charged.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

from . import config
from .redact import redact

# A comment line. Clients ignore it; it keeps idle connections from being
# reaped by proxies or a dozing phone radio.
HEARTBEAT = ": keep-alive\n\n"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


_TRACE_TYPES = {"tool_call": "params", "tool_result": "result_raw"}


def ensure_redacted(payload: dict) -> dict:
    """Mask a trace event that has not already been masked.

    Events built by the constructors below carry `redacted` and are returned
    untouched — re-masking them would degrade phone masks (module docstring).
    Everything else claiming to be a `tool_call` / `tool_result` is treated as
    raw, which is exactly what A's loop yields.
    """
    field = _TRACE_TYPES.get(payload.get("type", ""))
    if field is None or "redacted" in payload:
        return payload
    safe, redacted_paths = redact(payload.get(field))
    return {**payload, field: safe, "redacted": redacted_paths}


def format_sse(payload: dict) -> str:
    """Encode one event dict as an SSE frame.

    The last thing every event passes through, and therefore where the "no
    unredacted trace leaves the process" guarantee is actually enforced.

    `ensure_ascii=False` keeps Bangla readable on the wire instead of turning
    it into \\uXXXX soup — helps a lot when debugging with curl.
    Newlines inside the JSON would break the framing, so the separators are
    kept compact and the whole object stays on one line.
    """
    body = json.dumps(
        ensure_redacted(payload), ensure_ascii=False, separators=(",", ":"), default=str
    )
    return f"data: {body}\n\n"


def from_agent_event(event: Any) -> dict:
    """Convert one event from A's loop into a wire dict.

    A yields pydantic models from schemas.py; the dev harness and B's own
    routes yield plain dicts. Both are accepted, and neither is redacted here —
    `format_sse` does that for every event on one path, rather than this
    function doing it for some of them.
    """
    dump = getattr(event, "model_dump", None)
    return dump() if dump is not None else event


# --- event constructors (docs/archive/hackathon/PLAN.md §2 contract) -------------------------------
# Only the ones H0 needs. The rest land as their features do.


def token(text: str) -> dict:
    return {"type": "token", "text": text}


def tool_call(call_id: str, name: str, params: Any) -> dict:
    """A tool invocation, params redacted by construction.

    `redacted` lists the field paths that were masked. It is additive to the
    docs/archive/hackathon/PLAN.md §2 shape — A produces nothing here, the emitter builds the event —
    and it lets the trace panel show that masking was deliberate rather than
    leaving a judge wondering why a field says `***`.
    """
    safe_params, redacted_paths = redact(params)
    return {
        "type": "tool_call",
        "id": call_id,
        "name": name,
        "params": safe_params,
        "ts": now_iso(),
        "redacted": redacted_paths,
    }


def tool_result(call_id: str, name: str, result_raw: Any) -> dict:
    """A tool's raw result, redacted by construction. See tool_call."""
    safe_result, redacted_paths = redact(result_raw)
    return {
        "type": "tool_result",
        "id": call_id,
        "name": name,
        "result_raw": safe_result,
        "ts": now_iso(),
        "redacted": redacted_paths,
    }


def done(in_tokens: int = 0, out_tokens: int = 0, cost_usd: float = 0.0) -> dict:
    return {
        "type": "done",
        "usage": {
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "cost_usd": cost_usd,
        },
    }


def error(message: str) -> dict:
    return {"type": "error", "message": message}


# --- stream plumbing --------------------------------------------------------


async def _with_heartbeat(
    events: AsyncIterator[dict],
    request: Request,
    interval: float,
) -> AsyncIterator[str]:
    """Encode events, injecting a heartbeat whenever the source goes quiet.

    Also the place client disconnects are noticed: a farmer on a phone will
    lock the screen mid-plan, and we want the agent loop torn down rather than
    left burning tokens into a dead socket (docs/NOTES.md #5).
    """
    iterator = events.__aiter__()
    pending: asyncio.Task | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(iterator.__anext__())

            finished, _ = await asyncio.wait({pending}, timeout=interval)

            if not finished:
                if await request.is_disconnected():
                    break
                yield HEARTBEAT
                continue

            task, pending = pending, None
            try:
                payload = task.result()
            except StopAsyncIteration:
                break
            yield format_sse(payload)
    finally:
        if pending is not None:
            pending.cancel()
        aclose = getattr(events, "aclose", None)
        if aclose is not None:
            await aclose()


def sse_response(events: AsyncIterator[dict], request: Request) -> StreamingResponse:
    """Wrap an async iterator of event dicts in a streaming SSE response.

    The headers are the difference between a stream that arrives live and one
    that arrives all at once at the end:
      - no-cache / no-transform: stop intermediaries rewriting or caching it
      - X-Accel-Buffering: no    : stop nginx-style proxies buffering it
    """
    return StreamingResponse(
        _with_heartbeat(events, request, config.SSE_HEARTBEAT_SECONDS),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
