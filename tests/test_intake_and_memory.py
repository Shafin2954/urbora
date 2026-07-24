"""Two judged behaviours that were wired but never fired.

1. **Intake widgets** (PRD §8 Tier0.1). The five `input_request` widgets have
   been in the UI since H2 and the event in the frozen contract since H1, but
   nothing ever emitted one — in the real flow they were unreachable. The
   `ask_farmer` tool is the missing half.

2. **Memory** (PRD §4). `get_farm`/`save_farm` existed and nothing called them,
   so a returning farmer was never actually recalled — which is the demo's
   opening twenty seconds (PLAN §5 step 1).

Both are asserted at the seam that matters: the event a browser receives, and
the messages the model is handed.
"""

import json

import pytest

from backend.agent.loop import _panel_event
from backend.agent.tools_spec import dispatch
from backend.tools.ask import DISTRICT_BN, ask_farmer, district_options


# --- the widget the farmer actually sees -------------------------------------


def test_district_options_are_filled_in_for_the_model():
    """64 hand-typed options is a transcription error waiting to happen, and the
    spellings must match what geocode and crop.db accept."""
    result = ask_farmer(
        field="district", prompt_bn="আপনার জেলা কোনটি?", input_kind="dropdown"
    )
    options = result["input_request"]["options"]
    assert len(options) == 64
    assert {"value": "Rajshahi", "label_bn": "রাজশাহী"} in options
    # Every district is Bangla-labelled — a farmer should not have to read
    # Latin script to find their own district.
    assert all(option["label_bn"] != option["value"] for option in options)


def test_every_district_has_a_bangla_name():
    from backend.tools.districts import DISTRICTS

    missing = sorted(set(DISTRICTS) - set(DISTRICT_BN))
    assert not missing, f"no Bangla label for: {missing}"


def test_bangla_labels_are_actually_bangla():
    """A Latin-script 'label_bn' would silently defeat the point."""
    for option in district_options():
        assert any("ঀ" <= ch <= "৿" for ch in option["label_bn"])


@pytest.mark.parametrize(
    "kind", ["chips", "dropdown", "number", "number_unit", "text"]
)
def test_all_five_widget_kinds_produce_a_valid_event(kind):
    """The UI implements exactly these five; the contract allows exactly these."""
    result = ask_farmer(
        field="soil_type",
        prompt_bn="মাটি কী ধরনের?",
        input_kind=kind,
        options=[{"value": "loam", "label_bn": "দোআঁশ"}],
    )
    event = _panel_event("ask_farmer", result)
    assert event is not None
    assert event.type == "input_request"
    assert event.input_kind == kind


def test_area_defaults_to_the_local_units_a_farmer_speaks():
    result = ask_farmer(
        field="area", prompt_bn="জমির পরিমাণ কত?", input_kind="number_unit"
    )
    assert result["input_request"]["unit_options"][:4] == [
        "bigha",
        "katha",
        "decimal",
        "acre",
    ]


def test_the_tool_tells_the_model_to_stop_after_asking():
    """Without this the model answers its own question and carries on, which
    defeats the entire point of asking."""
    result = ask_farmer(field="area", prompt_bn="কত?", input_kind="number")
    assert "End your turn" in result["note"]


# --- refusing a malformed widget before it reaches the wire ------------------


def test_an_invalid_widget_kind_is_refused_with_the_valid_list():
    result = ask_farmer(field="x", prompt_bn="?", input_kind="slider")
    assert "invalid input_kind" in result["error"]
    assert "number_unit" in result["detail"]
    assert _panel_event("ask_farmer", result) is None


def test_chips_without_options_are_refused():
    """An empty chip row is a question the farmer cannot answer by tapping."""
    result = ask_farmer(field="soil_type", prompt_bn="মাটি?", input_kind="chips")
    assert "needs options" in result["error"]


def test_an_empty_prompt_is_refused():
    result = ask_farmer(field="area", prompt_bn="   ", input_kind="number")
    assert "prompt_bn is required" in result["error"]


def test_options_are_dropped_for_kinds_that_cannot_show_them():
    result = ask_farmer(
        field="budget_bdt",
        prompt_bn="বাজেট কত?",
        input_kind="number",
        options=[{"value": "x", "label_bn": "য"}],
    )
    assert result["input_request"]["options"] is None


def test_the_tool_is_reachable_through_the_agent_dispatcher():
    result = dispatch(
        "ask_farmer",
        {"field": "district", "prompt_bn": "জেলা?", "input_kind": "dropdown"},
    )
    assert "input_request" in result


# --- memory: the returning farmer -------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch):
    import backend.memory.store as store_module

    monkeypatch.setattr(store_module, "_DB_PATH", tmp_path / "memory.db")
    return store_module


def collect(agen):
    import asyncio

    async def run():
        return [event async for event in agen]

    return asyncio.run(run())


def scripted_client(reply="ঠিক আছে"):
    """Reuses the fake-backend pattern from backend/tests/test_loop_integration."""
    from types import SimpleNamespace

    from backend.agent.config import AgentConfig
    from backend.agent.llm_client import OpenAIClient, TurnStream

    def chunk(content=None, finish_reason=None, usage=None):
        delta = SimpleNamespace(content=content, tool_calls=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(delta=delta, finish_reason=finish_reason)],
            usage=usage,
        )

    usage = SimpleNamespace(
        prompt_tokens=10, completion_tokens=2, prompt_tokens_details=None
    )
    script = [chunk(content=reply), chunk(finish_reason="stop"), chunk(usage=usage)]

    class Scripted(OpenAIClient):
        def __init__(self):
            super().__init__(AgentConfig(model="gpt-4o-mini", api_key="x"))
            self.seen: list[list[dict]] = []

        def stream(self, messages, system=None, tools=None):
            self.seen.append([dict(m) for m in messages])
            return TurnStream(
                _stream=iter(script),
                _model=self.config.model,
                _cost_fn=self.cost_from_usage,
            )

    return Scripted()


PROFILE = {
    "name": "করিম",
    "district": "Rajshahi",
    "area_local": {"value": 2, "unit": "bigha"},
    "soil_type": "clay_loam",
}


def test_a_remembered_farm_is_handed_to_the_model(store):
    from backend.agent.loop import run_turn

    store.save_farm("farm-1", PROFILE)
    client = scripted_client()
    collect(run_turn(session_id="s1", farm_id="farm-1", message="হ্যালো", client=client))

    system_notes = [m for m in client.seen[0] if m["role"] == "system"]
    assert system_notes, "the remembered farm never reached the model"
    note = system_notes[0]["content"]
    assert "করিম" in note and "Rajshahi" in note
    # It must read as memory the agent holds, not as words the farmer said.
    assert "do NOT re-ask" in note


def test_an_unknown_farm_injects_nothing(store):
    """Never fabricate a farm — a miss means the agent proceeds without context."""
    from backend.agent.loop import run_turn

    client = scripted_client()
    collect(run_turn(session_id="s2", farm_id="nobody", message="হ্যালো", client=client))
    assert not [m for m in client.seen[0] if m["role"] == "system"]


def test_the_profile_is_injected_once_not_every_turn(store):
    """After turn one the history already carries it; repeating burns tokens
    and drifts the context."""
    from backend.agent.loop import run_turn

    store.save_farm("farm-1", PROFILE)
    client = scripted_client()
    collect(run_turn(session_id="s3", farm_id="farm-1", message="এক", client=client))
    collect(run_turn(session_id="s3", farm_id="farm-1", message="দুই", client=client))

    second_turn = client.seen[1]
    assert len([m for m in second_turn if m["role"] == "system"]) == 1


def test_a_stored_profile_survives_a_restart(store):
    """SQLite, not a process dict — the demo opens on a farm remembered from
    a session that has already ended."""
    store.save_farm("farm-9", PROFILE)
    reloaded = store.get_farm("farm-9")
    assert reloaded == PROFILE
    assert json.dumps(reloaded, ensure_ascii=False)  # round-trips as JSON


# --- remembering, so that recall has something to recall ---------------------


def test_the_agent_can_store_a_farm_it_just_learned(store):
    from backend.tools.farm_memory import remember_farm

    result = remember_farm(farm_id="farm-2", name="করিম", district="Rajshahi")
    assert result["saved"] is True
    assert store.get_farm("farm-2") == {"name": "করিম", "district": "Rajshahi"}


def test_a_later_call_merges_and_does_not_erase(store):
    """Intake is incremental — a call carrying only a budget must not wipe the
    district learned three turns earlier."""
    from backend.tools.farm_memory import remember_farm

    remember_farm(farm_id="farm-3", district="Rajshahi", area=2, area_unit="bigha")
    remember_farm(farm_id="farm-3", budget_bdt=15000)

    profile = store.get_farm("farm-3")
    assert profile["district"] == "Rajshahi"
    assert profile["area"] == 2
    assert profile["budget_bdt"] == 15000


def test_unknown_fields_are_reported_not_silently_stored(store):
    from backend.tools.farm_memory import remember_farm

    result = remember_farm(farm_id="farm-4", district="Khulna", favourite_colour="green")
    assert result["ignored_fields"] == ["favourite_colour"]
    assert "favourite_colour" not in store.get_farm("farm-4")


def test_remembering_nothing_is_refused(store):
    from backend.tools.farm_memory import remember_farm

    assert "nothing to remember" in remember_farm(farm_id="farm-5")["error"]
    assert store.get_farm("farm-5") is None


def test_store_then_recall_across_sessions(store):
    """The full memory loop, which is the demo's opening twenty seconds."""
    from backend.agent.loop import run_turn
    from backend.tools.farm_memory import remember_farm

    remember_farm(farm_id="farm-6", name="করিম", district="Rajshahi", soil_type="clay_loam")

    client = scripted_client()
    collect(run_turn(session_id="brand-new", farm_id="farm-6", message="আবার এলাম", client=client))

    note = next(m["content"] for m in client.seen[0] if m["role"] == "system")
    assert "করিম" in note and "clay_loam" in note
