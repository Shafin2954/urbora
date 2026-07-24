from backend.memory import store
from backend.tools import plan_conflicts


def test_weather_dependent_task_with_heavy_rain_becomes_persisted_alert(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "alerts.db")
    store.save_farm("farm-1", {"district": "Rajshahi"})
    store.save_plan("farm-1", {"farm_id": "farm-1", "crop": "potato", "tasks": [
        {"date": "2026-07-25", "task": "Irrigate", "depends_on_weather": True},
        {"date": "2026-07-25", "task": "Land prep", "depends_on_weather": False},
    ]})
    monkeypatch.setattr(plan_conflicts, "get_forecast", lambda *_: {
        "daily": [{"date": "2026-07-25", "precip_mm": 12.5}],
        "source_id": "open-meteo-forecast", "source_title": "Open-Meteo forecast",
        "locator": "https://api.open-meteo.com", "retrieved_at": "2026-07-24T00:00:00+00:00",
    })

    result = plan_conflicts.check_plan_conflicts("farm-1")

    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["task"] == "Irrigate"
    assert result["alerts"][0]["provenance"]["value"] == 12.5
    assert len(store.get_alerts("farm-1")) == 1
