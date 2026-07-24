"""Persisted deterministic season-plan endpoint from the frozen API contract."""
from fastapi import APIRouter, HTTPException

from backend.memory.store import get_plan
from backend.schemas import SeasonPlan

router = APIRouter()


@router.get("/api/plan/{farm_id}", response_model=SeasonPlan)
async def plan_for_farm(farm_id: str) -> SeasonPlan:
    plan = get_plan(farm_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No season plan for this farm")
    return SeasonPlan.model_validate(plan)
