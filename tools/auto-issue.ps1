# tools/auto-issue.ps1
# Purpose: Create/checkout an issue branch only. No PR here.

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber
)

function Fail($msg){ Write-Error $msg; exit 1 }

# Non-interactive hardening
$ErrorActionPreference     = 'Stop'
$ProgressPreference        = 'SilentlyContinue'
$env:GIT_ASKPASS           = "echo"
$env:GIT_TERMINAL_PROMPT   = "0"
$env:GIT_EDITOR            = "true"
$env:GH_PROMPT_DISABLED    = "1"
$env:GH_NO_UPDATE_NOTIFIER = "1"

# Preconditions
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found in PATH." }
if (-not (Get-Command gh  -ErrorAction SilentlyContinue)) { Fail "GitHub CLI 'gh' not found." }

# Use GH_TOKEN or existing gh login
if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN) -and [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $env:GH_TOKEN = $env:GITHUB_TOKEN
}
if (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $null = & gh api user --jq .login 2>$null
  if ($LASTEXITCODE -ne 0) { Fail "GH_TOKEN provided but invalid/insufficient scope. Need 'repo' & 'workflow'." }
} else {
  & gh auth status 1>$null 2>$null
}

# Must run inside git repo & clean tree
try { & git rev-parse --is-inside-work-tree 1>$null 2>$null } catch { Fail "Run from inside a git repository." }
$dirty = git status --porcelain
if ($dirty) { Fail "Working tree is dirty. Commit or stash before continuing." }

# Fetch issue info for slug
$title = & gh api "repos/$Repo/issues/$IssueNumber" --jq .title 2>$null
if ([string]::IsNullOrWhiteSpace($title)) { Fail "Unable to fetch issue #$IssueNumber from $Repo." }

function New-Slug([string]$s){
  $s = $s.ToLower()
  $s = ($s -replace '[^a-z0-9]+','-').Trim('-')
  if ($s.Length -gt 64) { $s = $s.Substring(0,64).Trim('-') }
  return $s
}

$slug       = New-Slug $title
$branchName = "issue-$IssueNumber-$slug"

# Create or checkout the branch
$exists = & git rev-parse --verify --quiet "refs/heads/$branchName" 2>$null
if ($LASTEXITCODE -eq 0) {
  Write-Host "Checking out existing branch: $branchName"
  & git checkout "$branchName" | Out-Null
} else {
  Write-Host "Creating new branch: $branchName"
  & git checkout -b "$branchName" | Out-Null
}

Write-Host "Branch ready: $branchName"
