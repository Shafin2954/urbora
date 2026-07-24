"""Tests for the streamed-token digit normalization in backend.agent.loop.

CLAUDE.md rule 10: numerals reaching the client are always Western, even
inside Bangla prose. The system prompt already said so and the model does
not reliably comply (same class of bug as ask_farmer not firing — see
test_intake_extraction.py), so loop.py enforces it deterministically at the
point each streamed chunk is turned into a TokenEvent, using the same
`_bn_to_western_digits` translation table the intake extractor uses.

These tests exercise the real `run_turn` streaming path (scripted client, no
network — same pattern as test_loop_integration.py) rather than calling the
translation helper directly, because the risk this code guards against is
specifically about STREAMING: a number split across chunk boundaries must
still come out fully Western once the client concatenates the tokens.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import backend.memory.store as store
from backend.agent.config import AgentConfig
from backend.agent.llm_client import OpenAIClient, TurnStream
from backend.agent.loop import _bn_to_western_digits, run_turn


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


def _streamed_text_script(*content_pieces):
    """A script that streams `content_pieces` as SEPARATE chunks — the whole
    point is that no single chunk sees the full text, mirroring how a real
    OpenAI stream can split a number across token boundaries."""
    chunks = [_chunk(content=piece) for piece in content_pieces]
    chunks.append(_chunk(finish_reason="stop"))
    chunks.append(_chunk(usage=_usage()))
    return chunks


class _ScriptedClient(OpenAIClient):
    def __init__(self, scripts):
        super().__init__(AgentConfig(model="gpt-4o", api_key="x", max_iterations=5))
        self._scripts = list(scripts)
        self._calls = 0

    def stream(self, messages, system=None, tools=None):
        chunks = self._scripts[self._calls]
        self._calls += 1
        return TurnStream(_stream=iter(chunks), _model=self.config.model,
                          _cost_fn=self.cost_from_usage)


def _collect(async_gen):
    async def _run():
        return [item async for item in async_gen]
    return asyncio.run(_run())


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "test_digit_normalization.db")


def _joined_tokens(events):
    return "".join(e["text"] for e in events if e["type"] == "token")


# ── the translation helper itself ───────────────────────────────────────────


def test_translate_helper_converts_digits_only():
    assert _bn_to_western_digits("স্কোর: ৮২.৬৪") == "স্কোর: 82.64"


def test_translate_helper_leaves_pure_bangla_prose_untouched():
    text = "আপনার জমির জেলা কোনটি?"
    assert _bn_to_western_digits(text) == text


# ── streamed end-to-end through run_turn ───────────────────────────────────


def test_composite_score_digits_are_western_in_streamed_output(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_streamed_text_script("সামগ্রিক স্কোর: ৮২.৬৪")])

    events = _collect(run_turn(session_id="dn1", farm_id=None, message="hi", client=client))

    assert _joined_tokens(events) == "সামগ্রিক স্কোর: 82.64"


def test_number_split_across_chunk_boundary_still_fully_western(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    # "৮২.৬৪" split mid-number across three separate streamed chunks.
    client = _ScriptedClient([_streamed_text_script("লাভ: ৳৮", "২.৬", "৪ টাকা")])

    events = _collect(run_turn(session_id="dn2", farm_id=None, message="hi", client=client))

    assert _joined_tokens(events) == "লাভ: ৳82.64 টাকা"


def test_date_digits_converted_to_western(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_streamed_text_script("বপনের তারিখ: ২০২৬-১১-০৮")])

    events = _collect(run_turn(session_id="dn3", farm_id=None, message="hi", client=client))

    assert _joined_tokens(events) == "বপনের তারিখ: 2026-11-08"


def test_pure_bangla_prose_with_no_digits_is_unchanged(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    text = "আপনার জমির তথ্য অনুযায়ী পরিকল্পনা তৈরি হচ্ছে।"
    client = _ScriptedClient([_streamed_text_script(text)])

    events = _collect(run_turn(session_id="dn4", farm_id=None, message="hi", client=client))

    assert _joined_tokens(events) == text


def test_western_digits_pass_through_unchanged(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_streamed_text_script("2 বিঘা, 40000 টাকা")])

    events = _collect(run_turn(session_id="dn5", farm_id=None, message="hi", client=client))

    assert _joined_tokens(events) == "2 বিঘা, 40000 টাকা"


def test_tool_call_params_are_not_touched_by_digit_normalization(tmp_path, monkeypatch):
    """Normalization must be scoped to the narration token stream only — tool
    params/results (already Western per rule 10, produced server-side) must
    reach the client byte-for-byte as the model/tool emitted them."""
    _use_temp_db(tmp_path, monkeypatch)
    import json
    args = json.dumps({"note": "৮২ অপরিবর্তিত থাকা উচিত"}, ensure_ascii=False)
    scripts = [
        [
            _chunk(tool_calls=[_tc(0, id="call_1", name="no_such_tool", args=args)]),
            _chunk(finish_reason="tool_calls"),
            _chunk(usage=_usage(50, 10)),
        ],
        _streamed_text_script("সম্পন্ন"),
    ]
    client = _ScriptedClient(scripts)

    events = _collect(run_turn(session_id="dn6", farm_id=None, message="hi", client=client))

    tool_calls = [e for e in events if e["type"] == "tool_call"]
    assert tool_calls[0]["params"]["note"] == "৮২ অপরিবর্তিত থাকা উচিত"
