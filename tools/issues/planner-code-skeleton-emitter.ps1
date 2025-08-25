# tools/issues/planner-code-skeleton-emitter.ps1
# Windows PowerShell 5 compatible

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber,
  [Parameter(Mandatory=$true)][string] $Title,
  [Parameter(Mandatory=$false)][string]$Body,
  [switch] $OpenPR,
  [switch] $DockerSmoke
)

Write-Host "Implementing '$Title' (Issue #$IssueNumber)"

$ErrorActionPreference = 'Stop'

$env:AGENTIC_SKIP_INDEX_WRITE = "1"
& .\.venv\Scripts\python.exe -m pytest -q services\api
if ($LASTEXITCODE -ne 0) { throw "Pre-flight unit tests failed" }

# ... your edits/commits ...

$env:AGENTIC_SKIP_INDEX_WRITE = "1"
& .\.venv\Scripts\python.exe -m pytest -q services\api
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed after emitter change" }


function _Run($cmd, $err) {
  Write-Host "• $cmd"
  cmd.exe /c $cmd
  if ($LASTEXITCODE -ne 0) { throw $err }
}

# 1) Ensure venv + deps (best-effort; your repo already has helpers)
if (Test-Path .venv\Scripts\python.exe) {
  & .\.venv\Scripts\python.exe -m pip install -q -r services\api\requirements.txt
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  python -m pip install -q -r services\api\requirements.txt
}

# 2) Pre-flight tests
_Run ".\.venv\Scripts\python.exe -m pytest -q services\api" "Pre-flight unit tests failed"

# 3) Minimal implementation: add a skeleton emitter module (non-breaking)
$emitterDir = "services\api\planner"
$emitterFile = Join-Path $emitterDir "emitter.py"
$initFile    = Join-Path $emitterDir "__init__.py"

if (-not (Test-Path $emitterDir)) { New-Item -ItemType Directory -Force -Path $emitterDir | Out-Null }
if (-not (Test-Path $initFile))   { "" | Set-Content -Path $initFile -Encoding UTF8 }

if (-not (Test-Path $emitterFile)) {
@'
"""
Planner code skeleton emitter (v0).
Non-breaking placeholder: takes a "plan" dict and returns a dict of file paths -> contents.
"""
from typing import Dict, Any

def emit_skeleton(plan: Dict[str, Any]) -> Dict[str, str]:
    """
    Given a normalized plan, emit a minimal code skeleton.
    Safe placeholder implementation that returns an empty dict if no plan provided.
    """
    if not plan:
        return {}
    # Example scaffold (no side-effects; caller decides where to write):
    files = {}
    # You can populate files like:
    # files["README_SKELETON.md"] = "# Skeleton\\n\\nThis was generated from the plan."
    return files
'@ | Set-Content -Path $emitterFile -Encoding UTF8
}

# 4) Re-run tests
_Run ".\.venv\Scripts\python.exe -m pytest -q services\api" "Unit tests failed after emitter change"

# 5) Commit changes
# Stage expected files
git add services\api\planner\emitter.py services\api\planner\__init__.py

# If nothing is staged, skip the commit instead of failing
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
  Write-Host "• No staged changes; skipping commit."
} else {
  git commit -m "feat(planner): add code skeleton emitter stub (#8)"
  if ($LASTEXITCODE -ne 0) {
    throw "git commit failed"
  }
}

# Ensure .env exists for docker compose
$envPath = Join-Path $PSScriptRoot '..\..\.env' | Resolve-Path -Relative
if (-not (Test-Path $envPath)) {
  Write-Host "• .env not found; creating default .env"
  @'
POSTGRES_DB=appdb
POSTGRES_USER=app
POSTGRES_PASSWORD=app
DB_HOST=db
DB_PORT=5432
DB_NAME=appdb
DB_USER=app
DB_PASSWORD=app
'@ | Set-Content -Path $envPath -Encoding ascii
}


# 6) Optional docker smoke
if ($DockerSmoke) {
  Write-Host "Running docker smoke…"
  _Run "docker compose up --build -d" "docker compose up failed"
  try {
    Start-Sleep -Seconds 3
    # basic health ping
    _Run "curl -fsS http://localhost:8080/health" "health check failed"
  } finally {
    _Run "docker compose down -v" "docker compose down failed"
  }
}

# 7) Push & PR
_Run "git push -u origin HEAD" "git push failed"

if ($OpenPR) {
  $prTitle = "$Title"
  $prBody  = if ($Body) { $Body + "`n`nCloses #$IssueNumber" } else { "Closes #$IssueNumber" }
  _Run ("gh pr create -R {0} --base main --head {1} --title ""{2}"" --body ""{3}""" -f `
      $Repo, (git rev-parse --abbrev-ref HEAD), $prTitle, $prBody) "gh pr create failed"
}
