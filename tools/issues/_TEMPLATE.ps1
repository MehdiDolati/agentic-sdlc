# tools/issues/_TEMPLATE.ps1
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$Issue,
  [Parameter(Mandatory=$true)][string]$VenvPython
)

$ErrorActionPreference = "Stop"
$root = (Get-Location).Path

# This is a skeleton. Replace contents to actually implement __TITLE__.
Write-Host "Implementing '__TITLE__' (Issue #$Issue, slug '__SLUG__')" -ForegroundColor Cyan

# Example: touch a marker (idempotent)
$newFile = Join-Path $root "tools/.issue-__ISSUE__-__SLUG__.done"
Set-Content $newFile "# completed at $(Get-Date -Format s)" -Encoding UTF8
