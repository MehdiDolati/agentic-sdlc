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