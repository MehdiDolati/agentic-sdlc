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
$compose = Join-Path $root "docker-compose.yml"
if (-not (Test-Path $compose)) { throw "docker-compose.yml not found" }

$y = Get-Content $compose -Raw

function Ensure-NoNewPriv($serviceName) {
  param([string]$svc)
  $pattern = "(?ms)(^\s*$svc:\s*(?:\n.+?)*?)(?=^\s*[a-zA-Z0-9_-]+:|\Z)"
  $m = [regex]::Match($y, $pattern)
  if (-not $m.Success) { return }
  $block = $m.Groups[1].Value
  if ($block -match "security_opt:\s*\n\s*-\s*no-new-privileges:true") { return }

  if ($block -match "security_opt:\s*\n") {
    $block2 = $block -replace "security_opt:\s*\n", "security_opt:`n  - no-new-privileges:true`n"
  } else {
    $block2 = $block.TrimEnd() + "`n  security_opt:`n    - no-new-privileges:true`n"
  }
  $script:changed = $true
  $script:y = $y -replace [regex]::Escape($block), [System.Text.RegularExpressions.Regex]::Escape($block2).Replace('\n',"`n")
}

$changed = $false
Ensure-NoNewPriv "db"
Ensure-NoNewPriv "db-init"

if ($script:changed) {
  Set-Content $compose $script:y -Encoding UTF8
  Write-Host "Updated security_opt for db/db-init." -ForegroundColor Green
} else {
  Write-Host "No changes needed (already hardened)." -ForegroundColor DarkYellow
}
