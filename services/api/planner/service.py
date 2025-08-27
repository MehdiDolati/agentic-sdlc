from planner.prompt_templates import render_template

def build_task_breakdown_prompt(goal: str, context: str | None, nfrs: list[str] | None) -> str:
    return render_template("task_breakdown.md", {
        "goal": goal,
        "context": context,
        "nfrs": nfrs or [],
    })
