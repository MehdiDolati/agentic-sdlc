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

## Quickstart (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r orchestrator\requirements.txt
pip install -r services\api\requirements.txt
uvicorn services.api.app:app --reload
```
Then POST a request:
```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/requests' -Method Post -ContentType 'application/json' -Body (@{text="Build a notes service with auth"} | ConvertTo-Json)
```

## Planner (PRD/ADR/Stories/Tasks + OpenAPI)
The Planner generates **PRD**, **ADR**, **User Stories**, **Task Plan**, and an **OpenAPI skeleton** under `docs/`.

## Dev Agent (scaffold from OpenAPI)
Scaffold CRUD endpoints + tests from a generated OpenAPI spec.

```powershell
# from repo root (Windows)
.venv\Scripts\activate.bat
pip install -r tools\requirements.txt

# pick your generated spec (from /requests call)
$spec = Get-ChildItem docs\api\generated\openapi-*.yaml | Select-Object -Last 1 | % { $_.FullName }

python tools\dev_agent.py --spec $spec

# run tests
pytest -q services\api

# start API
uvicorn services.api.app:app --reload
```
To also commit on a branch (and open a PR with GitHub CLI if configured):
```powershell
python tools\dev_agent.py --spec $spec --git --pr
```
