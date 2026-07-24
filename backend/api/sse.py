"""SSE wire format + stream plumbing.

Wire format decision (B, H0): every event goes out as a single `data:` line
holding one JSON object, and the discriminator lives *inside* that JSON as
`type` — exactly the shape PLAN.md §2 specifies. We do NOT use the SSE
`event:` field. One channel, one handler, one switch on `payload.type` in the
client; adding a second naming system on the wire would only give us two places
to typo an event name.

NOT YET IMPLEMENTED HERE: the redacting trace emitter (PLAN.md H1-H3,
NOTES.md #19). `tool_call` / `tool_result` payloads carry raw bdapps request
bodies, which contain `password` and `applicationId`. Nothing may emit those
two event types until the redactor exists and its unit test passes. The
constructors below deliberately do not pretend to redact — a no-op redactor
would be worse than none, because it would look safe.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import StreamingResponse

from . import config

# A comment line. Clients ignore it; it keeps idle connections from being
# reaped by proxies or a dozing phone radio.
HEARTBEAT = ": keep-alive\n\n"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def format_sse(payload: dict) -> str:
    """Encode one event dict as an SSE frame.

    `ensure_ascii=False` keeps Bangla readable on the wire instead of turning
    it into \\uXXXX soup — helps a lot when debugging with curl.
    Newlines inside the JSON would break the framing, so the separators are
    kept compact and the whole object stays on one line.
    """
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"data: {body}\n\n"


# --- event constructors (PLAN.md §2 contract) -------------------------------
# Only the ones H0 needs. The rest land as their features do.


def token(text: str) -> dict:
    return {"type": "token", "text": text}


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
    left burning tokens into a dead socket (NOTES.md #5).
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
