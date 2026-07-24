from fastapi.testclient import TestClient

from backend.api.main import app
from backend.memory.store import get_plan, save_plan
from backend.tools.season_plan import season_plan


def test_plan_round_trips_through_memory_and_api():
    plan = season_plan("test-plan-farm", "potato", "2026-11-01")["plan"]
    save_plan("test-plan-farm", plan)
    assert get_plan("test-plan-farm") == plan
    response = TestClient(app).get("/api/plan/test-plan-farm")
    assert response.status_code == 200
    assert response.json()["tasks"][0]["provenance"]["locator"]


def test_missing_plan_is_404():
    assert TestClient(app).get("/api/plan/no-such-plan").status_code == 404
