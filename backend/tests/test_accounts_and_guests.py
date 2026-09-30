"""Account-level land memory for web consultations, and guest chat history."""

import pytest
from fastapi.testclient import TestClient

from backend.api import crops
from backend.api.main import app
from backend.memory import store

GUEST = "g-1b4e28ba-2fa1-4d2e-8b1a-5c3f9e0a7d21"


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "memory.db")


def test_new_consultation_carries_the_land_but_not_season_or_budget():
    store.save_farm("old-empty", {})
    store.save_farm("old", {"district": "Rajshahi", "area": 2, "area_unit": "bigha", "soil_type": "loam",
                            "water_source": "tubewell", "season": "rabi", "budget_bdt": 20000})
    carried = crops.carry_land("new", ["old-empty", "old"])
    assert carried == {"district": "Rajshahi", "area": 2, "area_unit": "bigha", "soil_type": "loam",
                       "water_source": "tubewell"}
    assert store.get_farm("new") == carried


def test_first_consultation_carries_nothing():
    assert crops.carry_land("new", []) == {}
    assert store.get_farm("new") is None


def test_create_crop_copies_the_accounts_land(monkeypatch):
    store.save_farm("farm-a", {"district": "Bogura", "soil_type": "clay_loam"})
    calls = []

    async def fake_request(method, path, token, *, json=None, params=None):
        calls.append((method, path))
        if path == "/auth/v1/user":
            return {"id": "user-1"}
        if method == "GET" and path == "/rest/v1/crops":
            return [{"farm_id": "farm-a"}]
        return [{**json, "id": "row-2"}]

    monkeypatch.setattr(crops, "_request", fake_request)
    body = TestClient(app).post("/api/crops", headers={"Authorization": "Bearer t"}).json()
    assert body["carried_profile"] == {"district": "Bogura", "soil_type": "clay_loam"}
    assert body["profile"] == {"district": "Bogura", "soil_type": "clay_loam"}
    assert body["farm_id"] != "farm-a"   # own farm row, so later edits do not touch the old one


def test_guest_history_shows_only_farmer_and_advisor_words():
    store.save_session_messages(GUEST, [
        {"role": "system", "content": "farm note"},
        {"role": "user", "content": "আলু কবে লাগাব?"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "x"}]},
        {"role": "tool", "content": "{}", "tool_call_id": "x"},
        {"role": "assistant", "content": "নভেম্বরের মাঝামাঝি।"},
    ])
    body = TestClient(app).get(f"/api/guest/sessions/{GUEST}").json()
    assert body == {"messages": [{"role": "user", "content": "আলু কবে লাগাব?"},
                                 {"role": "assistant", "content": "নভেম্বরের মাঝামাঝি।"}]}


@pytest.mark.parametrize("sid", ["1b4e28ba-2fa1-4d2e-8b1a-5c3f9e0a7d21", "g-abc", "ph-123", "G-1B4E28BA-2FA1-4D2E-8B1A-5C3F9E0A7D21"])
def test_guest_history_refuses_anything_but_a_guest_id(sid):
    store.save_session_messages(sid, [{"role": "user", "content": "private"}])
    assert TestClient(app).get(f"/api/guest/sessions/{sid}").status_code == 404
