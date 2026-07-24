from backend.memory import store
from backend.tools import care_scheduler


def test_scheduler_keeps_only_cited_fertilizer_and_irrigation_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "scheduler.db")
    store.save_farm("farm-1", {"district": "Rajshahi"})
    store.save_plan("farm-1", {"farm_id": "farm-1", "crop": "boro_rice", "tasks": [
        {"date": "2026-07-25", "task": "Irrigate", "category": "irrigation", "details": "d", "provenance": {"source_id": "x"}},
        {"date": "2026-07-26", "task": "Fertilize", "category": "fertilizer", "details": "d", "provenance": {"source_id": "x"}},
        {"date": "2026-07-26", "task": "Weed", "category": "weeding", "details": "d", "provenance": {"source_id": "x"}},
    ]})
    monkeypatch.setattr(care_scheduler, "get_forecast", lambda *_: {"daily": [{"date": "2026-07-25", "precip_mm": 4}], "source_id": "weather", "source_title": "Weather", "locator": "url", "retrieved_at": "now"})
    result = care_scheduler.care_schedule("farm-1")
    assert [task["task"] for task in result["tasks"]] == ["Irrigate", "Fertilize"]
    assert result["tasks"][0]["forecast"]["precip_mm"] == 4
