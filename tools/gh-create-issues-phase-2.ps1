# tools/gh-create-issues.ps1
param(
  [string]$Repo,                  # optional: "owner/name". If omitted, auto-detect from git remote.
  [switch]$DryRun,                # optional: show what would run
  [hashtable[]]$Issues            # optional: array of @{ title=...; body=...; labels=@(...) }
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command '$name' not found. Please install it and retry."
  }
}

Require-Cmd gh
Require-Cmd git

# Ensure you're authenticated (will prompt if needed)
$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { gh auth login }

function Get-GitHubRepoSlug {
  $url = git config --get remote.origin.url 2>$null
  if (-not $url) { return $null }
  if ($url -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)') {
    return "$($matches.owner)/$($matches.repo)"
  }
  return $null
}

if (-not $Repo) { $Repo = Get-GitHubRepoSlug }
if (-not $Repo) { throw "Could not detect owner/repo. Pass -Repo 'owner/name' or run inside the repo clone." }

# Verify repo is reachable
gh repo view $Repo 1>$null 2>$null

# Ensure labels exist
$desiredLabels = @{
  "type:feature"      = "0E8A16"
  "type:bug"          = "D73A4A"
  "priority:normal"   = "C2E0C6"
  "priority:high"     = "B60205"
  "priority:low"      = "561F8A"
  "area:ui" 		  = "79ED76"
  "area:deployment"   = "E22CB4"
  "area:auth"         = "014751"
  "area:execution"    = "A86FCC"
  "area:cicd"		  = "01e986"
  "area:storage"	  = "AF1D21"
}

$existing = @()
try {
  $existing = (gh label list --repo $Repo --limit 200 --json name | ConvertFrom-Json).name
} catch { $existing = @() }

foreach ($kv in $desiredLabels.GetEnumerator()) {
  if ($existing -notcontains $kv.Key) {
    if ($DryRun) {
      Write-Host "[dry-run] would create label '$($kv.Key)'" -ForegroundColor Yellow
    } else {
      gh label create $kv.Key --repo $Repo --color $kv.Value | Out-Null
    }
  }
}

# Default issues if none passed in
if (-not $Issues -or $Issues.Count -eq 0) {
# Next batch of issues
	$issues = @(
    @{ title = "Multi-Agent Planning"
       body  = "Add support for multiple collaborating planner agents (e.g., one for PRD, one for OpenAPI, one for ADR). Aggregate into a single plan."
       labels= @("type:feature","area:planner","priority:low") }
	)
}

foreach ($i in $Issues) {
  $title  = [string]$i.title
  $body   = if ($i.ContainsKey('body'))   { [string]$i.body }   else { "" }
  $labels = if ($i.ContainsKey('labels')) { ($i.labels) -join "," } else { "" }

  if ($DryRun) {
    Write-Host "[dry-run] gh issue create --repo $Repo --title `"$title`" --label $labels" -ForegroundColor Yellow
  } else {
    gh issue create --repo $Repo --title $title --body $body --label $labels
  }
}