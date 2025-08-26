# tools/auto-pilot.ps1  (Windows PowerShell 5 compatible)

param(
  [Parameter(Mandatory = $true)][string] $Repo,
  [int]       $MaxIssues    = 1,
  [string[]]  $Labels       = @(),   # optional
  [switch]    $OpenPR,
  [switch]    $DockerSmoke,
  [switch]    $AutoMerge,
  [switch]    $WaitForChecks,
  [switch]    $DryRun
)

if (-not $Repo -or [string]::IsNullOrWhiteSpace($Repo)) {
  $Repo = $env:REPO
}
if (-not $MaxIssues -or $MaxIssues -le 0) {
  $MaxIssues = [int]::TryParse($env:MAX, [ref]0) ? [int]$env:MAX : 2
}


function Fail($msg) { Write-Error $msg; exit 1 }

$ErrorActionPreference = 'Stop'

# Guard: gh CLI present
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Fail "GitHub CLI 'gh' not found. Install https://cli.github.com and run 'gh auth login'."
}
& gh auth status 1>$null 2>$null

# Optional global guard for CI (keeps workflow safe until explicitly enabled)
if (-not $DryRun -and -not $env:AUTOPILOT_ENABLE) {
  Write-Host "AUTOPILOT_ENABLE not set; exiting safely (use -DryRun to test locally)."
  exit 0
}

# Helper: run one issue through auto-issue.ps1
function Invoke-OneIssue([int]$IssueNumber) {
  $scriptPath = Join-Path $PSScriptRoot 'auto-issue.ps1'
  if (-not (Test-Path $scriptPath)) {
    Fail "Missing $scriptPath"
  }

  $argsList = @(
    '-Repo', $Repo,
    '-IssueNumber', $IssueNumber
  )

  if ($Labels -and $Labels.Count -gt 0) {
    # Pass as proper array to match [string[]] parameter
    $argsList += @('-Labels')
    $argsList += $Labels
  }
  if ($OpenPR)      { $argsList += '-OpenPR' }
  if ($DockerSmoke) { $argsList += '-DockerSmoke' }
  if ($WaitForChecks) { $argsList += '-WaitForChecks' }
  if ($AutoMerge)   { $argsList += '-AutoMerge' }

  if ($DryRun) {
    Write-Host "[DRY-RUN] tools/auto-issue.ps1 $($argsList -join ' ')"
    return
  }

  & $scriptPath @argsList
}

# Find candidate issues (oldest open, limited)
# Adjust the query/labels to your triage process as needed.
$jq = '.[].number'
$numbers = @()
try {
  $json = gh issue list -R $Repo --state open --sort created --limit $MaxIssues --json number | ConvertFrom-Json
  if ($json) {
    foreach ($it in $json) { $numbers += [int]$it.number }
  }
} catch {
  Fail "Failed to list issues via gh: $_"
}

if (-not $numbers -or $numbers.Count -eq 0) {
  Write-Host "No open issues found to process."
  exit 0
}

Write-Host "Processing issues: $($numbers -join ', ')"
foreach ($n in $numbers) {
  Invoke-OneIssue -IssueNumber $n
}

Write-Host "Autopilot completed."
