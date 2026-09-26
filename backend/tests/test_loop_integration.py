"""Integration tests for the real `backend.agent.loop.run_turn` entrypoint —
the exact async(session_id, farm_id, message) -> AsyncIterator[dict] contract
`backend/api/chat.py` calls. No network: a scripted fake ChatBackend replays
canned OpenAI-shaped stream chunks (same pattern as test_llm_backend.py).

This is what proves the earlier "live verified" claim held for a hand-rolled
script calling the sync engine directly, but NOT for B's actual API contract —
the bug this file exists to catch and pin down.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import backend.memory.store as store
from backend.agent.config import AgentConfig
from backend.agent.llm_client import OpenAIClient, TurnStream
from backend.agent.loop import run_turn


def _chunk(content=None, tool_calls=None, finish_reason=None, usage=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def _tc(index, id=None, name=None, args=None):
    fn = SimpleNamespace(name=name, arguments=args)
    return SimpleNamespace(index=index, id=id, function=fn)


def _usage(prompt=10, completion=2):
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                           prompt_tokens_details=None)


def _final_script(text):
    return [_chunk(content=text), _chunk(finish_reason="stop"), _chunk(usage=_usage())]


def _tool_script(tool_name, args_json):
    return [
        _chunk(tool_calls=[_tc(0, id="call_1", name=tool_name, args=args_json)]),
        _chunk(finish_reason="tool_calls"),
        _chunk(usage=_usage(50, 10)),
    ]


class _ScriptedClient(OpenAIClient):
    """A ChatBackend whose .stream() replays canned scripts instead of calling
    OpenAI — one script (list of fake chunks) per .stream() invocation."""

    def __init__(self, scripts):
        super().__init__(AgentConfig(model="gpt-4o-mini", api_key="x", max_iterations=5))
        self._scripts = list(scripts)
        self._calls = 0
        self.messages_seen = []

    def stream(self, messages, system=None, tools=None):
        self.messages_seen.append(list(messages))
        chunks = self._scripts[self._calls]
        self._calls += 1
        return TurnStream(_stream=iter(chunks), _model=self.config.model,
                          _cost_fn=self.cost_from_usage)


def _collect(async_gen):
    async def _run():
        return [item async for item in async_gen]
    return asyncio.run(_run())


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "test_loop.db")


def test_run_turn_matches_chat_py_contract_shape():
    import inspect
    sig = inspect.signature(run_turn)
    # `language` is additive with a default, so chat.py may pass it or not.
    assert list(sig.parameters) == ["session_id", "farm_id", "message", "client", "language", "channel"]
    assert sig.parameters["language"].default == "bn"  # Bangla-first, CLAUDE.md rule 10
    assert inspect.isasyncgenfunction(run_turn)


def test_run_turn_plain_text_yields_dicts_and_persists_session(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_final_script("স্বাগতম")])

    events = _collect(run_turn(session_id="s1", farm_id=None, message="হ্যালো", client=client))

    assert all(isinstance(e, dict) for e in events)  # exactly what chat.py forwards to sse_response
    assert any(e["type"] == "token" and e["text"] == "স্বাগতম" for e in events)
    assert events[-1]["type"] == "done"
    assert events[-1]["usage"]["in_tokens"] == 10

    saved = store.get_session_messages("s1")
    assert saved[0] == {"role": "user", "content": "হ্যালো"}
    assert saved[-1]["role"] == "assistant"


def test_run_turn_second_message_resumes_stored_history(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client1 = _ScriptedClient([_final_script("first reply")])
    _collect(run_turn(session_id="s2", farm_id=None, message="turn one", client=client1))

    client2 = _ScriptedClient([_final_script("second reply")])
    _collect(run_turn(session_id="s2", farm_id=None, message="turn two", client=client2))

    saved = store.get_session_messages("s2")
    user_msgs = [m["content"] for m in saved if m.get("role") == "user"]
    assert user_msgs == ["turn one", "turn two"]


def test_run_turn_tool_call_goes_through_redacting_constructors(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    secret_args = json.dumps({"password": "supersecret123", "note": "ok"})
    client = _ScriptedClient([
        _tool_script("no_such_tool", secret_args),
        _final_script("done"),
    ])

    events = _collect(run_turn(session_id="s3", farm_id=None, message="hi", client=client))

    tool_calls = [e for e in events if e["type"] == "tool_call"]
    assert len(tool_calls) == 1
    tc = tool_calls[0]
    # Redacted BY CONSTRUCTION via sse.tool_call — never a raw secret on the wire.
    assert tc["params"]["password"] == "***"
    assert tc["params"]["note"] == "ok"
    assert tc["redacted"], "redacted-paths list must be populated, not silently empty"

    tool_results = [e for e in events if e["type"] == "tool_result"]
    assert len(tool_results) == 1  # dispatch() degrades unknown tools safely, no crash


def test_run_turn_farm_id_none_is_accepted_without_error(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_final_script("ok")])
    events = _collect(run_turn(session_id="s4", farm_id=None, message="hi", client=client))
    assert not any(e["type"] == "error" for e in events)


def test_run_turn_injects_authoritative_farm_id_for_a_fresh_session(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_final_script("ok")])

    _collect(run_turn(
        session_id="s5", farm_id="demo-rajshahi", message="hi", client=client,
    ))

    system_notes = [m["content"] for m in client.messages_seen[0] if m["role"] == "system"]
    assert any("Authoritative farm_id" in note and "demo-rajshahi" in note for note in system_notes)


def test_calendar_call_is_preceded_by_visible_kb_retrieval(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([
        _tool_script("season_plan", json.dumps({
            "farm_id": "farm-1", "crop": "mustard", "start_date": "2026-10-30",
        })),
        _final_script("done"),
    ])

    events = _collect(run_turn(session_id="s6", farm_id="farm-1", message="plan", client=client))

    calls = [event["name"] for event in events if event["type"] == "tool_call"]
    assert calls == ["rag_query", "season_plan"]
    calendar = next(event for event in events if event["type"] == "tool_result" and event["name"] == "season_plan")
    assert calendar["result_raw"]["kb_evidence"]
