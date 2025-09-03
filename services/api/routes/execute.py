from fastapi import APIRouter, BackgroundTasks
from ..app import execute_plan as _execute_plan

router = APIRouter()

@router.post("/plans/{plan_id}/execute")
def execute_plan_route(plan_id: str, background: BackgroundTasks):
    # Delegate to the canonical implementation in app.py
    return _execute_plan(plan_id, background)