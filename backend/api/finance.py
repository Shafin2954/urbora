"""Finance routes — `POST /api/finance/recompute` (docs/archive/hackathon/PLAN.md §2).

This is the endpoint behind the judged moment in docs/archive/hackathon/PLAN.md §5 step 3: change the
area from 2 bigha to 3 on screen and watch every number move consistently. It
recomputes through the same pure engine the agent's tool uses, so the live edit
and the agent's narration can never disagree.

The frozen `RecomputeRequest` is `{farm_id, overrides}` — deliberately partial,
because the UI's edit really is a single changed field. The rest of the inputs
come from the last projection computed for that farm. That state is a dict in
this process, which is the honest scope for a single-process demo: it is lost on
restart, and the UI re-seeds it on the next full projection.

Missing inputs produce a 400 naming exactly which ones, rather than a projection
built on defaults. There is no default farm, and a plausible number nobody chose
is the failure mode this whole subsystem exists to avoid.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.finance import PriceDataUnavailable, load_catalog
from backend.schemas import RecomputeRequest
from backend.tools.cropdb import holt_projection
from backend.tools.finance import _yield_provenance
from backend.units import to_hectares

router = APIRouter()

# farm_id -> the inputs of the last projection computed for it.
_LAST_INPUTS: dict[str, dict[str, Any]] = {}

# What a projection needs before it can be computed at all.
_REQUIRED = ("crop", "district", "area")

# Overrides we accept. Anything else is ignored rather than silently absorbed,
# so a typo'd field name cannot look like it worked.
_ACCEPTED = {"crop", "district", "area", "area_unit", "budget_bdt"}


def remember(farm_id: str, inputs: dict[str, Any]) -> None:
    """Seed the inputs for a farm (used by the chat path and by tests)."""
    _LAST_INPUTS[farm_id] = {k: v for k, v in inputs.items() if k in _ACCEPTED}


def forget(farm_id: str | None = None) -> None:
    if farm_id is None:
        _LAST_INPUTS.clear()
    else:
        _LAST_INPUTS.pop(farm_id, None)


@router.post("/api/finance/recompute")
async def recompute(payload: RecomputeRequest) -> dict:
    """Recompute one farm's projection with some inputs changed."""
    unknown = sorted(set(payload.overrides) - _ACCEPTED)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown override field(s): {', '.join(unknown)}. "
            f"Accepted: {', '.join(sorted(_ACCEPTED))}",
        )

    inputs = {**_LAST_INPUTS.get(payload.farm_id, {}), **payload.overrides}
    missing = [field for field in _REQUIRED if inputs.get(field) in (None, "")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"no projection to recompute for farm '{payload.farm_id}': "
                f"missing {', '.join(missing)}. Send them once in `overrides`; "
                "later edits can send only the changed field."
            ),
        )

    crop = str(inputs["crop"])
    district = str(inputs["district"])
    try:
        area_ha = to_hectares(float(inputs["area"]), str(inputs.get("area_unit", "hectare")))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"bad area: {exc}") from exc

    yields = holt_projection(crop, district)
    if "error" in yields:
        raise HTTPException(status_code=422, detail=yields["error"])

    try:
        projection = load_catalog().projection(
            crop=crop,
            area_ha=area_ha,
            base_yield_kg_ha=yields["base_yield_kg_ha"],
            band_kg_ha=yields["band_kg_ha"],
            yield_provenance=_yield_provenance(yields),
        )
    except PriceDataUnavailable as exc:
        # 422, not 500: the request is fine, the cited data does not exist yet.
        raise HTTPException(
            status_code=422,
            detail=f"no cited {' or '.join(exc.missing)} for {crop} in data/prices.md",
        ) from exc

    remember(payload.farm_id, inputs)

    budget = inputs.get("budget_bdt")
    base = projection.scenarios.base
    return {
        "farm_id": payload.farm_id,
        "crop": crop,
        "district": yields["district"],
        "area_ha": round(area_ha, 4),
        "area_stated": {
            "value": inputs["area"],
            "unit": inputs.get("area_unit", "hectare"),
        },
        "finance": projection.model_dump(),
        "affordable": None if budget is None else base.total_cost <= float(budget),
    }
