from fastapi import APIRouter

from backend.memory.store import get_alerts
from backend.tools.plan_conflicts import check_plan_conflicts

router = APIRouter()


@router.post("/api/plan/{farm_id}/check")
async def check_plan(farm_id: str) -> dict:
    return check_plan_conflicts(farm_id)


@router.get("/api/plan/{farm_id}/alerts")
async def plan_alerts(farm_id: str) -> dict:
    return {"farm_id": farm_id, "alerts": get_alerts(farm_id)}
