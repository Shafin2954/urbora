"""Tier 1 fertilizer and irrigation schedule derived from a cited season plan."""
from __future__ import annotations

from backend.memory.store import get_farm, get_plan
from backend.tools.districts import lookup_district
from backend.tools.weather import get_forecast


def care_schedule(farm_id: str) -> dict:
    """Return the plan's fertilizer/irrigation tasks with live forecast context.

    Task dates, doses and sources remain those of `season_plan`; this tool only
    selects actionable care work and attaches an API reading for dates inside
    the forecast horizon.
    """
    plan, farm = get_plan(farm_id), get_farm(farm_id)
    if not plan:
        return {"error": "no saved season plan for this farm"}
    if not farm or not farm.get("district"):
        return {"error": "farm has no remembered district"}
    hit = lookup_district(str(farm["district"]))
    if not hit:
        return {"error": f"unknown district: {farm['district']}"}
    _, _, lat, lon = hit
    forecast = get_forecast(lat, lon)
    daily = {row["date"]: row for row in forecast.get("daily", [])}
    tasks = []
    for task in plan.get("tasks", []):
        if task.get("category") not in {"fertilizer", "irrigation"}:
            continue
        item = {"date": task["date"], "task": task["task"], "category": task["category"],
                "details": task["details"], "provenance": task["provenance"]}
        if task["date"] in daily:
            item["forecast"] = daily[task["date"]]
            item["forecast_provenance"] = {
                "value": daily[task["date"]].get("precip_mm"), "unit": "mm",
                "source_type": "api", "source_id": forecast["source_id"],
                "source_title": forecast["source_title"], "locator": forecast["locator"],
                "retrieved_at": forecast["retrieved_at"], "formula": "forecast precipitation on scheduled task date",
                "confidence": "high",
            }
        tasks.append(item)
    return {"farm_id": farm_id, "crop": plan["crop"], "tasks": tasks, "forecast": forecast}
