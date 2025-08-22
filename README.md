# Agentic SDLC Starter (Configurable & Runtime-Specialized)

This repository bootstraps an autonomous, agentic software team that can execute a full SDLC for user requests.
It includes:
- Configurable **stack profiles** and **agent specializations** via YAML
- Orchestrator stubs (Planner/Registry/Capability Graph)
- FastAPI service + sample tests
- Optional Next.js web skeleton
- Policy-as-code gates and GitHub Actions CI
- Documentation templates (PRD, ADR, Test Plan, Runbook, User Manual)

> Generated on: 2025-08-22

## Quickstart
```bash
git init
git add .
git commit -m "chore: bootstrap agentic SDLC starter"
git branch -M main
git remote add origin git@github.com:<YOUR_USERNAME>/agentic-sdlc-starter.git
git push -u origin main

# (Windows)
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r orchestrator\requirements.txt
pip install -r services\api\requirements.txt
uvicorn services.api.app:app --reload
```

## Planner (auto-generates PRD/ADR/Stories/Tasks)
Submit a request and the system will generate artifacts under `docs/`:

```bash
curl -X POST "http://127.0.0.1:8000/requests" -H "Content-Type: application/json" -d "{"text":"Build a notes service with auth"}"
```

Artifacts created:
- `docs/prd/PRD-YYYYMMDD-<slug>.md` (now **enriched** with stack summary & policy gates)
- `docs/adr/ADR-YYYYMMDD-auto-planning.md`
- `docs/stories/USER_STORIES-YYYYMMDD-<slug>.yaml`
- `docs/plans/TASKS-YYYYMMDD-<slug>.md`
