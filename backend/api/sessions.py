"""In-process chat sessions (B owns sessions, PLAN.md §1).

A's `run_turn(messages, ...)` is stateless: it takes the conversation history,
appends the assistant and tool-result turns to it in place, and returns. Some-
body has to hold that list between HTTP requests, and on B's side of the seam
that is here.

Scope, stated plainly so nobody mistakes this for the memory feature: this is a
dictionary in one process. It is lost on restart and it is not shared between
workers. Durable memory — farm profiles, resumable conversations, alerts — is
A's `backend/memory/` at H9–H12, and when it lands this becomes a cache in
front of it rather than the only copy.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    session_id: str
    farm_id: str | None = None
    # Native provider message dicts, owned by A's loop once handed over.
    messages: list[dict[str, Any]] = field(default_factory=list)
    # One turn at a time per session. A farmer on a laggy phone will tap send
    # twice, and two turns appending to one history concurrently would
    # interleave tool results into the wrong assistant message — which the
    # provider rejects, after the tokens have been paid for.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_SESSIONS: dict[str, Session] = {}


def get_session(session_id: str, farm_id: str | None = None) -> Session:
    """Fetch or create a session, recording the farm it is about."""
    session = _SESSIONS.get(session_id)
    if session is None:
        session = Session(session_id=session_id, farm_id=farm_id)
        _SESSIONS[session_id] = session
    elif farm_id is not None:
        # A farmer can pick a different farm mid-session; last one named wins.
        session.farm_id = farm_id
    return session


def reset(session_id: str | None = None) -> None:
    """Drop one session or all of them. Used by tests and the dev harness."""
    if session_id is None:
        _SESSIONS.clear()
    else:
        _SESSIONS.pop(session_id, None)
