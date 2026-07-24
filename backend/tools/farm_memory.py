"""`remember_farm` — persist what the agent learned about a farm.

PRD §4 lists memory as one of the five judged behaviours, and PLAN §5 opens the
demo on it: the agent greets a returning farmer and recalls their farm. That
only works if something writes the profile down. `backend/memory/store.py` has
had `save_farm` since the store was built; nothing called it, so a "returning
farmer" could only ever be a row seeded by hand.

The agent calls this once it has confirmed the profile with the farmer — after
the restatement step the prompt already requires, so what gets stored is what
the farmer agreed to, not what the model inferred halfway through intake.

Storage is a JSON blob rather than typed columns on purpose: intake is
incremental, and a half-known farm ("district and area, nothing else yet") has
to be storable. `FarmProfile` in schemas.py is the shape for a *complete*
profile reaching the UI; this is the working memory behind it.
"""

from __future__ import annotations

from ..memory.store import get_farm, save_farm

# Fields worth remembering between sessions. Anything else is conversation, not
# farm identity, and belongs in the message history instead.
REMEMBERED = (
    "name",
    "district",
    "area",
    "area_unit",
    "soil_type",
    "water_source",
    "budget_bdt",
    "season",
    "land_type",
    "last_crop",
)


def remember_farm(farm_id: str, **fields) -> dict:
    """Save or update a farm profile.

    Args:
        farm_id: which farm. Comes from the session; ask the farmer for a name
            rather than inventing an id.
        **fields: any of name, district, area, area_unit, soil_type,
            water_source, budget_bdt, season, land_type, last_crop.
    """
    if not (farm_id or "").strip():
        return {"error": "farm_id is required", "detail": "Nothing to key the farm on."}

    known = {k: v for k, v in fields.items() if k in REMEMBERED and v not in (None, "")}
    if not known:
        return {
            "error": "nothing to remember",
            "detail": f"Pass at least one of: {', '.join(REMEMBERED)}.",
        }

    unknown = sorted(set(fields) - set(REMEMBERED))

    # Merge, don't replace: intake is incremental, and a second call carrying
    # only the budget must not erase the district learned three turns ago.
    profile = {**(get_farm(farm_id) or {}), **known}
    save_farm(farm_id, profile)

    return {
        "saved": True,
        "farm_id": farm_id,
        "profile": profile,
        "ignored_fields": unknown,
        "note": (
            "Stored. This farm will be recalled at the start of the farmer's next "
            "session, so do not promise to remember anything not listed in profile."
        ),
    }
