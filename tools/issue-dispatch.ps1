# tools/issue-dispatch.ps1
# Windows PowerShell 5 compatible (no ?. null-conditional etc.)

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo = "MehdiDolati/agentic-sdlc",
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [switch] $OpenPR,
  [switch] $DockerSmoke
)

function Fail($msg) {
  Write-Error $msg
  exit 1
}

# --- Preconditions -----------------------------------------------------------
$ErrorActionPreference = 'Stop'

# Ensure gh exists
$gh = (Get-Command gh -ErrorAction SilentlyContinue)
if (-not $gh) {
  Fail "GitHub CLI 'gh' not found. Install from https://cli.github.com and try again."
}

# Ensure gh is authenticated
try {
  & gh auth status 1>$null 2>$null
} catch {
  Fail "Not logged in to GitHub CLI. Run: gh auth login"
}

# --- Fetch issue -------------------------------------------------------------
Write-Host "Fetching issue #$IssueNumber from $Repo..."
try {
  $json = & gh api "repos/$Repo/issues/$IssueNumber" --jq . 2>$null
} catch {
  Fail "Error contacting api.github.com. Check network or 'gh auth status'."
}

if (-not $json) { Fail "Empty response for issue #$IssueNumber. Network/auth problem?" }

$issue = $json | ConvertFrom-Json
$title = [string]$issue.title
$body  = [string]$issue.body

if ([string]::IsNullOrWhiteSpace($title)) {
  Fail "Issue #$IssueNumber has no title (or fetch failed)."
}

# --- Slugify title -> script name -------------------------------------------
function New-Slug([string]$s) {
  $s = $s.ToLower()
  $s = ($s -replace '[^a-z0-9]+','-').Trim('-')
  if ($s.Length -gt 64) { $s = $s.Substring(0,64).Trim('-') }
  return $s
}

$slug = New-Slug $title
$issueScriptDir = Join-Path $PSScriptRoot "issues"
$issueScript = Join-Path $issueScriptDir "$slug.ps1"
$template = Join-Path $issueScriptDir "_template.ps1"

if (-not (Test-Path $issueScriptDir)) {
  New-Item -ItemType Directory -Force -Path $issueScriptDir | Out-Null
}

if (-not (Test-Path $template)) {
  # minimal template if missing
  @'
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$false)][string]$Body,
  [switch]$OpenPR,
  [switch]$DockerSmoke
)

Write-Host ">>> Running issue script for #$IssueNumber: $Title"

# TODO: implement actual work here. Below is a common pattern most issue scripts need:

# 1) Ensure venv + deps
# & tools/sanity.ps1  # optional if you have it
# 2) Run unit tests before making changes (quick safety)
# python -m pytest -q services/api
# if ($LASTEXITCODE -ne 0) { throw "Pre-test failed" }

# 3) Make changes (edit files / generate code)
# 4) Re-run tests + optional docker smoke
# 5) Create a feature branch + commit
# 6) Open PR (if -OpenPR)

Write-Host "<<< Done (template)"
'@ | Set-Content -Path $template -Encoding UTF8
}

if (-not (Test-Path $issueScript)) {
  Write-Host "No script found for '$title' -> $slug. Creating from template…"
  Copy-Item $template $issueScript -Force
  $rel = Resolve-Path -Relative $issueScript
  git add $rel | Out-Null
  git commit -m "chore(issues): add script for #$IssueNumber $title" | Out-Null
}

Write-Host "=== Processing #${IssueNumber}: $title ==="

# --- Git pre-checks & branch create/checkout ---------------------------------
# Ensure git exists
$git = (Get-Command git -ErrorAction SilentlyContinue)
if (-not $git) {
  Fail "git not found in PATH. Install Git and try again."
}

# Ensure we are inside a git repository
try {
  & git rev-parse --is-inside-work-tree 1>$null 2>$null
} catch {
  Fail "Not inside a git repository. Run this from your repo root."
}

# Helper: is working tree clean?
function Test-GitClean {
  $status = & git status --porcelain
  if ($LASTEXITCODE -ne 0) { return $false }
  return [string]::IsNullOrWhiteSpace($status)
}

# Require a clean tree before switching/creating branches
if (-not (Test-GitClean)) {
  Fail "Working tree has uncommitted changes. Commit or stash before dispatching."
}

# Compose branch name from issue + slug
$branchName = "issue-$IssueNumber-$slug"

# If branch exists, checkout; else create from current HEAD
$existing = & git rev-parse --verify --quiet "refs/heads/$branchName"
if ($LASTEXITCODE -eq 0) {
  Write-Host "Checking out existing branch: $branchName"
  & git checkout "$branchName" | Out-Null
} else {
  Write-Host "Creating new branch: $branchName"
  & git checkout -b "$branchName" | Out-Null
}

# Track the branch name for later steps
$env:AGENTIC_CURRENT_BRANCH = $branchName

# --- Invoke the issue script with a standard param set -----------------------
$invokeParams = @{
  Repo        = $Repo
  IssueNumber = $IssueNumber
  Title       = $title
  Body        = $body
}
if ($OpenPR)     { $invokeParams.OpenPR = $true }
if ($DockerSmoke){ $invokeParams.DockerSmoke = $true }

& $issueScript @invokeParams
$exit = $LASTEXITCODE

if ($exit -ne 0) {
  Fail "Issue script failed with exit code $exit"
} else {
  Write-Host "✅ Issue #$IssueNumber script completed."

  if ($OpenPR) {
    $head = (git rev-parse --abbrev-ref HEAD).Trim()
    Import-Module "$PSScriptRoot/Agentic.Tools.psm1" -Force
    Ensure-PrBodyHasClose -Repo $Repo -HeadBranch $head -IssueNumber $IssueNumber -Title $title -Body $body
  }
}

# --- Post-run: commit, push, optionally open PR -------------------------------
# Stage any changes (issue script may have created/edited files)
& git add -A

# If there are staged changes, commit them
$diffIndex = & git diff --cached --name-only
if (-not [string]::IsNullOrWhiteSpace($diffIndex)) {
  $commitMsg = "Resolve #$IssueNumber: $title"
  Write-Host "Committing changes: $commitMsg"
  & git commit -m "$commitMsg" | Out-Null
} else {
  Write-Host "No changes to commit."
}

# Ensure remote exists
$remoteCheck = & git remote
if ([string]::IsNullOrWhiteSpace($remoteCheck)) {
  Fail "No git remotes configured. Add a remote (e.g., 'origin') and re-run."
}

# Ensure upstream & push safely
$branch = if ($env:AGENTIC_CURRENT_BRANCH) { $env:AGENTIC_CURRENT_BRANCH } else { (& git rev-parse --abbrev-ref HEAD).Trim() }
$hasUpstream = & git rev-parse --symbolic-full-name --abbrev-ref "$branch@{u}" 2>$null

if (-not $hasUpstream) {
  Write-Host "Setting upstream and pushing $branch…"
  & git push -u origin $branch | Out-Null
} else {
  Write-Host "Rebasing on remote and pushing $branch…"
  & git pull --rebase origin $branch | Out-Null
  & git push | Out-Null
}


# Optionally open PR
if ($OpenPR) {
  Write-Host "Opening PR via GitHub CLI…"
  # PR title mirrors the commit; body auto-closes the issue
  $prTitle = ${"Resolve #$IssueNumber: $title"}
  $prBody  = ${"This PR implements: **$title**`n`nCloses #$IssueNumber."}
  # If a PR already exists, gh will error; we catch and just print a hint
  try {
    & gh pr create `
      --title "$prTitle" `
      --body "$prBody" `
      --base "main" `
      --head "$branchName"
  } catch {
    Write-Warning "gh pr create failed (maybe PR already exists). You can open manually with: gh pr create"
  }
}

$branchName = (git rev-parse --abbrev-ref HEAD).Trim()
[pscustomobject]@{
  Repo        = $Repo
  IssueNumber = $IssueNumber
  Title       = $title
  Branch      = $branchName
}

Write-Host "✅ Issue #$IssueNumber script completed on branch '$branchName'."