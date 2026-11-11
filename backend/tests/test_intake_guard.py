"""The agent may not plan on farm facts the farmer never gave (LOG.md, found live)."""

import json

from backend.agent import intake_guard

PARAMS = {"district": "Dinajpur", "soil_type": "loam", "water_source": "irrigated",
          "season": "rabi", "area": 2, "area_unit": "bigha", "budget_bdt": 40000}


def user(text):
    return {"role": "user", "content": text}


def test_the_live_failure_is_refused():
    # What the loop really received on 2026-09-28: the Bangla was garbled in transit.
    history = [user("???? ????????? 2 ???? ????? ????? ??? ???, ??? ?????, ????? 40000 ????? ??? ?????? ?? ??? ????")]
    missing = intake_guard.unstated_fields("crop_scorer", PARAMS, history)
    assert missing == ["district", "soil_type", "water_source", "season"]
    refusal = intake_guard.refusal(missing)
    assert refusal["error"] and "ask_farmer" in refusal["detail"]


def test_stated_facts_pass_including_inflected_bangla_district():
    history = [user("আমার দিনাজপুরে 2 বিঘা দোআঁশ মাটির জমি, সেচ আছে, রবি মৌসুম, বাজেট 40000 টাকা")]
    assert intake_guard.unstated_fields("crop_scorer", PARAMS, history) == []


def test_facts_can_arrive_over_several_turns_and_from_widget_answers():
    history = [user("রবি মৌসুমে কী চাষ করব?"), {"role": "assistant", "content": "জেলা?"},
               user("Dinajpur"), user("দোআঁশ"), user("সেচ")]
    assert intake_guard.unstated_fields("crop_scorer", PARAMS, history) == []


def test_remembered_profile_counts():
    profile = {"district": "Dinajpur", "soil_type": "loam", "water_source": "irrigated", "season": "rabi"}
    history = [{"role": "system", "content": "Known farm profile for this farmer, from memory.\n"
                                             + json.dumps(profile) + "\n"},
               user("আবার পরিকল্পনা দিন")]
    assert intake_guard.unstated_fields("finance_projection", PARAMS, history) == []


def test_a_different_value_than_stated_is_refused():
    history = [user("রাজশাহীতে বেলে মাটি, নলকূপ, রবি")]
    missing = intake_guard.unstated_fields("crop_scorer", {**PARAMS, "district": "Rajshahi"}, history)
    assert missing == ["soil_type", "water_source"]


def test_non_planning_tools_are_not_checked():
    assert intake_guard.unstated_fields("get_forecast", {"district": "Dinajpur"}, []) == []


def test_absent_fields_are_the_tools_business():
    assert intake_guard.unstated_fields("season_plan", {"crop": "potato"}, [user("আলু")]) == []
