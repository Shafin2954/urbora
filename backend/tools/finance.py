"""`finance_projection` — the agent's costing tool.

CLAUDE.md §2.1: the LLM never does arithmetic. It calls this, and narrates what
comes back. Every taka in the result was produced by `backend/finance/engine.py`
from a cited row in `data/prices.md` and a yield from crop.db.

The tool is a join of two sources, and keeping them visibly separate is the
point: **yield** comes from crop.db's damped-Holt projection (with its band —
NOTES #23, never quote one without the other), **money** comes from prices.md.
When either is missing the tool says which one, in a form the agent is
instructed to relay honestly rather than paper over.
"""

from __future__ import annotations

from backend.finance import PriceDataUnavailable, load_catalog
from backend.schemas import Provenance

from .cropdb import holt_projection, resolve_crop

# Local units the farmer actually speaks, accepted here so the agent never has
# to convert (rule 1 again: it does not do arithmetic, including unit maths).
from backend.units import to_hectares


def _yield_provenance(projection: dict) -> Provenance:
    return Provenance(
        value=projection["base_yield_kg_ha"],
        unit="kg/ha",
        source_type="computed",
        source_id=projection["source_id"],
        source_title=projection["source_title"],
        locator=f"{projection['district']} {projection['crop']}, n={projection['n_points']}",
        retrieved_at=projection["retrieved_at"],
        formula=projection["formula"],
        confidence=projection["confidence"],
    )


def finance_projection(
    crop: str,
    district: str,
    area: float,
    area_unit: str = "hectare",
    budget_bdt: float | None = None,
) -> dict:
    """Three-scenario costing for one crop on one farm.

    Args:
        crop: canonical crop key (boro_rice, aman_rice, potato, mustard, lentil).
        district: farm district; selects the yield series.
        area: farm size as the farmer stated it.
        area_unit: bigha/katha/decimal/acre/hectare — converted here, once.
        budget_bdt: optional. If given, the result says whether the plan fits.
    """
    if resolve_crop(crop) is None:
        return {
            "error": f"no yield data for '{crop}'",
            "detail": (
                "This crop has no district yield series, so it cannot be costed "
                "without inventing a harvest. Tell the farmer plainly."
            ),
        }

    try:
        area_ha = to_hectares(area, area_unit)
    except Exception as exc:  # noqa: BLE001 — unknown unit is a user-facing error
        return {"error": f"unknown area unit '{area_unit}'", "detail": str(exc)}

    projection = holt_projection(crop, district)
    if "error" in projection:
        return {
            "error": projection["error"],
            "detail": "No yield projection, so no revenue can be estimated.",
        }

    catalog = load_catalog()
    try:
        result = catalog.projection(
            crop=crop,
            area_ha=area_ha,
            base_yield_kg_ha=projection["base_yield_kg_ha"],
            band_kg_ha=projection["band_kg_ha"],
            yield_provenance=_yield_provenance(projection),
        )
    except PriceDataUnavailable as exc:
        # The honest degradation path, and the one that is live today.
        return {
            "error": "price_data_unavailable",
            "crop": crop,
            "missing": exc.missing,
            "detail": (
                f"data/prices.md has no cited {' or '.join(exc.missing)} for {crop}. "
                "Say so in Bangla — do not estimate a cost or a profit."
            ),
            "yield_available": {
                "base_yield_kg_ha": projection["base_yield_kg_ha"],
                "band_kg_ha": projection["band_kg_ha"],
                "n_points": projection["n_points"],
            },
        }

    base = result.scenarios.base
    out: dict = {
        "crop": crop,
        "district": projection["district"],
        "area_ha": round(area_ha, 4),
        "area_stated": {"value": area, "unit": area_unit},
        "projection": result.model_dump(),
        "summary": {
            "total_cost_bdt": base.total_cost,
            "expected_yield_kg": base.expected_yield_kg,
            "revenue_bdt": base.revenue,
            "net_profit_bdt": base.net_profit,
            "roi_pct": base.roi_pct,
            "breakeven_yield_kg": result.breakeven_yield_kg,
            "breakeven_price_bdt_per_kg": result.breakeven_price_bdt,
        },
        # The band is surfaced next to the yield so a narration cannot quote one
        # without the other (NOTES #23).
        "yield_band_kg_ha": projection["band_kg_ha"],
        "yield_n_points": projection["n_points"],
    }

    if budget_bdt is not None:
        affordable = base.total_cost <= budget_bdt
        out["budget"] = {
            "budget_bdt": budget_bdt,
            "affordable": affordable,
            "shortfall_bdt": round(max(0.0, base.total_cost - budget_bdt), 2),
            "max_area_ha_within_budget": (
                round(budget_bdt / base.total_cost * area_ha, 4)
                if base.total_cost > 0
                else None
            ),
            "note": (
                "If not affordable, offer a reduced area — max_area_ha_within_budget "
                "is that area, already computed. Do not compute it yourself."
            ),
        }

    return out
