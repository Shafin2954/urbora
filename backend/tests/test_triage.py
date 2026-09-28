"""Crop-problem triage: the KB-bounded table, the keypad menu, the SMS answer."""

from __future__ import annotations

import asyncio
import re
from datetime import date

import pytest

from backend.channels import triage_menu
from backend.channels.ussd import UssdContext, fits, step
from backend.kb import triage
from backend.memory import store

PHONE = "01812345678"


# --- the table stays inside the KB ------------------------------------------------------


def test_every_candidate_cites_a_real_kb_passage():
    corpus = triage.corpus()
    for r in triage.RULES:
        assert r.candidate.kb_id in corpus, r.candidate.key
        assert corpus[r.candidate.kb_id]["crop"] in (r.crop, "boro_rice", "aman_rice")


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def test_every_number_in_a_dose_or_advice_appears_in_its_passage():
    """No invented figures (CLAUDE.md rule 2): a dose or an advice line may only
    carry numbers its KB passage states."""
    corpus = triage.corpus()
    for r in triage.RULES:
        c = r.candidate
        for text, kb_id in ((c.advice_bn, c.advice_kb or c.kb_id),
                            (c.dose.text_bn if c.dose else "", c.dose.kb_id if c.dose else c.kb_id)):
            assert kb_id in corpus
            missing = _numbers(text) - _numbers(corpus[kb_id]["text"])
            assert not missing, f"{c.key}: {missing} not in {kb_id}"
        if c.dose and c.dose.amount is not None:
            assert f"{c.dose.amount:g}" in _numbers(corpus[c.dose.kb_id]["text"])


def test_only_described_symptoms_carry_a_dose():
    for r in triage.RULES:
        if r.candidate.dose:
            assert r.candidate.coverage == "S", r.candidate.key


def test_carbofuran_is_never_quoted():
    for r in triage.RULES:
        blob = " ".join(filter(None, [r.candidate.advice_bn, r.candidate.dose.text_bn if r.candidate.dose else ""]))
        assert "কার্বোফুরান" not in blob and "Carbofuran" not in blob


def test_rules_only_use_organs_and_symptoms_the_menu_offers():
    for r in triage.RULES:
        assert r.organ in triage.organs(r.crop), (r.crop, r.organ)
        for s in r.symptoms:
            assert s in triage.symptoms(r.crop, r.organ), (r.crop, r.organ, s)
        stages = triage.STAGES[r.crop]
        assert stages[0][2] <= r.days[0] and r.days[1] <= stages[-1][3] + 10


# --- diagnosis ---------------------------------------------------------------------------


def test_dead_heart_in_aman_tillering_is_stem_borer():
    d = triage.diagnose("aman_rice", "tillering", "sheath", "deadheart", "little")
    assert [c.key for c in d.candidates] == ["yellow_stem_borer"] and d.coverage == "covered"


def test_stage_window_filters_candidates():
    # Mustard alternaria is a 35–75 day problem: not at the seedling stage.
    assert triage.diagnose("mustard", "seedling", "leaf", "spots", "little").candidates == []
    assert triage.diagnose("mustard", "flowering", "leaf", "spots", "little").candidates


def test_cold_injury_needs_the_farmer_to_report_fog_or_cold():
    dry = triage.diagnose("boro_rice", "booting", "panicle", "white_head", "little", "none")
    fog = triage.diagnose("boro_rice", "booting", "panicle", "white_head", "little", "rain_fog")
    assert "cold_injury" not in [c.key for c in dry.candidates]
    assert "cold_injury" in [c.key for c in fog.candidates]


def test_no_kb_coverage_refers_instead_of_guessing():
    d = triage.diagnose("potato", "mature", "root", "other", "half")
    body = triage.answer_sms(d)
    assert d.coverage == "none" and "তথ্য যথেষ্ট নয়" in body and "16123" in body and "হতে পারে" not in body


def test_dose_is_scaled_to_the_farmers_land_by_units():
    d = triage.diagnose("lentil", "flowering", "pod", "holes", "half")
    body = triage.answer_sms(d, area_bigha=2)
    # 900 g and 90 L per acre; 2 bigha = 0.6612 acre (backend/units.py)
    assert "মোট 595 গ্রাম, 60 লিটার পানিতে" in body
    assert "SAAO" in body and "মাস্ক-দস্তানা" in body


def test_whole_field_outbreak_gets_no_dose_and_an_urgent_referral():
    d = triage.diagnose("lentil", "flowering", "pod", "holes", "most")
    body = triage.answer_sms(d, area_bigha=2)
    assert "মাত্রা" not in body and "দেরি না করে SAAO" in body


def test_fertiliser_answer_has_no_spray_lines():
    body = triage.answer_sms(triage.diagnose("boro_rice", "tillering", "leaf", "yellow", "half"), 2.5)
    assert "মোট 20 কেজি" in body and "মাস্ক" not in body and "16123" in body


def test_survey_only_candidate_is_named_but_not_treated():
    body = triage.answer_sms(triage.diagnose("potato", "vegetative", "stem", "cut", "little"))
    assert "কাটুই পোকা" in body and "যাচাই করা তথ্য আমাদের কাছে নেই" in body and "মাত্রা" not in body


# --- keypad menu -----------------------------------------------------------------------------


def ctx(**kw):
    base = dict(brand="B", farm_id="ph-x", today=date(2026, 11, 1), submenus=dict(triage_menu.SUBMENUS))
    base.update(kw)
    return UssdContext(**base)


def walk(keys, c=None):
    c = c or ctx()
    screen, state, action = step(None, None, c)
    for k in keys:
        screen, state, action = step(state, k, c)
        assert fits(screen.text), screen.text
    return screen, state, action


def test_menu_walk_ends_with_a_problem_action():
    # 2 problem → 1 aman → 2 tillering → 2 sheath → 1 dead heart → 2 half
    screen, state, action = walk(["2", "1", "2", "2", "1", "2"])
    assert screen.end and "SMS" in screen.text
    assert action == {"kind": "problem", "request": {
        "crop": "aman_rice", "stage": "tillering", "organ": "sheath", "symptom": "deadheart",
        "extent": "half", "weather": "none", "days_exact": None}}


def test_weather_is_asked_only_when_a_rule_depends_on_it():
    # boro → booting → panicle → white head → little: cold injury depends on fog
    screen, state, action = walk(["2", "2", "3", "4", "1", "1"])
    assert state.get("step") == "weather" and action is None
    screen, state, action = step(state, "1", ctx())
    assert action["request"]["weather"] == "rain_fog"


def test_saved_plan_shortcut_skips_crop_and_stage():
    plan = {"crop": "potato", "tasks": [{"date": "2026-10-01", "task": "রোপণ", "category": "sowing"}]}
    c = ctx(plan=plan)
    screen, state, _ = walk(["2"], c)
    assert "আলু, বপনের 31 দিন?" in screen.text
    screen, state, action = walk(["2", "1", "1", "2", "1"], c)   # yes → leaf → spots → little
    assert action["request"]["days_exact"] == 31 and action["request"]["stage"] == "vegetative"


def test_back_from_the_first_problem_screen_returns_to_the_main_menu():
    screen, state, _ = walk(["2", "0"])
    assert state == {"at": "main"} and screen.text.startswith("B")


# --- the background action --------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    from backend.channels import sms
    sms.set_provider(None)
    yield
    sms.set_provider(None)


def test_problem_action_texts_the_answer_and_records_a_traced_report(db):
    from backend.channels.identity import farm_id_for, mask
    fid = farm_id_for(PHONE)
    store.upsert_contact(fid, PHONE, mask(PHONE), "ussd")
    store.save_farm(fid, {"district": "Rajshahi", "area": 2, "area_unit": "bigha"})
    action = {"kind": "problem", "request": {"crop": "lentil", "stage": "flowering", "organ": "pod",
                                             "symptom": "holes", "extent": "half", "weather": "none",
                                             "days_exact": None}}
    asyncio.run(triage_menu.run_problem_action(PHONE, fid, action))
    sent = store.list_sms(fid)[0]
    assert "ফল ছিদ্রকারী পোকা" in sent["body"] and "মোট 595 গ্রাম" in sent["body"]
    report = store.latest_triage_report(fid)
    assert report["detail"]["candidates"][0]["kb_id"] == "lentil_pest_podborer"
    assert store.triage_summary("2000-01-01")[0] == {
        "district": "Rajshahi", "crop": "lentil", "candidate": "pod_borer", "reports": 1,
        "latest": report["created_at"]}
    turns = [t for s in store.list_channel_sessions() for t in store.get_channel_turns(s["session_id"])]
    names = [e.get("name") for t in turns for e in t["events"]]
    assert names == ["crop_triage", "crop_triage"]  # traced call + result (rule 5)


def test_follow_up_sms_carries_the_triage_as_context(db):
    from backend.channels import adapter
    from backend.channels.identity import farm_id_for
    fid = farm_id_for(PHONE)
    assert adapter._triage_context(fid, "sms") is None
    store.save_triage_report(fid, "Rajshahi", triage.diagnose("mustard", "flowering", "leaf", "spots",
                                                              "little").to_dict(), "sms")
    note = adapter._triage_context(fid, "sms")
    assert note and "alternaria" in note and "never state a pesticide dose" in note
    assert adapter._triage_context(fid, "voice") is None
