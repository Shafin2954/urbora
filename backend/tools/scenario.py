"""Deterministic Tier 1 scenario simulation; never model arithmetic."""
from __future__ import annotations

from backend.tools.crop_scorer import crop_scorer_tool
from backend.tools.finance import finance_projection


def simulate_budget(
    district: str, soil_type: str, water_source: str, season: str,
    area: float, area_unit: str, budget_bdt: float, budget_change_pct: float,
) -> dict:
    """Re-run ranking and finance under a changed farmer budget."""
    if not -100 < budget_change_pct <= 500:
        return {"error": "budget_change_pct must be greater than -100 and at most 500"}
    scenario_budget = round(budget_bdt * (1 + budget_change_pct / 100), 2)
    inputs = {"district": district, "soil_type": soil_type, "water_source": water_source,
              "season": season, "area": area, "area_unit": area_unit}
    baseline = crop_scorer_tool(**inputs, budget_bdt=budget_bdt)
    scenario = crop_scorer_tool(**inputs, budget_bdt=scenario_budget)
    survivors = [candidate["crop"] for candidate in scenario.get("candidates", []) if not candidate["excluded"]]
    finances = {
        crop: finance_projection(crop, district, area, area_unit, scenario_budget)
        for crop in survivors
    }
    return {
        "baseline_budget_bdt": budget_bdt, "scenario_budget_bdt": scenario_budget,
        "budget_change_pct": budget_change_pct,
        "formula": "scenario_budget = baseline_budget * (1 + budget_change_pct / 100)",
        "baseline_ranking": baseline, "scenario_ranking": scenario,
        "finance": finances,
    }
