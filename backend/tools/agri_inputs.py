"""Read-only Chapter 7 agricultural-input facts from ``agristats.db``.

This deliberately exposes a small set of parameterised lookups rather than SQL.
The tables describe historic national supply/use, regional irrigation coverage and
wages; they are *not* current shop prices and must not be used to cost a plan.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB = Path(__file__).resolve().parents[2] / "data" / "agristats.db"

_CROP_NAMES = {
    "boro_rice": "Boro", "aman_rice": "Aman", "potato": "Potato",
    "mustard": "Oil", "lentil": "Pulses",
}
_SEED_CROP_NAMES = {
    "boro_rice": "Rice", "aman_rice": "Rice", "potato": "Potato",
    "mustard": "Oil", "lentil": "Pulses",
}


def _ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _provenance(view: str, yearbook_year: int | None = None, reference_year: str | None = None) -> dict:
    locator = f"agristats.db :: {view}"
    if yearbook_year is not None:
        locator += f" :: yearbook {yearbook_year}"
    if reference_year:
        locator += f" :: reference {reference_year}"
    return {
        "source_type": "dataset",
        "source_id": "agristats_ch7_agricultural_inputs",
        "source_title": "BBS Yearbook of Agricultural Statistics — Chapter 7: Agricultural Inputs",
        "locator": locator,
        "confidence": "high",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope_note": "Historical input statistics, not current retail prices or a farm-specific prescription.",
    }


def _one_or_many(view: str, where: str = "", params: tuple = ()) -> tuple[list[sqlite3.Row], dict]:
    if not _DB.exists():
        return [], {"error": "agristats.db is unavailable"}
    conn = _ro()
    rows = conn.execute(f"SELECT * FROM {view} {where}", params).fetchall()
    conn.close()
    return rows, {}


def seed_supply(crop: str) -> dict:
    crop_name = _SEED_CROP_NAMES.get(crop.lower())
    if crop_name is None:
        return {"error": f"unsupported crop '{crop}'", "available_crops": sorted(_SEED_CROP_NAMES)}
    rows, error = _one_or_many(
        "v_seed", "WHERE lower(crop_name)=lower(?) AND demand_metric_tons_is_outlier=0 "
        "AND supply_metric_tons_is_outlier=0 ORDER BY yearbook_year DESC, reference_year DESC LIMIT 1", (crop_name,)
    )
    if error or not rows:
        return error or {"error": f"no verified seed record for {crop_name}"}
    r = rows[0]
    return {"crop": crop, "dataset_crop": r["crop_name"], "reference_year": r["reference_year"],
            "yearbook_year": r["yearbook_year"], "seed_demand_metric_tons": r["demand_metric_tons"],
            "seed_supply_metric_tons": r["supply_metric_tons"], **_provenance("v_seed", r["yearbook_year"], r["reference_year"])}


def fertilizer_market(fertilizer_type: str) -> dict:
    rows, error = _one_or_many(
        "v_fertilizer", "WHERE lower(fertilizer_type)=lower(?) AND demand_metric_tons_is_outlier=0 "
        "AND production_metric_tons_is_outlier=0 AND import_metric_tons_is_outlier=0 "
        "AND sales_metric_tons_is_outlier=0 ORDER BY yearbook_year DESC, reference_year DESC LIMIT 1", (fertilizer_type,)
    )
    if error or not rows:
        return error or {"error": f"no verified fertilizer record for '{fertilizer_type}'", "available_types": ["Urea", "TSP", "DAP", "MOP"]}
    r = rows[0]
    return {"fertilizer_type": r["fertilizer_type"], "reference_year": r["reference_year"], "yearbook_year": r["yearbook_year"],
            "demand_metric_tons": r["demand_metric_tons"], "production_metric_tons": r["production_metric_tons"],
            "import_metric_tons": r["import_metric_tons"], "sales_metric_tons": r["sales_metric_tons"],
            **_provenance("v_fertilizer", r["yearbook_year"], r["reference_year"])}


def pesticide_use() -> dict:
    rows, error = _one_or_many(
        "v_pesticides", "WHERE total_consumption_metric_tons_is_outlier=0 "
        "ORDER BY CAST(calendar_year AS INTEGER) DESC, pesticide_id DESC LIMIT 1"
    )
    if error or not rows:
        return error or {"error": "no verified pesticide-use record"}
    r = rows[0]
    return {"calendar_year": r["calendar_year"], "quarter": r["quarter"], "yearbook_year": r["yearbook_year"],
            "total_consumption_metric_tons": r["total_consumption_metric_tons"],
            **_provenance("v_pesticides", r["yearbook_year"], r["calendar_year"])}


def wage_reference(district: str, gender: str = "male", meal_type: str = "two_meal") -> dict:
    rows, error = _one_or_many(
        "v_wages", "WHERE lower(region_name)=lower(?) AND lower(gender)=lower(?) AND lower(meal_type)=lower(?) "
        "AND wage_taka_is_outlier=0 AND wage_taka > 0 ORDER BY yearbook_year DESC, period DESC LIMIT 1",
        (district, gender, meal_type),
    )
    if error or not rows:
        return error or {"error": f"no verified wage record for {district}", "note": "Region spellings in the source may differ from current district spellings."}
    r = rows[0]
    return {"district": r["region_name"], "period": r["period"], "yearbook_year": r["yearbook_year"],
            "gender": r["gender"], "meal_type": r["meal_type"], "food_included": r["food_included"], "wage_taka": r["wage_taka"],
            **_provenance("v_wages", r["yearbook_year"], r["period"])}


def irrigation_region(crop: str, district: str) -> dict:
    crop_name = _CROP_NAMES.get(crop.lower())
    if crop_name is None:
        return {"error": f"unsupported crop '{crop}'", "available_crops": sorted(_CROP_NAMES)}
    rows, error = _one_or_many(
        "v_irrigation_by_region", "WHERE lower(region_name)=lower(?) AND lower(crop_name)=lower(?) "
        "AND area_acres_is_outlier=0 ORDER BY yearbook_year DESC, reference_year DESC LIMIT 1", (district, crop_name)
    )
    if error or not rows:
        return error or {"error": f"no verified irrigation-area record for {crop_name} in {district}"}
    r = rows[0]
    return {"crop": crop, "dataset_crop": r["crop_name"], "district": r["region_name"], "reference_year": r["reference_year"],
            "yearbook_year": r["yearbook_year"], "irrigated_area_acres": r["area_acres"],
            **_provenance("v_irrigation_by_region", r["yearbook_year"], r["reference_year"])}


def irrigation_method(crop: str) -> dict:
    crop_name = _CROP_NAMES.get(crop.lower())
    if crop_name is None:
        return {"error": f"unsupported crop '{crop}'", "available_crops": sorted(_CROP_NAMES)}
    rows, error = _one_or_many(
        "v_irrigation_by_method", "WHERE lower(crop_name)=lower(?) AND area_acres_is_outlier=0 "
        "AND reference_year=(SELECT max(reference_year) FROM v_irrigation_by_method WHERE lower(crop_name)=lower(?) AND area_acres_is_outlier=0) "
        "ORDER BY area_acres DESC", (crop_name, crop_name)
    )
    if error or not rows:
        return error or {"error": f"no verified irrigation-method record for {crop_name}"}
    r = rows[0]
    return {"crop": crop, "dataset_crop": r["crop_name"], "reference_year": r["reference_year"], "yearbook_year": r["yearbook_year"],
            "methods": [{"irrigation_method": x["irrigation_method"], "area_acres": x["area_acres"]} for x in rows],
            **_provenance("v_irrigation_by_method", r["yearbook_year"], r["reference_year"])}


_ACTIONS = {"seed_supply": seed_supply, "fertilizer_market": fertilizer_market, "pesticide_use": pesticide_use,
            "wage_reference": wage_reference, "irrigation_region": irrigation_region, "irrigation_method": irrigation_method}


def agri_inputs(action: str, crop: str = "", district: str = "", fertilizer_type: str = "", gender: str = "male", meal_type: str = "two_meal") -> dict:
    """Entrypoint for parameterised Chapter 7 input-statistics queries."""
    fn = _ACTIONS.get(action)
    if fn is None:
        return {"error": f"unknown action '{action}'", "actions": sorted(_ACTIONS)}
    if action == "seed_supply":
        return fn(crop)
    if action == "fertilizer_market":
        return fn(fertilizer_type)
    if action == "pesticide_use":
        return fn()
    if action == "wage_reference":
        return fn(district, gender, meal_type)
    if action == "irrigation_region":
        return fn(crop, district)
    return fn(crop)
