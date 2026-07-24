"""AgriSense API — FastAPI skeleton.

H0-H1 scope (PLAN.md §3): the app, CORS, and a hello-world SSE endpoint that
proves browser -> stream plumbing works. Real routes (/api/chat, /api/farms,
/api/plan, /api/finance/recompute, /api/checkout) land in later blocks against
the PLAN.md §2 contract.

Run from the repo root:
    .venv/Scripts/python -m uvicorn backend.api.main:app --reload --port 8000
"""

import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import config, sse
from .chat import router as chat_router

app = FastAPI(
    title="AgriSense API",
    version="0.1.0",
    description="Bangla-first farm planning agent. B-owned: api/finance/payments.",
)

# See config.CORS_ORIGINS: dev goes through the Vite proxy and needs none of
# this, but direct :8000 access (curl, phone on the LAN) does.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)


@app.get("/api/health")
async def health() -> dict:
    """Liveness probe. Also what the frontend pings to show the API dot."""
    return {"status": "ok", "service": "agrisense-api", "ts": sse.now_iso()}


# --- hello-world SSE --------------------------------------------------------

# A fixed script of contract-shaped events. This is PLUMBING, not content:
# there is no agronomy in here and there must never be. When /api/chat lands
# this endpoint stays as a transport self-test we can curl at 3am to answer
# "is it the stream or is it the agent?" in five seconds.
_SELFTEST_SCRIPT: list[tuple[float, dict]] = [
    (0.0, sse.token("SSE self-test: ")),
    # Bangla + Western numerals through the pipe on purpose. If encoding or
    # framing is going to mangle Bengali (CLAUDE.md §2.10, NOTES.md #17), we
    # find out at H0 with a 3-line fix, not at H14 on a rendered plan.
    (0.4, sse.token("বাংলা ঠিকমতো আসছে ")),
    (0.4, sse.token("(1234567890). ")),
    (0.4, sse.token("Stream is live.")),
    (0.4, sse.done()),
]


async def _selftest_events() -> AsyncIterator[dict]:
    for delay, event in _SELFTEST_SCRIPT:
        # Deliberate pacing: instant events can't tell a working stream apart
        # from a buffered one that flushed at the end. Visible arrival is the
        # whole point of the test.
        if delay:
            await asyncio.sleep(delay)
        yield event


@app.post("/api/hello/stream")
async def hello_stream_post(request: Request):
    """Same transport the real /api/chat will use: POST -> SSE.

    EventSource cannot POST, so the browser client is fetch + a streaming body
    reader. Proving that path at H0 is the point of this endpoint — building
    the frontend on EventSource would mean rewriting the client the day the
    real contract (POST /api/chat with a JSON body) arrives.
    """
    return sse.sse_response(_selftest_events(), request)


@app.get("/api/hello/stream")
async def hello_stream_get(request: Request):
    """GET twin of the above, for curl and EventSource smoke tests."""
    return sse.sse_response(_selftest_events(), request)
