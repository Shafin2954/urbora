"""Deterministic, traceable forecast checks for saved weather-dependent tasks."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.memory.store import get_farm, get_plan, save_alert
from backend.tools.districts import lookup_district
from backend.tools.weather import get_forecast

_RAIN_THRESHOLD_MM = 10.0


def check_plan_conflicts(farm_id: str) -> dict:
    plan = get_plan(farm_id)
    farm = get_farm(farm_id)
    if not plan:
        return {"error": "no saved season plan for this farm"}
    if not farm or not farm.get("district"):
        return {"error": "farm has no remembered district"}
    district = lookup_district(str(farm["district"]))
    if not district:
        return {"error": f"unknown district: {farm['district']}"}
    _, _, lat, lon = district
    forecast = get_forecast(lat, lon)
    if forecast.get("error"):
        return {"error": "forecast unavailable", "weather": forecast}
    by_date = {day["date"]: day for day in forecast.get("daily", [])}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    alerts = []
    for task in plan.get("tasks", []):
        if not task.get("depends_on_weather"):
            continue
        day = by_date.get(task.get("date"))
        if not day or (day.get("precip_mm") or 0) < _RAIN_THRESHOLD_MM:
            continue
        alert = {
            "alert_id": f"rain-{farm_id}-{task['date']}", "farm_id": farm_id,
            "task_date": task["date"], "task": task["task"],
            "conflict": f"Forecast precipitation is {day['precip_mm']} mm (threshold {_RAIN_THRESHOLD_MM} mm).",
            "suggestion": "Check field drainage and move this weather-dependent task to the next safe dry window.",
            "created_at": now, "status": "open",
            "provenance": {
                "value": day["precip_mm"], "unit": "mm", "source_type": "api",
                "source_id": forecast["source_id"], "source_title": forecast["source_title"],
                "locator": forecast["locator"], "retrieved_at": forecast["retrieved_at"],
                "formula": f"forecast precipitation >= {_RAIN_THRESHOLD_MM} mm for weather-dependent task",
                "confidence": "high",
            },
        }
        save_alert(alert)
        alerts.append(alert)
    return {"farm_id": farm_id, "alerts": alerts, "forecast": forecast}
