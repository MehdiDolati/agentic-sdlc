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
# 1) Create a public repo on GitHub named agentic-sdlc-starter (or any name you prefer)
# 2) Initialize locally
git init
git add .
git commit -m "chore: bootstrap agentic SDLC starter"
# 3) Add remote and push
#    Replace <YOUR_USERNAME> and repo name as needed
git branch -M main
git remote add origin git@github.com:<YOUR_USERNAME>/agentic-sdlc-starter.git
git push -u origin main

# 4) (Optional) Run API service
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

## Structure
```
.
├── .github/workflows/
├── configs/
├── docs/
├── orchestrator/
├── services/
│   ├── api/         # FastAPI sample
│   └── web/         # Next.js (minimal placeholder)
├── infra/
│   └── terraform/   # placeholders
├── security/
└── tools/
```

## Notes
- CI reads gates (coverage, security) from `configs/TEAM_PROFILE.yaml`.
- Policies (OPA, basic secret scanning) run in PR workflows.
- Extend orchestrator to route tasks to specialized agents at runtime.
