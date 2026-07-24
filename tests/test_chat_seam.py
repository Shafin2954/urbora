"""The A↔B seam: /api/chat driving A's agent loop.

A's `run_turn` is a *synchronous* generator taking a message history and
yielding *raw* pydantic events (LOG2 [04:45]). Three things must hold at that
boundary, and each has cost somebody a night somewhere:

  1. Raw `tool_call` / `tool_result` from A get redacted before the wire.
     A emits them unmasked on purpose (schemas.py says so), so if B's edge
     misses one, bdapps credentials land in the judge-facing trace panel.
  2. The blocking generator does not run on the event loop.
  3. A failure at the seam produces an honest `error` event, not a stream that
     stops mid-sentence and looks like a dead network.

The fake agents here yield contract-shaped events with visibly synthetic
English content — never Bangla farm advice, which would be invented data
(CLAUDE.md §2.2) sitting in the test suite waiting to be mistaken for real.
"""

import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient

from backend.api import chat as chat_module
from backend.api import sessions, sse
from backend.api.agent_bridge import stream_sync_generator
from backend.api.main import app
from backend.schemas import DoneEvent, ToolCallEvent, ToolResultEvent, TokenEvent, Usage


@pytest.fixture(autouse=True)
def clean_sessions():
    sessions.reset()
    yield
    sessions.reset()


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


def test_raw_agent_tool_call_is_redacted_on_the_wire():
    """A yields this unmasked by design; it must not leave the process that way."""
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


def test_raw_agent_tool_result_is_redacted_on_the_wire():
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

    So the edge must be able to tell a constructor-built event from a raw one.
    """
    built = sse.tool_call("c1", "charge", LEAKY_PARAMS)
    assert built["params"]["subscriberId"] == "***678"

    payload = json.loads(sse.format_sse(built)[len("data: ") :])
    assert payload["params"]["subscriberId"] == "***678"


def test_non_trace_events_pass_through_untouched():
    """Only tool_call/tool_result are trace events; a token is not a payload."""
    payload = json.loads(sse.format_sse(sse.token("password=hunter2 "))[len("data: ") :])
    assert payload == {"type": "token", "text": "password=hunter2 "}


# --- 2. the sync-to-async bridge --------------------------------------------


def test_bridge_yields_every_item_in_order():
    async def run():
        return [x async for x in stream_sync_generator(lambda: iter([1, 2, 3]))]

    assert asyncio.run(run()) == [1, 2, 3]


def test_bridge_runs_the_generator_off_the_event_loop():
    """The point of the bridge: A's blocking I/O must not stall the loop."""
    seen: list[str] = []

    def gen():
        seen.append(threading.current_thread().name)
        yield "x"

    async def run():
        async for _ in stream_sync_generator(gen):
            pass
        return threading.current_thread().name

    caller = asyncio.run(run())
    assert seen and seen[0] != caller


def test_bridge_reraises_generator_failures():
    """Including one raised before the first yield — e.g. a bad call signature."""

    def boom():
        raise TypeError("run_turn() got an unexpected keyword argument 'session_id'")
        yield  # pragma: no cover — makes this a generator function

    async def run():
        async for _ in stream_sync_generator(boom):
            pass

    with pytest.raises(TypeError, match="unexpected keyword"):
        asyncio.run(run())


def test_bridge_closes_the_generator_when_the_consumer_leaves():
    """A farmer locks their phone mid-plan; the turn must be torn down."""
    closed = threading.Event()

    def gen():
        try:
            for i in range(1000):
                yield i
        finally:
            closed.set()

    async def run():
        async for _ in stream_sync_generator(gen):
            break  # walk away after one event

    asyncio.run(run())
    assert closed.wait(timeout=5), "producer thread kept running after the consumer left"


# --- 3. the route ------------------------------------------------------------


def fake_agent(events, record=None):
    """Build a stand-in for A's run_turn with A's real signature."""

    def run_turn(messages, client=None, system=None):
        if record is not None:
            record.append(list(messages))
        for event in events:
            yield event
        messages.append({"role": "assistant", "content": "harness reply"})

    return run_turn


def post(client, message, session_id="s1", farm_id=None):
    return client.post(
        "/api/chat",
        json={"session_id": session_id, "farm_id": farm_id, "message": message},
    )


def test_chat_streams_agent_events_and_redacts_the_trace(monkeypatch):
    events = [
        TokenEvent(text="Harness reply — not agronomy."),
        ToolCallEvent(
            id="c1", name="charge", params=LEAKY_PARAMS, ts="2026-07-24T09:00:00+00:00"
        ),
        DoneEvent(usage=Usage(in_tokens=10, out_tokens=5, cost_usd=0.001)),
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


def test_history_accumulates_across_turns(monkeypatch):
    """A's loop is stateless; B holds the conversation (sessions.py)."""
    seen: list[list[dict]] = []
    monkeypatch.setattr(
        chat_module,
        "_load_agent",
        lambda: fake_agent([DoneEvent(usage=Usage(in_tokens=0, out_tokens=0, cost_usd=0.0))], seen),
    )

    with TestClient(app) as client:
        post(client, "first")
        post(client, "second")

    assert [m["content"] for m in seen[0]] == ["first"]
    # Second turn sees the first user message, A's appended assistant turn, then
    # the new message — in that order.
    assert [m["content"] for m in seen[1]] == ["first", "harness reply", "second"]


def test_separate_sessions_do_not_share_history(monkeypatch):
    seen: list[list[dict]] = []
    monkeypatch.setattr(
        chat_module,
        "_load_agent",
        lambda: fake_agent([DoneEvent(usage=Usage(in_tokens=0, out_tokens=0, cost_usd=0.0))], seen),
    )

    with TestClient(app) as client:
        post(client, "farmer one", session_id="s1")
        post(client, "farmer two", session_id="s2")

    assert [m["content"] for m in seen[1]] == ["farmer two"]


def test_a_broken_agent_degrades_honestly(monkeypatch):
    """No agent module: say so, don't emit something that looks like an answer."""
    monkeypatch.setattr(chat_module, "_load_agent", lambda: None)

    with TestClient(app) as client:
        got = frames(post(client, "hello").text)

    assert [e["type"] for e in got] == ["error", "done"]
    assert "run_turn" in got[0]["message"]


def test_a_failing_turn_reports_the_error_instead_of_truncating(monkeypatch):
    """A stream that just stops is indistinguishable from a dead network."""

    def exploding(messages, client=None, system=None):
        yield TokenEvent(text="Harness reply — ")
        raise RuntimeError("provider refused the request")

    monkeypatch.setattr(chat_module, "_load_agent", lambda: exploding)

    with TestClient(app) as client:
        got = frames(post(client, "hello").text)

    assert [e["type"] for e in got] == ["token", "error", "done"]
    assert "provider refused the request" in got[1]["message"]
