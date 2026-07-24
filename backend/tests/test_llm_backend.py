"""Offline tests for the OpenAI ChatBackend: tool translation, cost math, and
streaming parse (text deltas + tool-call accumulation) via a fake stream — no
network, no key.
"""

from types import SimpleNamespace

from backend.agent.config import AgentConfig
from backend.agent.llm_client import (
    NormToolCall,
    OpenAIClient,
    TurnStream,
    to_openai_tools,
)


def _client() -> OpenAIClient:
    # api_key None is fine — we never call the network in these tests.
    return OpenAIClient(AgentConfig(model="gpt-4o-mini", api_key="x"))


def test_tool_translation_to_openai_shape():
    defs = [{"name": "geocode", "description": "d",
             "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}}}]
    out = to_openai_tools(defs)
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "geocode"
    assert out[0]["function"]["parameters"]["properties"]["name"]["type"] == "string"


def test_cost_from_usage_splits_cached_input():
    c = _client()
    usage = SimpleNamespace(
        prompt_tokens=9200,
        completion_tokens=350,
        prompt_tokens_details=SimpleNamespace(cached_tokens=8000),
    )
    r = c.cost_from_usage(usage)
    assert r["in_tokens"] == 9200
    assert r["out_tokens"] == 350
    # fresh 1200 @0.15 + cached 8000 @0.075 + out 350 @0.60, per 1M
    expected = 1200/1e6*0.15 + 8000/1e6*0.15*0.5 + 350/1e6*0.60
    assert abs(r["cost_usd"] - round(expected, 6)) < 1e-9


def test_unknown_model_costs_zero_but_counts_tokens():
    c = OpenAIClient(AgentConfig(model="some-future-model", api_key="x"))
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_tokens_details=None)
    r = c.cost_from_usage(usage)
    assert r == {"in_tokens": 100, "out_tokens": 50, "cost_usd": 0.0}


def test_tool_result_message_shape():
    c = _client()
    m = c.tool_result_message("call_123", '{"ok": true}', is_error=False)
    assert m == {"role": "tool", "tool_call_id": "call_123", "content": '{"ok": true}'}


# ── fake stream chunks mimicking OpenAI's streaming shape ────────────────────
def _chunk(content=None, tool_calls=None, finish_reason=None, usage=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def _tc(index, id=None, name=None, args=None):
    fn = SimpleNamespace(name=name, arguments=args)
    return SimpleNamespace(index=index, id=id, function=fn)


def test_turnstream_parses_text_then_final():
    chunks = [
        _chunk(content="Hello "),
        _chunk(content="world"),
        _chunk(finish_reason="stop"),
        _chunk(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2,
                                     prompt_tokens_details=None)),
    ]
    c = _client()
    s = TurnStream(_stream=iter(chunks), _model="gpt-4o-mini", _cost_fn=c.cost_from_usage)
    with s:
        text = "".join(list(s))
    res = s.result()
    assert text == "Hello world"
    assert res.text == "Hello world"
    assert res.finish_reason == "stop"
    assert res.tool_calls == []
    assert res.usage["in_tokens"] == 10


def test_turnstream_accumulates_streamed_tool_call():
    # tool call args arrive split across chunks, like the real API
    chunks = [
        _chunk(tool_calls=[_tc(0, id="call_1", name="get_forecast", args='{"lat":24.3')]),
        _chunk(tool_calls=[_tc(0, args='7,"lon":88.6}')]),
        _chunk(finish_reason="tool_calls"),
        _chunk(usage=SimpleNamespace(prompt_tokens=20, completion_tokens=8,
                                     prompt_tokens_details=None)),
    ]
    c = _client()
    s = TurnStream(_stream=iter(chunks), _model="gpt-4o-mini", _cost_fn=c.cost_from_usage)
    with s:
        list(s)
    res = s.result()
    assert res.finish_reason == "tool_calls"
    assert len(res.tool_calls) == 1
    tc0: NormToolCall = res.tool_calls[0]
    assert tc0.id == "call_1"
    assert tc0.name == "get_forecast"
    assert tc0.args == {"lat": 24.37, "lon": 88.6}
    # assistant message carries the native tool_calls for history round-trip
    assert res.assistant_message["tool_calls"][0]["function"]["name"] == "get_forecast"
