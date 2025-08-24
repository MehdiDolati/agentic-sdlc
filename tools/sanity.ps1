# tools/sanity.ps1
# Basic sanity check: ensure venv, install requirements, and run tests.

param(
  [switch]$SkipTests
)

Write-Host ">>> Running sanity checks..."

# Ensure venv exists
if (-Not (Test-Path ".venv/Scripts/python.exe")) {
    Write-Error "Python venv not found. Run: python -m venv .venv"
    exit 1
}

$VenvPython = ".venv/Scripts/python.exe"
$VenvPip    = ".venv/Scripts/pip.exe"

# Install dependencies
Write-Host ">>> Installing dependencies..."
& $VenvPip install -r services/api/requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency install failed"
}

if (-Not $SkipTests) {
    # Quick unit test run
    Write-Host ">>> Running unit tests..."
    & $VenvPython -m pytest -q services/api
    if ($LASTEXITCODE -ne 0) {
        throw "Sanity check failed - tests did not pass"
    }
}

Write-Host "Sanity checks passed"
