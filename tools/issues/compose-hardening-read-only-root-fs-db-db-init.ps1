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
$changed = $false

function Ensure-ReadOnly($serviceName) {
  param([string]$svc)
  $pattern = "(?ms)(^\s*$svc:\s*(?:\n.+?)*?)(?=^\s*[a-zA-Z0-9_-]+:|\Z)"
  $m = [regex]::Match($y, $pattern)
  if (-not $m.Success) { return }
  $block = $m.Groups[1].Value

  if ($block -notmatch "read_only:\s*true") {
    $block2 = $block.TrimEnd() + "`n  read_only: true`n  tmpfs:`n    - /var/run/postgresql`n"
    $script:changed = $true
    $script:y = $y -replace [regex]::Escape($block), [System.Text.RegularExpressions.Regex]::Escape($block2).Replace('\n',"`n")
  }
}

Ensure-ReadOnly "db"
Ensure-ReadOnly "db-init"

if ($script:changed) {
  Set-Content $compose $script:y -Encoding UTF8
  Write-Host "Added read_only + tmpfs to db/db-init." -ForegroundColor Green
} else {
  Write-Host "No changes needed (already read-only)." -ForegroundColor DarkYellow
}
