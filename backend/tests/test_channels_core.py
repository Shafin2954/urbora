"""Channel core: identity hashing, SMS segment rules, summary, adapter."""

from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest

from backend.channels import identity, sms_text
from backend.channels.adapter import Menu, menu_from_input_request, run_channel_turn
from backend.memory import store


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "channels.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")


# --- identity -----------------------------------------------------------------

def test_same_farmer_however_the_number_is_typed():
    ids = {identity.farm_id_for(n) for n in ("01812345678", "+8801812345678", "8801812-345678", "1812345678")}
    assert len(ids) == 1


def test_farm_id_never_contains_the_number():
    fid = identity.farm_id_for("01812345678")
    assert "1812345678" not in fid and fid.startswith("ph-")


def test_salt_changes_the_id(monkeypatch):
    a = identity.farm_id_for("01812345678")
    monkeypatch.setenv("CHANNEL_ID_SALT", "other")
    assert identity.farm_id_for("01812345678") != a


def test_invalid_number_is_refused_not_fixed():
    with pytest.raises(identity.InvalidMsisdnError):
        identity.farm_id_for("12345")


def test_voice_calls_get_their_own_session_but_share_the_farm():
    a = identity.session_id_for("01812345678", "voice", stamp="call-1")
    b = identity.session_id_for("01812345678", "voice", stamp="call-2")
    assert a != b


# --- SMS segment rules ----------------------------------------------------------

def test_ascii_is_gsm7_and_bangla_is_ucs2():
    assert sms_text.encoding("Hello 123") == "gsm7"
    assert sms_text.encoding("ধান") == "ucs2"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("a" * 160, 1), ("a" * 161, 2), ("a" * 306, 2), ("a" * 307, 3),
        ("ক" * 70, 1), ("ক" * 71, 2), ("ক" * 134, 2), ("ক" * 135, 3),
        ("", 0),
    ],
)
def test_segment_boundaries(text, expected):
    assert sms_text.segments(text) == expected


def test_gsm_extension_chars_cost_two():
    assert sms_text.segments("€" * 80) == 1
    assert sms_text.segments("€" * 81) == 2


def test_fit_trims_to_budget_and_marks_the_cut():
    long = "\n".join(["বোরো ধানের জন্য সার দিন আজই"] * 20)
    out = sms_text.fit(long, max_parts=2)
    assert sms_text.segments(out) <= 2 and out.endswith("…")


def test_fit_leaves_short_text_alone():
    assert sms_text.fit("ধান", 1) == "ধান"


# --- summary: numbers only from tool payloads -----------------------------------

def _plan():
    prov = {"value": None, "source_type": "kb", "source_id": "x", "source_title": "x",
            "locator": "x", "retrieved_at": "2026-09-27T00:00:00Z", "confidence": "medium"}
    return {"farm_id": "f", "crop": "boro_rice", "tasks": [
        {"date": "2026-09-01", "task": "পুরনো কাজ", "category": "sowing", "details": "", "provenance": prov},
        {"date": "2026-12-10", "task": "বোরো চারা রোপণ", "category": "sowing", "details": "", "provenance": prov},
        {"date": "2026-12-25", "task": "ইউরিয়া প্রথম কিস্তি", "category": "fertilizer", "details": "", "provenance": prov},
    ]}


def _finance(cost=45210.4, revenue=98000, profit=52789.6):
    scen = {"items": [], "total_cost": cost, "expected_yield_kg": 1, "price_per_kg": 1,
            "revenue": revenue, "net_profit": profit, "roi_pct": 1}
    return {"scenarios": {"conservative": scen, "base": scen, "optimistic": scen},
            "breakeven_yield_kg": 1, "breakeven_price_bdt": 1, "assumptions": []}


def test_summary_quotes_tool_numbers_exactly():
    out = sms_text.plan_summary_sms("Brand", _plan(), _finance(), today=date(2026, 11, 1))
    assert "৳45,210" in out and "৳98,000" in out and "৳52,790" in out
    assert "10/12 বোরো চারা রোপণ" in out
    assert "পুরনো কাজ" not in out  # past tasks are skipped
    assert sms_text.segments(out) <= 3


def test_summary_labels_a_ceiling_when_costs_are_incomplete():
    out = sms_text.plan_summary_sms("B", None, _finance(), crop="mustard", cost_complete=False)
    assert "সর্বোচ্চ লাভ (সব খরচ ধরা হয়নি) ৳52,790" in out


def test_summary_is_none_with_nothing_sourced():
    assert sms_text.plan_summary_sms("B", None, None) is None


# --- menus ----------------------------------------------------------------------

def test_question_is_not_shown_twice_when_the_agent_already_asked_it():
    from backend.channels.adapter import ChannelReply
    r = ChannelReply("s", "f", "***1", text="আপনার জেলা কোনটি?",
                     menu=Menu("district", "আপনার জেলা কোনটি? (জেলার নাম লিখুন)", [], free_entry=True))
    assert r.display_text() == "আপনার জেলা কোনটি?\n(জেলার নাম লিখুন)"
    r2 = ChannelReply("s", "f", "***1", text="ঠিক আছে।", menu=Menu("soil_type", "মাটি কেমন?", [("loam", "দোআঁশ")]))
    assert r2.display_text() == "ঠিক আছে।\nমাটি কেমন?\n1. দোআঁশ"


def test_chips_become_numbered_options_and_digits_map_back():
    menu = menu_from_input_request({"field": "soil_type", "prompt_bn": "মাটি কেমন?", "input_kind": "chips",
                                    "options": [{"value": "loam", "label_bn": "দোআঁশ"},
                                                {"value": "clay", "label_bn": "এঁটেল"}]})
    assert menu.render() == "মাটি কেমন?\n1. দোআঁশ\n2. এঁটেল"
    assert menu.resolve("2") == "এঁটেল"
    assert menu.resolve("9") == "9"
    assert menu.resolve("বেলে") == "বেলে"


def test_district_dropdown_becomes_free_entry():
    menu = menu_from_input_request({"field": "district", "prompt_bn": "জেলা?", "input_kind": "dropdown",
                                    "options": [{"value": "Rajshahi", "label_bn": "রাজশাহী"}] * 64})
    assert menu.free_entry and not menu.options


def test_menu_round_trips_through_dict():
    m = Menu("season", "মৌসুম?", [("rabi", "রবি")])
    assert Menu.from_dict(json.loads(json.dumps(m.to_dict()))).resolve("1") == "রবি"


# --- adapter ----------------------------------------------------------------------

def _fake_run_turn(script):
    seen = {}

    async def fake(session_id, farm_id, message, client=None, language="bn", channel="web",
                   context_note=None):
        seen.update(session_id=session_id, farm_id=farm_id, message=message, channel=channel)
        for ev in script:
            yield ev
    return fake, seen


def test_adapter_collects_reply_menu_and_persists_redacted_trace(monkeypatch):
    from backend.agent import loop
    from backend.api import sse

    script = [
        sse.tool_call("c1", "geocode", {"name": "Rajshahi", "phone": "01812345678"}),
        sse.tool_result("c1", "geocode", {"ok": True}),
        sse.token("[[CHAT_TITLE: রাজশাহী]] আপনার মাটি কেমন?"),
        {"type": "input_request", "field": "soil_type", "prompt_bn": "মাটি?", "input_kind": "chips",
         "options": [{"value": "loam", "label_bn": "দোআঁশ"}], "unit_options": None},
        sse.done(10, 5, 0.001),
    ]
    fake, seen = _fake_run_turn(script)
    monkeypatch.setattr(loop, "run_turn", fake)

    reply = asyncio.run(run_channel_turn("+8801812345678", "কী চাষ করব?", "sms"))
    assert seen["channel"] == "sms" and seen["farm_id"] == reply.farm_id
    assert reply.text == "আপনার মাটি কেমন?"
    assert reply.display_text().endswith("1. দোআঁশ")
    assert reply.masked == "***678"

    turns = store.get_channel_turns(reply.session_id)
    assert len(turns) == 1
    blob = json.dumps(turns[0]["events"], ensure_ascii=False)
    assert "01812345678" not in blob  # the phone param was redacted by sse.tool_call
    assert store.get_contact(reply.farm_id)["msisdn"] == "01812345678"

    # The next SMS "1" reaches the agent as the option's label.
    fake2, seen2 = _fake_run_turn([sse.done()])
    monkeypatch.setattr(loop, "run_turn", fake2)
    asyncio.run(run_channel_turn("01812345678", "1", "sms"))
    assert seen2["message"] == "দোআঁশ"


def test_adapter_apologises_in_bangla_when_the_agent_fails(monkeypatch):
    from backend.agent import loop

    async def broken(*a, **k):
        raise RuntimeError("no key")
        yield  # pragma: no cover

    monkeypatch.setattr(loop, "run_turn", broken)
    reply = asyncio.run(run_channel_turn("01812345678", "hi", "sms"))
    assert reply.error and "দুঃখিত" in reply.text


# --- ranking summary (rule 15: figures by template only) -------------------------

def _scorer():
    return {
        "candidates": [
            {"crop": "boro_rice", "composite_score": 83.22, "excluded": False, "est_profit_bdt": 9362.2},
            {"crop": "lentil", "composite_score": 52.4, "excluded": False, "est_profit_bdt": 30560.51},
            {"crop": "mustard", "composite_score": 43.76, "excluded": False, "est_profit_bdt": 42820.36},
            {"crop": "potato", "composite_score": 0.0, "excluded": True, "est_profit_bdt": 0.0},
        ],
        "profit_basis": {"crops": {"boro_rice": {"comparable": True}, "lentil": {"comparable": False},
                                   "mustard": {"comparable": False}}},
    }


def test_ranking_sms_labels_ceilings_and_names_exclusions():
    out = sms_text.ranking_summary_sms("Brand", _scorer(), "rabi")
    assert out.splitlines()[0] == "Brand: রবি মৌসুমে ফসলের ক্রম"
    assert "1. বোরো ধান — স্কোর 83, লাভ ৳9,362" in out
    assert "2. মসুর — স্কোর 52, সর্বোচ্চ লাভ ৳30,561 (সব খরচ নয়)" in out
    assert "বাদ: আলু" in out and sms_text.segments(out) <= 3


def test_ranking_sms_is_none_without_candidates():
    assert sms_text.ranking_summary_sms("B", None) is None
    assert sms_text.ranking_summary_sms("B", {"candidates": []}) is None


def test_adapter_keeps_the_ranking_and_flows_text_it(monkeypatch):
    from backend.agent import loop
    from backend.api import sse
    from backend.channels import flows, sms

    class Rec:
        name, mode = "rec", "simulator"
        sent = []

        def send(self, local, text):
            self.sent.append(text)
            return sms.SendResult("rec", "sent")

    rec = Rec()
    sms.set_provider(rec)
    params = {"district": "Rajshahi", "season": "rabi"}

    async def fake(session_id, farm_id, message, client=None, language="bn", channel="web",
                   context_note=None):
        yield sse.tool_call("c1", "crop_scorer", params)
        yield sse.tool_result("c1", "crop_scorer", _scorer())
        yield sse.token("বোরো ধান সবচেয়ে উপযুক্ত। হিসাব পরের SMS-এ।")

    monkeypatch.setattr(loop, "run_turn", fake)
    try:
        reply = asyncio.run(run_channel_turn("01812345678", "কী চাষ করব", "sms"))
        assert reply.ranking_season == "rabi" and reply.ranking["candidates"][0]["crop"] == "boro_rice"
        flows.send_summary(reply)
        assert rec.sent[-1].startswith("Agrosfeer: রবি মৌসুমে ফসলের ক্রম")
    finally:
        sms.set_provider(None)
