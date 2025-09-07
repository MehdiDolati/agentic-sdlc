<# 
 Fast local CI for pre-push:
 - Lint with Ruff if available (skips if not installed)
 - Run unit tests (services/api)
 - Optional Docker smoke with -WithDockerSmoke switch

 Usage (manual):
   pwsh -File tools/local-lint-and-test.ps1
   pwsh -File tools/local-lint-and-test.ps1 -WithDockerSmoke
#>

[CmdletBinding()]
param(
  [switch]$WithDockerSmoke
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Section([string]$msg) {
  Write-Host ""
  Write-Host "== $msg ==" -ForegroundColor Cyan
}

function Fail([string]$msg) {
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

# Resolve python from venv if present; otherwise fall back to PATH
$python = $null
$venvPy = Join-Path -Path ".\.venv\Scripts" -ChildPath "python.exe"
if (Test-Path $venvPy) {
  $python = $venvPy
} else {
  $python = "python"
}

Section "Fast checks"

# Lint (skip if ruff not present)
try {
  if (Get-Command ruff -ErrorAction SilentlyContinue) {
    Section "Lint (ruff)"
    ruff --version | Out-Host
    ruff check services/api
  } else {
    Write-Host "(ruff not found; skipping lint)" -ForegroundColor Yellow
  }
} catch {
  Fail "Lint failed."
}

# Unit tests
Section "Unit tests (pytest)"
& $python -m pytest -q services\api
if ($LASTEXITCODE -ne 0) { Fail "Unit tests failed." }

Write-Host "`n== UI route smoke =="
python - <<'PY'
import requests, os
base = os.environ.get("API_BASE","http://127.0.0.1:8080")
try:
    r = requests.get(base + "/ui/plans", timeout=3)
    print("GET /ui/plans ->", r.status_code)
except Exception as e:
    print("UI smoke skipped (server not running):", e)
PY
Write-Host ""
Write-Host "== UI smoke (docker + curl) =="

# Build & start (best-effort; leave running briefly for smoke)
docker compose up -d --build

# Wait for API to be healthy
$healthUrl = "http://127.0.0.1:8080/health"
$max = 60
for ($i=0; $i -lt $max; $i++) {
  try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { break }
  } catch {}
  Start-Sleep -Seconds 1
}
if ($i -ge $max) {
  Write-Error "Timed out waiting for API health."
  exit 1
}

# Seed a plan to ensure UI has content
$reqBody = @{ text = "UI smoke seed plan" } | ConvertTo-Json
$resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/requests" -Body $reqBody -ContentType "application/json"
$planId = $resp.plan_id
if (-not $planId) { Write-Error "Failed to create plan for UI smoke."; exit 1 }

# Check list page contains the header
$listHtml = Invoke-WebRequest -Uri "http://127.0.0.1:8080/ui/plans" -UseBasicParsing
if ($listHtml.Content -notmatch "<h1>Plans</h1>") {
  Write-Error "UI /ui/plans missing header"
  exit 1
}

# Check detail page contains the header + PRD/OpenAPI sections
$detailHtml = Invoke-WebRequest -Uri "http://127.0.0.1:8080/ui/plans/$planId" -UseBasicParsing
$must = @("<h1>Plan</h1>", "<h2>PRD</h2>", "<h2>OpenAPI</h2>")
foreach ($m in $must) {
  if ($detailHtml.Content -notmatch [regex]::Escape($m)) {
    Write-Error "UI /ui/plans/$planId missing: $m"
    exit 1
  }
}

Write-Host "UI smoke passed."

# Optional Docker smoke
if ($WithDockerSmoke) {
  Section "Docker smoke (compose up + health probe)"
  $env:COMPOSE_DOCKER_CLI_BUILD = "1"
  $env:DOCKER_BUILDKIT = "1"

  docker compose up -d --build

  # Wait for API health
  $healthUrl = "http://127.0.0.1:8080/health"
  $maxTries  = 40
  $sleepSec  = 1
  $ok = $false
  for ($i = 1; $i -le $maxTries; $i++) {
    try {
      $res = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $healthUrl
      if ($res.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
    Start-Sleep -Seconds $sleepSec
  }

  if (-not $ok) {
    Write-Host "`n[docker] API did not get healthy; last logs:" -ForegroundColor Yellow
    docker logs agentic-sdlc-api 2>$null | Select-Object -Last 60 | Out-Host
    docker logs agentic-sdlc-db  2>$null | Select-Object -Last 40 | Out-Host
    docker compose down -v
    Fail "API readiness check failed."
  }

  Write-Host "Health OK."
  docker compose down -v
}

Section "All good ✅"
exit 0
