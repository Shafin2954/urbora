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

from ..tools.crop_scorer import crop_scorer_tool
from ..tools.cropdb import cropdb_sql
from ..tools.geocode import geocode
from ..tools.weather import get_climatology, get_forecast

# Anthropic tool definitions (input_schema = JSON Schema, English descriptions).
TOOL_DEFS: list[dict[str, Any]] = [
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
        "name": "crop_scorer",
        "description": (
            "Deterministic crop ranking (you must NEVER rank crops yourself — "
            "call this tool and narrate its output). Ranks boro_rice, aman_rice, "
            "potato, mustard, lentil for a farm. CURRENT LIMITATION: only the "
            "'District track record' and 'Stability' components score real "
            "points today (the curated soil/water/climate knowledge base and "
            "B's finance engine don't exist yet) — 'Agronomic fit', 'Profit', and "
            "'Climate fit' report as 'unavailable', and Season/Soil/Water/Budget "
            "screening does not run (all supported crops are shown regardless of "
            "fit). The result's 'degraded' list names exactly what's unavailable "
            "and why — you MUST relay this honestly in Bangla before presenting "
            "any ranking; never present the partial composite as a complete "
            "recommendation."
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
                "area_ha": {"type": "number", "description": "farm area in hectares"},
                "budget_bdt": {"type": "number", "description": "farmer's budget in BDT"},
            },
            "required": ["district", "soil_type", "water_source", "season"],
        },
    },
]

_DISPATCH: dict[str, Callable[..., dict]] = {
    "geocode": geocode,
    "get_forecast": get_forecast,
    "get_climatology": get_climatology,
    "cropdb_sql": cropdb_sql,
    "crop_scorer": crop_scorer_tool,
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
