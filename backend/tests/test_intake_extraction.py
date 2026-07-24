"""Tests for backend.agent.loop.extract_known_fields — the deterministic
intake pre-pass added to stop the agent re-asking fields the farmer already
stated (see loop.py's block above `extract_known_fields` for the rationale).

Also covers that `run_turn` actually injects the extraction note as a system
message ahead of the farmer's message, using the same scripted-client pattern
as test_loop_integration.py (no network).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import backend.memory.store as store
from backend.agent.config import AgentConfig
from backend.agent.llm_client import OpenAIClient, TurnStream
from backend.agent.loop import extract_known_fields, run_turn


# ── extract_known_fields: pure unit tests ──────────────────────────────────


def test_dense_opening_message_extracts_all_six_fields():
    text = (
        "আমার রংপুরে ২ বিঘা দোআঁশ জমি আছে, গভীর নলকূপ আছে, বাজেট ৪০০০০ টাকা। "
        "এই রবি মৌসুমে কী চাষ করব?"
    )
    found = extract_known_fields(text)
    assert found["district"] == "Rangpur"
    assert found["area"] == 2.0
    assert found["area_unit"] == "bigha"
    assert found["soil_type"] == "loam"
    assert found["water_source"] == "tubewell"
    assert found["budget_bdt"] == 40000.0
    assert found["season"] == "rabi"


def test_vague_message_extracts_nothing():
    assert extract_known_fields("আমি চাষ করতে চাই") == {}


def test_empty_and_none_safe():
    assert extract_known_fields("") == {}
    assert extract_known_fields("   ") == {}


def test_compound_soil_terms_beat_their_substrings():
    assert extract_known_fields("আমার জমি এঁটেল দোআঁশ")["soil_type"] == "clay_loam"
    assert extract_known_fields("আমার জমি বেলে দোআঁশ")["soil_type"] == "sandy_loam"
    assert extract_known_fields("আমার জমি এঁটেল মাটি")["soil_type"] == "clay"
    assert extract_known_fields("আমার জমি দোআঁশ মাটি")["soil_type"] == "loam"


def test_water_source_variants():
    assert extract_known_fields("গভীর নলকূপ আছে")["water_source"] == "tubewell"
    assert extract_known_fields("সেচ আছে")["water_source"] == "irrigated"
    assert extract_known_fields("খাল থেকে পানি")["water_source"] == "canal"
    assert extract_known_fields("বৃষ্টি নির্ভর জমি")["water_source"] == "rainfed"


def test_season_variants():
    assert extract_known_fields("আগামী রবি মৌসুমে")["season"] == "rabi"
    assert extract_known_fields("এখন খরিপ-২ মৌসুম")["season"] == "kharif2"
    assert extract_known_fields("kharif1 season")["season"] == "kharif1"


def test_area_english_unit_and_decimal_value():
    found = extract_known_fields("I have 1.5 bigha of land")
    assert found["area"] == 1.5
    assert found["area_unit"] == "bigha"


def test_budget_with_comma_thousands_separator():
    found = extract_known_fields("বাজেট ৪০,০০০ টাকা")
    assert found["budget_bdt"] == 40000.0


def test_budget_does_not_fire_on_area_number_alone():
    found = extract_known_fields("২ বিঘা জমি আছে")
    assert "budget_bdt" not in found


def test_district_english_alias_resolves_to_canonical():
    found = extract_known_fields("My land is in Bogra district")
    assert found["district"] == "Bogura"


def test_nothing_invented_only_detected_fields_present():
    # A message with only a district must not fabricate the other five keys.
    found = extract_known_fields("আমার বাড়ি রাজশাহীতে")
    assert found == {"district": "Rajshahi"}


# ── run_turn wiring: the note actually reaches the model as a system msg ───


def _chunk(content=None, tool_calls=None, finish_reason=None, usage=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def _usage(prompt=10, completion=2):
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                           prompt_tokens_details=None)


def _final_script(text):
    return [_chunk(content=text), _chunk(finish_reason="stop"), _chunk(usage=_usage())]


class _ScriptedClient(OpenAIClient):
    def __init__(self, scripts):
        super().__init__(AgentConfig(model="gpt-4o", api_key="x", max_iterations=5))
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
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "test_intake_extraction.db")


def test_run_turn_injects_extraction_note_for_dense_message(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_final_script("ঠিক আছে")])
    dense_message = (
        "আমার রংপুরে ২ বিঘা দোআঁশ জমি আছে, গভীর নলকূপ আছে, বাজেট ৪০০০০ টাকা। "
        "এই রবি মৌসুমে কী চাষ করব?"
    )

    _collect(run_turn(session_id="ix1", farm_id=None, message=dense_message, client=client))

    sent = client.messages_seen[0]
    system_notes = [m["content"] for m in sent if m["role"] == "system"]
    assert any("Deterministic extraction" in note for note in system_notes)
    extraction_note = next(n for n in system_notes if "Deterministic extraction" in n)
    payload = json.loads(extraction_note.splitlines()[-1])
    assert payload["district"] == "Rangpur"
    assert payload["season"] == "rabi"
    assert payload["budget_bdt"] == 40000.0
    # note must precede the farmer's own message in the sent list
    note_idx = sent.index({"role": "system", "content": extraction_note})
    user_idx = next(i for i, m in enumerate(sent) if m == {"role": "user", "content": dense_message})
    assert note_idx < user_idx


def test_run_turn_no_extraction_note_for_vague_message(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    client = _ScriptedClient([_final_script("কোন জেলায় আপনার জমি?")])

    _collect(run_turn(session_id="ix2", farm_id=None, message="আমি চাষ করতে চাই", client=client))

    sent = client.messages_seen[0]
    system_notes = [m["content"] for m in sent if m["role"] == "system"]
    assert not any("Deterministic extraction" in note for note in system_notes)
