from pathlib import Path
from datetime import datetime
import re
import yaml

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text[:60] or "request"

def _today() -> str:
    return datetime.utcnow().strftime("%Y%m%d")

def _load_yaml(p: Path):
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _selected_stack(repo_root: Path) -> dict:
    cfg_dir = repo_root / "configs"
    runtime = _load_yaml(cfg_dir / "runtime-config.yaml")
    stack_cfg = _load_yaml(cfg_dir / "STACK_CONFIG.yaml")
    team = _load_yaml(cfg_dir / "TEAM_PROFILE.yaml")

    stack = runtime.get("stack") or {}
    if not stack:
        stack = {
            "language": (stack_cfg.get("languages") or ["python"])[0],
            "framework": (stack_cfg.get("frameworks", {}).get("web") or ["fastapi"])[0],
            "frontend": "nextjs",
            "database": (stack_cfg.get("db") or ["postgres"])[0],
            "deployment": (stack_cfg.get("deploy") or ["docker"])[0],
        }

    gates = {
        "coverage_gate": (team.get("policies") or {}).get("coverage_gate", 0.8),
        "risk_threshold": (team.get("policies") or {}).get("risk_threshold", "medium"),
        "approvals": (team.get("policies") or {}).get("approvals", {}),
    }

    return {"stack": stack, "gates": gates}

def _derive_requirements(request_text: str):
    text = request_text.lower()
    must = ["Implement the primary endpoint(s) described by the request",
            "Write unit tests with coverage above the gate"]
    should = ["Add basic error handling and input validation"]
    could = ["Add OpenAPI docs and a simple UI stub"]
    if "auth" in text or "login" in text:
        must.append("Add authentication flow (basic token or session)")
    if "search" in text:
        should.append("Provide a search parameter on list endpoint")
    if "export" in text:
        could.append("Add export endpoint (CSV/JSON)")
    return must, should, could

def _acceptance_criteria(request_text: str):
    return [
        "Given the service is running, When I call the primary endpoint, Then I receive a 200 response.",
        "Given invalid input, When I call the endpoint, Then I receive a 4xx response with an error body."
    ]

def plan_request(request_text: str, repo_root: Path) -> dict:
    slug = _slugify(request_text.splitlines()[0] if request_text else "request")
    date = _today()

    selection = _selected_stack(repo_root)
    stack = selection["stack"]
    gates = selection["gates"]

    prd_dir = repo_root / "docs" / "prd"
    adr_dir = repo_root / "docs" / "adr"
    stories_dir = repo_root / "docs" / "stories"
    plans_dir = repo_root / "docs" / "plans"
    for d in (prd_dir, adr_dir, stories_dir, plans_dir):
        d.mkdir(parents=True, exist_ok=True)

    must, should, could = _derive_requirements(request_text)
    criteria = _acceptance_criteria(request_text)
    prd_path = prd_dir / f"PRD-{date}-{slug}.md"
    prd_md = f"""
    # Product Requirements Document — {request_text[:80]}

    ## Problem
    {request_text.strip() or "User request describing desired functionality."}

    ## Goals / Non-goals
    - **Goals**: Deliver the requested functionality with tests and docs.
    - **Non-goals**: Features not explicitly requested; large-scale infra changes.

    ## Personas & Scenarios
    - Primary Persona: End-user
    - Scenario: A user interacts with the system to accomplish: "{request_text.strip()}"

    ## Requirements (Must / Should / Could)
    **Must**
    {chr(10).join(f"- {item}" for item in must)}

    **Should**
    {chr(10).join(f"- {item}" for item in should)}

    **Could**
    {chr(10).join(f"- {item}" for item in could)}

    ## Acceptance Criteria
    {chr(10).join(f"- {c}" for c in criteria)}

    ## Stack Summary (Selected)
    - Language: **{stack.get('language','')}**
    - Backend Framework: **{stack.get('framework','')}**
    - Frontend: **{stack.get('frontend','')}**
    - Database: **{stack.get('database','')}**
    - Deployment: **{stack.get('deployment','')}**

    ## Quality & Policy Gates
    - Coverage gate: **{gates.get('coverage_gate')}**
    - Risk threshold: **{gates.get('risk_threshold')}**
    - Approvals: **{gates.get('approvals')}**

    ## Risks & Assumptions
    - Assumes default adapters and templates for the chosen stack are available.
    - Security scanning and policy checks run in CI before deploy.
    """
    prd_path.write_text(prd_md.strip() + "\n", encoding="utf-8")

    adr_path = adr_dir / f"ADR-{date}-auto-planning.md"
    adr_md = f"""
    # Architecture Decision Record — Auto Planning
    ## Context
    Initial design decision for request: {request_text[:80]}

    ## Decision
    Use selected stack from runtime config (or defaults). Document deviations via follow-up ADRs.

    ## Alternatives
    - Alternate frameworks or data stores per profile

    ## Consequences
    - Provides a baseline to iterate on in subsequent cycles.
    """
    adr_path.write_text(adr_md.strip() + "\n", encoding="utf-8")

    stories_path = stories_dir / f"USER_STORIES-{date}-{slug}.yaml"
    stories = [
        {
            "id": "US-0001",
            "persona": "end-user",
            "story": f"As an end-user, I want {request_text[:60]} so that I can achieve the desired outcome.",
            "acceptance_criteria": _acceptance_criteria(request_text),
            "priority": "Must",
            "estimates": {"size": "S", "confidence": 0.6},
        }
    ]
    stories_yaml = yaml.safe_dump(stories, sort_keys=False, allow_unicode=True)
    stories_path.write_text(stories_yaml, encoding="utf-8")

    tasks_path = plans_dir / f"TASKS-{date}-{slug}.md"
    tasks_md = f"""
    # Task Plan — {request_text[:80]}

    - [ ] Clarify detailed acceptance criteria
    - [ ] Define API contract (OpenAPI)
    - [ ] Implement endpoint(s)
    - [ ] Write unit tests (meet coverage gate {gates.get('coverage_gate')})
    - [ ] Add integration tests (optional for MVP)
    - [ ] Update USER_MANUAL & CHANGELOG
    - [ ] Run CI; ensure gates pass (security, secrets scan)
    - [ ] Prepare deploy (staging)
    """
    tasks_path.write_text(tasks_md.strip() + "\n", encoding="utf-8")

    def rel(p: Path) -> str:
        return str(p.relative_to(repo_root).as_posix())

    return {
        "prd": rel(prd_path),
        "adr": rel(adr_path),
        "stories": rel(stories_path),
        "tasks": rel(tasks_path),
    }
