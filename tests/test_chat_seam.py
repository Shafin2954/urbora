"""The agent↔API seam: /api/chat driving the agent loop.

`run_turn(session_id, farm_id, message)` is an async generator yielding wire
dicts, and it builds its own tool events through the redacting constructors.
Two things still have to hold at this boundary, and each has cost somebody a
night somewhere:

  1. **Nothing unmasked reaches the wire.** The loop redacts by construction,
     and `format_sse` masks anything that arrives unmasked anyway. The second
     layer is not paranoia: schemas.py declares that tool events carry RAW
     params, so any future producer that skips the constructors would leak
     bdapps credentials straight into the judge-facing trace panel.
  2. **A failure produces an honest `error` event**, not a stream that stops
     mid-sentence and looks like a dead network.

The fakes here yield contract-shaped events with visibly synthetic English
content — never Bangla farm advice, which would be invented data (CLAUDE.md
§2.2) sitting in the test suite waiting to be mistaken for real.
"""

import json

import pytest
from fastapi.testclient import TestClient

from backend.api import chat as chat_module
from backend.api import sse
from backend.api.main import app
from backend.schemas import ToolCallEvent, ToolResultEvent


def frames(body: str) -> list[dict]:
    """Parse an SSE response body into event dicts, ignoring heartbeats."""
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


# A bdapps-shaped tool payload: auth in the body, which is the whole reason
# redaction exists (NOTES.md #19).
LEAKY_PARAMS = {
    "applicationId": "APP_000123",
    "password": "9f8e7d6c5b4a39281706f5e4d3c2b1a0",
    "subscriberId": "tel:8801812345678",
    "amount": "2.00",
}


# --- 1. redaction at the edge -----------------------------------------------


def test_raw_tool_call_is_redacted_on_the_wire():
    """schemas.py says tool events carry RAW params. None may leave the process."""
    raw = ToolCallEvent(
        id="c1", name="charge", params=LEAKY_PARAMS, ts="2026-07-24T09:00:00+00:00"
    )
    payload = json.loads(sse.format_sse(sse.from_agent_event(raw))[len("data: ") :])

    assert payload["params"]["password"] == "***"
    assert payload["params"]["applicationId"] == "***"
    assert payload["params"]["subscriberId"] == "***678"
    # Untouched: masking a payment amount would blank a judge-relevant number.
    assert payload["params"]["amount"] == "2.00"
    # Paths are relative to the redacted field, matching what the constructors
    # report, so the trace panel reads the same whoever built the event.
    assert payload["redacted"] == ["applicationId", "password", "subscriberId"]
    assert payload["redacted"] == sse.tool_call("c1", "charge", LEAKY_PARAMS)["redacted"]


def test_raw_tool_result_is_redacted_on_the_wire():
    raw = ToolResultEvent(
        id="c1",
        name="charge",
        result_raw={"statusCode": "S1000", "password": "hunter2"},
        ts="2026-07-24T09:00:00+00:00",
    )
    payload = json.loads(sse.format_sse(sse.from_agent_event(raw))[len("data: ") :])
    assert payload["result_raw"]["password"] == "***"
    assert payload["result_raw"]["statusCode"] == "S1000"


def test_already_masked_events_are_not_masked_twice():
    """Re-masking is lossy for phones: '***678' has 3 digits left and becomes '***'.

    The loop's events arrive already masked, so the edge must be able to tell
    them from raw ones — that is what the `redacted` marker is for.
    """
    built = sse.tool_call("c1", "charge", LEAKY_PARAMS)
    assert built["params"]["subscriberId"] == "***678"

    payload = json.loads(sse.format_sse(built)[len("data: ") :])
    assert payload["params"]["subscriberId"] == "***678"


def test_non_trace_events_pass_through_untouched():
    """Only tool_call/tool_result are trace events; a token is not a payload."""
    payload = json.loads(sse.format_sse(sse.token("password=hunter2 "))[len("data: ") :])
    assert payload == {"type": "token", "text": "password=hunter2 "}


# --- 2. the route ------------------------------------------------------------


def fake_agent(events, record=None):
    """A stand-in for the loop, with its real signature and dict output."""

    async def run_turn(session_id, farm_id, message, client=None, language='bn'):
        if record is not None:
            record.append({"session_id": session_id, "farm_id": farm_id, "message": message, "language": language})
        for event in events:
            yield event

    return run_turn


def post(client, message, session_id="s1", farm_id=None):
    return client.post(
        "/api/chat",
        json={"session_id": session_id, "farm_id": farm_id, "message": message},
    )


def test_chat_streams_agent_events_and_redacts_the_trace(monkeypatch):
    events = [
        sse.token("Harness reply — not agronomy."),
        # Deliberately hand-built raw, bypassing the constructors, to prove the
        # edge still masks it.
        {
            "type": "tool_call",
            "id": "c1",
            "name": "charge",
            "params": LEAKY_PARAMS,
            "ts": "2026-07-24T09:00:00+00:00",
        },
        sse.done(10, 5, 0.001),
    ]
    monkeypatch.setattr(chat_module, "_load_agent", lambda: fake_agent(events))

    with TestClient(app) as client:
        body = post(client, "hello").text

    got = frames(body)
    assert [e["type"] for e in got] == ["token", "tool_call", "done"]
    assert got[1]["params"]["password"] == "***"
    assert got[1]["params"]["subscriberId"] == "***678"
    assert got[2]["usage"] == {"in_tokens": 10, "out_tokens": 5, "cost_usd": 0.001}
    # The raw password must not appear anywhere in the response, not just in
    # the field we happened to check.
    assert LEAKY_PARAMS["password"] not in body


def test_route_forwards_the_request_fields_unchanged(monkeypatch):
    """session_id and farm_id must reach the loop — the loop owns the history."""
    seen: list[dict] = []
    monkeypatch.setattr(
        chat_module, "_load_agent", lambda: fake_agent([sse.done()], seen)
    )

    with TestClient(app) as client:
        post(client, "কেমন আছেন", session_id="s7", farm_id="farm-1")

    assert seen == [{"session_id": "s7", "farm_id": "farm-1", "message": "কেমন আছেন", "language": "bn"}]


def test_a_missing_agent_degrades_honestly(monkeypatch):
    """No agent module: say so, don't emit something that looks like an answer."""
    monkeypatch.setattr(chat_module, "_load_agent", lambda: None)

    with TestClient(app) as client:
        got = frames(post(client, "hello").text)

    assert [e["type"] for e in got] == ["error", "done"]
    assert "run_turn" in got[0]["message"]


def test_a_failing_turn_reports_the_error_instead_of_truncating(monkeypatch):
    """A stream that just stops is indistinguishable from a dead network."""

    async def exploding(session_id, farm_id, message, client=None, language='bn'):
        yield sse.token("Harness reply — ")
        raise RuntimeError("provider refused the request")

    monkeypatch.setattr(chat_module, "_load_agent", lambda: exploding)

    with TestClient(app) as client:
        got = frames(post(client, "hello").text)

    assert [e["type"] for e in got] == ["token", "error", "done"]
    assert "provider refused the request" in got[1]["message"]


def test_a_failure_before_the_first_yield_is_still_reported(monkeypatch):
    """The real case: a missing OPENAI_API_KEY raises at client construction,
    which happens above the loop's own try block and escapes it entirely."""

    async def dead_on_arrival(session_id, farm_id, message, client=None, language='bn'):
        raise RuntimeError("Missing credentials")
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(chat_module, "_load_agent", lambda: dead_on_arrival)

    with TestClient(app) as client:
        got = frames(post(client, "hello").text)

    assert [e["type"] for e in got] == ["error", "done"]
    assert "Missing credentials" in got[0]["message"]
