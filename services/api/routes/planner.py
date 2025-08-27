from fastapi import APIRouter
from planner.service import build_task_breakdown_prompt
from planner.prompt_templates import render_template

router = APIRouter(prefix="/planner")

@router.post("/plan")
def plan(req: PlanRequest):
    prompt = render_template("task_breakdown.md", {
        "goal": req.goal,
        "context": getattr(req, "context", None),
        "nfrs": getattr(req, "nfrs", None),
    })
    # LLM call…
    return {"prompt": prompt}
