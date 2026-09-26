"""Tool definitions (Claude native tool-use schemas) + dispatcher.

Every tool here emits a tool_call / tool_result pair in the trace (rule 5). Tool
params are ENGLISH (rule 10). Results are JSON-serializable dicts that already
carry source_type / source_id / retrieved_at so the UI can build a Provenance for
any number they contain (rule 3).

New tools (rag_query, cropdb_sql, crop_scorer, aez_soil_check, finance, checkout,
check_plan_conflicts) get registered here as they land in later blocks.
"""

from __future__ import annotations

from typing import Any, Callable

from ..tools.ask import ask_farmer
from ..tools.crop_scorer import crop_scorer_tool
from ..tools.farm_memory import remember_farm
from ..tools.cropdb import cropdb_sql
from ..tools.agri_inputs import agri_inputs
from ..tools.finance import finance_projection
from ..tools.geocode import geocode
from ..tools.weather import get_climatology, get_forecast
from ..tools.season_plan import season_plan
from ..tools.plan_conflicts import check_plan_conflicts
from ..tools.pest_risk import pest_risk
from ..tools.market_price import market_price
from ..tools.care_scheduler import care_schedule
from ..tools.scenario import simulate_budget
from ..kb.retrieval import rag_query
from ..market.inputs import find_inputs

# Anthropic tool definitions (input_schema = JSON Schema, English descriptions).
TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "simulate_budget",
        "description": "Re-run deterministic crop ranking and finance when the farmer changes budget. The server computes the changed budget and deltas; never do the percentage arithmetic yourself.",
        "input_schema": {"type": "object", "properties": {"district": {"type": "string"}, "soil_type": {"type": "string"}, "water_source": {"type": "string"}, "season": {"type": "string"}, "area": {"type": "number"}, "area_unit": {"type": "string"}, "budget_bdt": {"type": "number"}, "budget_change_pct": {"type": "number"}}, "required": ["district", "soil_type", "water_source", "season", "area", "area_unit", "budget_bdt", "budget_change_pct"]},
    },
    {
        "name": "care_schedule",
        "description": "Show source-cited fertilizer and irrigation tasks from the saved season plan, with live forecast context when a task falls in the forecast horizon. Never calculate dose or task date yourself.",
        "input_schema": {"type": "object", "properties": {"farm_id": {"type": "string"}}, "required": ["farm_id"]},
    },
    {
        "name": "check_plan_conflicts",
        "description": "Check the saved season plan against the live Open-Meteo forecast. It only flags weather-dependent tasks in the forecast horizon and persists traceable alerts; never invent a weather conflict.",
        "input_schema": {"type": "object", "properties": {"farm_id": {"type": "string"}}, "required": ["farm_id"]},
    },
    {
        "name": "market_price",
        "description": (
            "Historical monthly market-price pattern for a crop, plus a deterministic "
            "sell-now / consider-storing reading. Use it when the farmer asks when to "
            "sell, whether to store, or what the crop is worth over the year. You must "
            "NEVER work out the seasonal pattern or the percentage yourself. Three "
            "things you MUST say when narrating it: (1) it is a HISTORICAL PATTERN "
            "averaged over past years, not a forecast — word it like climatology, "
            "never as a prediction; (2) these are WHOLESALE prices, not what the "
            "farmer is paid, so they must not be used as revenue (revenue comes from "
            "finance_projection); (3) storage cost and spoilage are NOT included "
            "because no source prices them, so a 'store' reading is an upside before "
            "costs, not a net gain."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "enum": ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]},
                "month": {"type": "integer", "description": "1-12, the month being decided in; defaults to now"},
            },
            "required": ["crop"],
        },
    },
    {
        "name": "pest_risk",
        "description": (
            "Deterministic pest and disease risk for a crop at its CURRENT growth "
            "stage, scored against the live 16-day forecast. You must NEVER judge "
            "pest risk yourself — call this and narrate it. Pass farm_id and it "
            "recovers the crop, sowing date and district from the saved plan and "
            "farm profile. Each risk returns low/medium/high, the stage window, "
            "which forecast days favoured the organism, and cited prevention/"
            "treatment text with doses. Risks whose susceptible window starts "
            "beyond the 16-day horizon come back as status='upcoming' with NO "
            "risk level — report that as 'নজর রাখুন', never as a prediction. "
            "treatment_cost_bdt is always null: no citable pesticide price exists "
            "in our sources, so say the cost is unknown and never estimate one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "enum": ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]},
                "farm_id": {"type": "string", "description": "fills crop/sowing_date/district from memory"},
                "district": {"type": "string", "description": "canonical district name"},
                "sowing_date": {"type": "string", "description": "confirmed YYYY-MM-DD sowing/transplant date"},
            },
        },
    },
    {
        "name": "rag_query",
        "description": (
            "Retrieve source-cited passages from the curated local agronomy knowledge base. "
            "Use English queries. You MUST call it before explaining a crop recommendation "
            "and again for the chosen crop's calendar/fertilizer/irrigation advice; narrate "
            "only what its returned passages support."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "English agronomy query"},
                "crop": {"type": "string", "enum": ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]},
                "limit": {"type": "integer", "description": "1–5 results; default 3"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "season_plan",
        "description": "Create a source-cited calendar for a confirmed crop and confirmed planting/transplant date. Never write dates yourself; call this tool and narrate its tasks.",
        "input_schema": {"type": "object", "properties": {"farm_id": {"type": "string"}, "crop": {"type": "string", "enum": ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]}, "start_date": {"type": "string", "description": "confirmed YYYY-MM-DD planting or transplant date"}}, "required": ["farm_id", "crop", "start_date"]},
    },
    {
        "name": "geocode",
        "description": (
            "Resolve a Bangladeshi place or district name to candidate coordinates. "
            "Returns a list of candidates; ALWAYS confirm the district with the "
            "farmer before using the coordinates (village names are ambiguous). "
            "Falls back to a 64-district table if the live geocoder is down."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Place/district name to look up"},
                "count": {"type": "integer", "description": "Max candidates (default 5)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_forecast",
        "description": (
            "16-day daily weather FORECAST (actionable) for coordinates. Returns "
            "daily tmax/tmin (°C) and precipitation (mm), source_type='forecast'. "
            "Use for near-term, dated tasks. Word it as a forecast, not a guarantee."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "days": {"type": "integer", "description": "1–16, default 16"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "get_climatology",
        "description": (
            "Historical monthly NORMALS (planning assumption) for coordinates, "
            "averaged over past years. source_type='climatology'. Use for months "
            "beyond the 16-day forecast horizon. This is an average that may "
            "differ — NEVER present it as a prediction."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "month": {"type": "integer", "description": "1–12; omit for all months"},
                "years": {"type": "integer", "description": "Years to average, default 10"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "cropdb_sql",
        "description": (
            "District crop-yield facts with provenance. Actions: 'district_yields' "
            "(observed yield history kg/ha), 'holt_projection' (damped-Holt base "
            "yield + band + n_points + trend — a projection, not a guarantee), "
            "'yield_track_record' (district's latest yield percentile vs other "
            "districts). Available crops: boro_rice, aman_rice, potato, mustard, "
            "lentil. Wheat and maize have NO yield data — the tool returns an error "
            "for them; report that honestly, never estimate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["district_yields", "holt_projection", "yield_track_record"],
                },
                "crop": {
                    "type": "string",
                    "description": "boro_rice | aman_rice | potato | mustard | lentil",
                },
                "district": {"type": "string", "description": "canonical district name"},
            },
            "required": ["action", "crop", "district"],
        },
    },
    {
        "name": "agri_inputs",
        "description": (
            "Retrieve verified historic BBS Chapter 7 agricultural-input statistics. "
            "Actions are: seed_supply (crop), fertilizer_market (fertilizer_type: Urea/TSP/DAP/MOP), "
            "pesticide_use, wage_reference (district, optional gender/meal_type), irrigation_region "
            "(crop, district), and irrigation_method (crop). These are historical aggregate/reference "
            "facts, NOT current retail prices or a farm-specific dosage. Never use them to calculate "
            "costs, profit, or fertilizer dose; use finance_projection and retrieved agronomy sources for those."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["seed_supply", "fertilizer_market", "pesticide_use", "wage_reference", "irrigation_region", "irrigation_method"]},
                "crop": {"type": "string", "enum": ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]},
                "district": {"type": "string"},
                "fertilizer_type": {"type": "string", "enum": ["Urea", "TSP", "DAP", "MOP"]},
                "gender": {"type": "string", "enum": ["male", "female"]},
                "meal_type": {"type": "string", "enum": ["one_meal", "two_meal"]},
            },
            "required": ["action"],
        },
    },
    {
        "name": "crop_scorer",
        "description": (
            "Deterministic crop ranking (you must NEVER rank crops yourself — "
            "call this tool and narrate its output). Ranks boro_rice, aman_rice, "
            "potato, mustard, lentil for a farm. It uses cited crop facts for "
            "season, soil, water and climate checks. 'Profit' plus Budget "
            "screening need cited prices for EVERY candidate in data/prices.md. "
            "The result's 'degraded' list names any live source failure or "
            "missing finance evidence; you MUST relay it honestly in Bangla before "
            "presenting any ranking, and never present a partial composite as a "
            "complete recommendation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "district": {"type": "string", "description": "canonical district name"},
                "soil_type": {
                    "type": "string",
                    "enum": ["clay", "loam", "sandy_loam", "clay_loam", "silt", "sandy", "peat"],
                },
                "water_source": {
                    "type": "string",
                    "enum": ["rainfed", "tubewell", "canal", "irrigated"],
                },
                "season": {"type": "string", "enum": ["rabi", "kharif1", "kharif2"]},
                "candidates": {
                    "type": "array", "items": {"type": "string"},
                    "description": "subset of the 5 supported crops; omit for all 5",
                },
                "area": {
                    "type": "number",
                    "description": "Exact number stated by the farmer; NEVER convert it to hectares",
                },
                "area_unit": {
                    "type": "string",
                    "enum": ["bigha", "katha", "decimal", "acre", "hectare"],
                    "description": "The farmer's stated unit for `area`; the server converts it, never the model",
                },
                "budget_bdt": {"type": "number", "description": "farmer's budget in BDT"},
            },
            "required": ["district", "soil_type", "water_source", "season"],
        },
    },
    {
        "name": "ask_farmer",
        "description": (
            "Ask the farmer ONE missing intake detail and show them the right "
            "input widget for it. Use this whenever you need a required field "
            "you do not have: district, area, soil type, water source, budget, "
            "season, land type. Prefer it over asking in plain prose — the "
            "widget is far faster to answer on a phone. Only one question may "
            "be open at a time, so call this at most once per turn and then END "
            "YOUR TURN: do not answer your own question or assume a value. "
            "Widget choice: 'dropdown' for district (options are filled in for "
            "you — do not list them), 'chips' for a short fixed set like soil "
            "type or water source, 'number_unit' for area (farmer picks "
            "bigha/katha/decimal/acre), 'number' for budget, 'text' otherwise. "
            "prompt_bn must be Bangla, and so must every option's label_bn."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "what is being collected, e.g. district / area / soil_type",
                },
                "prompt_bn": {
                    "type": "string",
                    "description": "the question in Bangla, as the farmer will read it",
                },
                "input_kind": {
                    "type": "string",
                    "enum": ["chips", "dropdown", "number", "number_unit", "text"],
                },
                "options": {
                    "type": "array",
                    "description": "for chips/dropdown: [{value, label_bn}]. Omit for district.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "label_bn": {"type": "string"},
                        },
                        "required": ["value", "label_bn"],
                    },
                },
                "unit_options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "for number_unit; defaults to the area units",
                },
            },
            "required": ["field", "prompt_bn", "input_kind"],
        },
    },
    {
        "name": "remember_farm",
        "description": (
            "Save what you now know about this farmer's farm, so you can greet "
            "them with it next session. Call this ONCE, after you have restated "
            "the profile and the farmer has confirmed it — store what they "
            "agreed to, not what you inferred mid-intake. Calls merge, so a "
            "later call carrying only a budget will not erase the district. "
            "Only promise to remember what the result's `profile` actually "
            "contains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "farm_id": {
                    "type": "string",
                    "description": "the farm id for this session",
                },
                "name": {"type": "string", "description": "farmer's name"},
                "district": {"type": "string"},
                "area": {"type": "number", "description": "farm size as stated"},
                "area_unit": {
                    "type": "string",
                    "enum": ["bigha", "katha", "decimal", "acre", "hectare"],
                },
                "soil_type": {
                    "type": "string",
                    "enum": ["clay", "loam", "sandy_loam", "clay_loam", "silt", "sandy", "peat"],
                },
                "water_source": {
                    "type": "string",
                    "enum": ["rainfed", "tubewell", "canal", "irrigated"],
                },
                "budget_bdt": {"type": "number"},
                "season": {"type": "string", "enum": ["rabi", "kharif1", "kharif2"]},
                "land_type": {"type": "string", "description": "উঁচু / মাঝারি / নিচু"},
                "last_crop": {"type": "string"},
            },
            "required": ["farm_id"],
        },
    },
    {
        "name": "finance_projection",
        "description": (
            "Costed three-scenario projection for ONE crop on ONE farm: itemised "
            "costs, expected yield, revenue, net profit, ROI, break-even yield and "
            "break-even price. You must NEVER compute money yourself — call this "
            "and narrate it. Yield comes from crop.db's damped-Holt projection; "
            "always quote the base yield together with its band, never alone. "
            "Prices come from data/prices.md, and only from cited rows: if a crop "
            "has no cited price or cost yet the tool returns "
            "error='price_data_unavailable' listing what is missing — say that "
            "plainly in Bangla ('তথ্য যথেষ্ট নয়') and do NOT estimate a number. "
            "Pass the farmer's exact area number and stated unit unchanged; the tool converts. "
            "If you pass budget_bdt it also returns whether the plan is affordable "
            "and the largest area that would fit — use that for a reduced-area "
            "replan instead of calculating one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "crop": {
                    "type": "string",
                    "description": "boro_rice | aman_rice | potato | mustard | lentil",
                },
                "district": {"type": "string", "description": "canonical district name"},
                "area": {
                    "type": "number",
                    "description": "Exact number stated by the farmer; NEVER convert it to hectares",
                },
                "area_unit": {
                    "type": "string",
                    "enum": ["bigha", "katha", "decimal", "acre", "hectare"],
                    "description": "The farmer's stated unit for `area`; the server converts it, never the model",
                },
                "budget_bdt": {"type": "number", "description": "farmer's budget in BDT"},
            },
            "required": ["crop", "district", "area"],
        },
    },
    {
        "name": "find_inputs",
        "description": (
            "Marketplace: ranked nearby dealer offers for ONE input the farmer needs "
            "(fertiliser, fungicide, insecticide), with each pack price, distance and "
            "stock. Call it after you have recommended an input from a cited source "
            "(KB dose, pest_risk treatment) and the farmer wants to buy, or asks where "
            "to get it or what it costs. The ranking is deterministic — never re-rank "
            "or compute totals yourself; quote `for_quantity` when present. Offers "
            "with is_demo=true are seeded demo dealers: say 'ডেমো দোকান'. You do not "
            "place orders: tell the farmer to tap the order button in the app, use "
            "USSD menu 4, or ask again by SMS."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "generic input name in English, e.g. urea, tsp, mop, mancozeb, tricyclazole"},
                "district": {"type": "string", "description": "the farm's district, canonical English (from geocode / farm profile)"},
                "quantity": {"type": "number", "description": "amount needed in kg or litres, copied from a tool result; omit if unknown"},
            },
            "required": ["product", "district"],
        },
    },
]

_DISPATCH: dict[str, Callable[..., dict]] = {
    "rag_query": rag_query,
    "geocode": geocode,
    "get_forecast": get_forecast,
    "get_climatology": get_climatology,
    "cropdb_sql": cropdb_sql,
    "agri_inputs": agri_inputs,
    "crop_scorer": crop_scorer_tool,
    "finance_projection": finance_projection,
    "season_plan": season_plan,
    "ask_farmer": ask_farmer,
    "remember_farm": remember_farm,
    "check_plan_conflicts": check_plan_conflicts,
    "pest_risk": pest_risk,
    "market_price": market_price,
    "care_schedule": care_schedule,
    "simulate_budget": simulate_budget,
    "find_inputs": find_inputs,
}


def dispatch(name: str, params: dict[str, Any]) -> dict:
    """Run a tool by name with kwargs `params`. Never raises: a failed tool returns
    an {error: ...} dict so the loop can hand it back to the model as an is_error
    tool_result and let the agent recover."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return fn(**params)
    except TypeError as e:
        return {"error": f"bad params for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 — surface, don't crash the turn
        return {"error": f"{name} failed: {e}"}
