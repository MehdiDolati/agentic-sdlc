param(
  [string]$Repo,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Import-Module "$PSScriptRoot\..\Agentic.Tools.psm1" -Force

$py = Get-VenvPython
Invoke-ApiUnitTests

if ($DockerSmoke) { Invoke-DockerSmoke }

$ErrorActionPreference = "Stop"
$root = (Get-Location).Path

# Directories
$promptsDir = Join-Path $root "services/api/prompts"
$goldenDir  = Join-Path $root "services/api/tests/golden"
New-Item -ItemType Directory -Force $promptsDir | Out-Null
New-Item -ItemType Directory -Force $goldenDir  | Out-Null

# PRD + OpenAPI prompt skeletons (idempotent create)
$prd = @"
{{ system | default('You are a senior product manager.') }}
Write a concise PRD for: "{{ request }}"

Sections:
- Summary
- Goals/Non-goals
- Requirements
- API (high-level)
- Risks & Open Questions
"@
$openapi = @"
{{ system | default('You are a senior backend engineer.') }}
Generate OpenAPI 3.1 YAML for the service described:

{{ prd }}

Constraints:
- FastAPI compatible
- Components: schemas
- Security if auth is present
"@

$prdPath     = Join-Path $promptsDir "prd.j2"
$openapiPath = Join-Path $promptsDir "openapi.j2"
if (-not (Test-Path $prdPath))     { Set-Content $prdPath $prd -Encoding UTF8 }
if (-not (Test-Path $openapiPath)) { Set-Content $openapiPath $openapi -Encoding UTF8 }

# Golden test fixtures (placeholder)
$goldenPrd = Join-Path $goldenDir "notes_prd.md"
$goldenOAS = Join-Path $goldenDir "notes_openapi.yaml"
if (-not (Test-Path $goldenPrd)) { Set-Content $goldenPrd "# Notes Service PRD (golden)" -Encoding UTF8 }
if (-not (Test-Path $goldenOAS)) { Set-Content $goldenOAS "openapi: 3.1.0" -Encoding UTF8 }

Write-Host "Planner prompts + golden fixtures prepared." -ForegroundColor Green
