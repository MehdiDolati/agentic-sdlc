# tools/issues/_TEMPLATE.ps1
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$false)][string]$Body,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)


$ErrorActionPreference = "Stop"
$root = (Get-Location).Path

# This is a skeleton. Replace contents to actually implement .
Write-Host "Implementing '' (Issue #$Issue, slug '__SLUG__')" -ForegroundColor Cyan

# Example: touch a marker (idempotent)
$newFile = Join-Path $root "tools/.issue-__ISSUE__-__SLUG__.done"
Set-Content $newFile "# completed at $(Get-Date -Format s)" -Encoding UTF8
