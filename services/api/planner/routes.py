from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from .prompt_templates import render_template

router = APIRouter(prefix="/planner", tags=["planner"])

class PlanRequest(BaseModel):
    goal: str
    context: Optional[str] = None
    nfrs: Optional[List[str]] = None

@router.post("/plan")
def plan(req: PlanRequest):
    prompt = render_template("task_breakdown.md", {
        "goal": req.goal,
        "context": req.context or "",
        "nfrs": "\n".join(req.nfrs or []),
    })
    # In the future, call LLM here and return its output.
    return {"prompt": prompt}
