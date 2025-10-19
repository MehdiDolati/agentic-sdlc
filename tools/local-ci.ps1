param(
  [switch]$SkipDocker = $false,   # run just venv + tests
  [switch]$KeepRunning = $false   # leave containers up after smoke tests
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

# --- repo root ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Resolve-Path "$scriptDir\..")

Write-Host "== Local CI starting ==" -ForegroundColor Cyan

# --- ensure .venv + deps ---
$venvPy = ".\.venv\Scripts\python.exe"
if (!(Test-Path $venvPy)) {
  Write-Host "[venv] Creating .venv..." -ForegroundColor Cyan
  python -m venv .venv
}
& $venvPy -m pip install --upgrade pip wheel
& $venvPy -m pip install -r services\api\requirements.txt

# --- unit tests ---
Write-Host "== Running unit tests ==" -ForegroundColor Cyan
& $venvPy -m pytest -q services\api
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }

if (-not $SkipDocker) {
  # --- .env for compose (idempotent; won't overwrite if present) ---
  $envPath = ".env"
  if (!(Test-Path $envPath)) {
    @"
POSTGRES_DB=appdb
POSTGRES_USER=app
POSTGRES_PASSWORD=app
DB_HOST=db
DB_PORT=5432
DB_NAME=appdb
DB_USER=app
DB_PASSWORD=app
"@ | Out-File -FilePath $envPath -Encoding ascii -NoNewline
    Write-Host "[docker] Created .env" -ForegroundColor DarkGray
  }

  # --- bring up compose ---
  Write-Host "== docker compose up --build -d ==" -ForegroundColor Cyan
  docker compose up -d --build

  # --- wait for API /health ---
  $healthUrl = "http://127.0.0.1:8081/health"
  Write-Host "Waiting for API readiness at $healthUrl ..." -ForegroundColor DarkGray
  $max = 50; $ok = $false
  for ($i=1; $i -le $max; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
      if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 1 }
    Start-Sleep -Seconds 1
  }
  if (-not $ok) {
    Write-Host "`n[docker] API did not get healthy; last logs:" -ForegroundColor Red
    docker compose logs --no-color api | Select-Object -Last 200
    throw "API readiness check failed."
  }

  # --- smoke tests (read-only safe) ---
  Write-Host "== Smoke tests ==" -ForegroundColor Cyan

  $check = {
    param($url, $headers)
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -Headers $headers -TimeoutSec 5
    if ($r.StatusCode -ne 200) { throw "Smoke check failed: $url -> $($r.StatusCode)" }
  }

  & $check "http://127.0.0.1:8081/health" @{}
  & $check "http://127.0.0.1:8081/openapi.json" @{}
  & $check "http://127.0.0.1:8081/api/create" @{}
  & $check "http://127.0.0.1:8081/api/notes" @{ Authorization = "Bearer smoke" }

  Write-Host "Smoke tests ✅" -ForegroundColor Green

  if (-not $KeepRunning) {
    Write-Host "== docker compose down ==" -ForegroundColor Cyan
    docker compose down
  } else {
    Write-Host "Leaving containers up. (use 'docker compose down' when done)" -ForegroundColor Yellow
  }
}

Write-Host "`nAll checks passed ✅  Safe to push." -ForegroundColor Green
