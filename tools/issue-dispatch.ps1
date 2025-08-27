# tools/issue-dispatch.ps1
# Minimal, self-contained dispatcher. PowerShell 5 compatible.

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string] $Repo,
  [Parameter(Mandatory = $true)][int]    $IssueNumber,
  [switch] $OpenPR,
  [switch] $DockerSmoke
)

function Fail($msg) { Write-Error $msg; exit 1 }

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

# --- Preconditions (no dot-sourcing, no interactivity)
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found in PATH." }
if (-not (Get-Command gh  -ErrorAction SilentlyContinue)) { Fail "GitHub CLI 'gh' not found." }

# If GH_TOKEN is present, verify it quickly
if (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $null = & gh api user --jq .login 2>$null
  if ($LASTEXITCODE -ne 0) {
    Fail "GH_TOKEN present but invalid or missing scopes (need 'repo','workflow')."
  }
} else {
  # Fallback to stored auth; bail if not logged in
  try { & gh auth status 1>$null 2>$null } catch { Fail "Run: gh auth login (or set GH_TOKEN)." }
}

# Ensure we are in a git repo and the tree is clean enough for checkout
try { & git rev-parse --is-inside-work-tree 1>$null 2>$null } catch { Fail "Run from inside a git repository." }

# --- Fetch the issue (title/body)
# Get title
$title = & gh api "repos/$Repo/issues/$IssueNumber" --jq .title 2>$null
if ([string]::IsNullOrWhiteSpace($title)) { Fail "Unable to fetch issue #$IssueNumber from $Repo." }

# Body (optional)
$body  = & gh api "repos/$Repo/issues/$IssueNumber" --jq .body 2>$null
if ($LASTEXITCODE -ne 0) { $body = "" }

# --- Slugify title
function New-Slug([string]$s) {
  $s = $s.ToLower()
  $s = ($s -replace '[^a-z0-9]+','-').Trim('-')
  if ($s.Length -gt 64) { $s = $s.Substring(0,64).Trim('-') }
  return $s
}
$slug = New-Slug $title

# --- Create or checkout branch
$branchName = "issue-$IssueNumber-$slug"

# If branch exists, checkout; else create
$exists = & git rev-parse --verify --quiet "refs/heads/$branchName" 2>$null
if ($LASTEXITCODE -eq 0) {
  & git checkout "$branchName" | Out-Null
} else {
  & git checkout -b "$branchName" | Out-Null
}

# --- Return minimal context (auto-issue.ps1 will JSON-ify this)
[pscustomobject]@{
  Repo        = $Repo
  IssueNumber = $IssueNumber
  Title       = $title
  Body        = $body
  Branch      = $branchName
}
