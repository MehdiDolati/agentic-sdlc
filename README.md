# Agentic SDLC Starter (Configurable & Runtime-Specialized)

This repository bootstraps an autonomous, agentic software team that can execute a full SDLC for user requests.
It includes:
- Configurable **stack profiles** and **agent specializations** via YAML
- Orchestrator stubs (Planner/Registry/Capability Graph)
- FastAPI service + sample tests
- Planner that generates PRD/ADR/Stories/Tasks **and OpenAPI 3.1**
- **Plans API** for traceability (`/plans` & `/plans/{id}`)
- **Dev Agent** that scaffolds FastAPI routes + tests from OpenAPI
- **QA Agent** that enforces coverage gate
- GitHub Actions CI (tests + coverage + QA gate) and a basic secret scan

> Generated on: 2025-08-22

## Quickstart (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r orchestrator\requirements.txt
pip install -r services\api\requirements.txt
uvicorn services.api.app:app --reload
```

Submit a request:
```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/requests' -Method Post -ContentType 'application/json' -Body (@{text="Build a notes service with auth"} | ConvertTo-Json)
```

## Planner (PRD/ADR/Stories/Tasks + OpenAPI)
Artifacts appear under `docs/` (including an OpenAPI skeleton under `docs/api/generated/`).

## Plans API
After you `POST /requests`, the server stores a plan entry and returns a `plan_id`.
- `GET /plans` — list recent plans
- `GET /plans/{id}` — fetch a specific plan with artifact paths

## Dev Agent (scaffold from OpenAPI)
Scaffold CRUD endpoints + tests from a generated OpenAPI spec.

```powershell
# from repo root (Windows)
. .\.venv\Scripts\activate.ps1
pip install -r tools\requirements.txt

# pick your generated spec (from /requests call)
$spec = (Get-ChildItem .\docs\api\generated\openapi-*.yaml | Select-Object -Last 1).FullName

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

## QA Agent (coverage gate)
Enforce coverage gate from `TEAM_PROFILE.yaml` locally or in CI.

```powershell
. .\.venv\Scripts\activate.ps1
pip install -r tools\requirements.txt
python tools\qa_agent.py --strict
# or reuse existing XML
python tools\qa_agent.py --strict --xml reports\coverage.xml
```
