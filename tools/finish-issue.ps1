# tools/finish-issue.ps1
# Purpose: Merge the PR for the current issue branch (squash), delete remote & local branch.
# Usage: tools/finish-issue.ps1 -Repo owner/repo [-IssueNumber N] [-WaitForChecks]

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [int]                                $IssueNumber,
  [switch]                             $WaitForChecks
)

function Fail($msg){ Write-Error $msg; exit 1 }

$ErrorActionPreference     = 'Stop'
$ProgressPreference        = 'SilentlyContinue'
$env:GIT_ASKPASS           = "echo"
$env:GIT_TERMINAL_PROMPT   = "0"
$env:GIT_EDITOR            = "true"
$env:GH_PROMPT_DISABLED    = "1"
$env:GH_NO_UPDATE_NOTIFIER = "1"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found in PATH." }
if (-not (Get-Command gh  -ErrorAction SilentlyContinue)) { Fail "GitHub CLI 'gh' not found." }

if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN) -and [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $env:GH_TOKEN = $env:GITHUB_TOKEN
}
if (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $null = & gh api user --jq .login 2>$null
  if ($LASTEXITCODE -ne 0) { Fail "GH_TOKEN provided but invalid/insufficient scope. Need 'repo' & 'workflow'." }
} else {
  & gh auth status 1>$null 2>$null
}

# Determine branch
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch) -or $branch -eq 'HEAD') {
  Fail "Not on a branch. Checkout your issue branch first."
}

# Find PR by branch (preferred) or by issue number
$prNum = gh pr list -R $Repo --head $branch --json number --jq '.[0].number' 2>$null
if (-not $prNum -and $IssueNumber) {
  $prNum = gh pr list -R $Repo --search "involves:@me is:open linked:issue/$IssueNumber" --json number --jq '.[0].number' 2>$null
}
if (-not $prNum) { Fail "No open PR found for branch '$branch' (and no PR found by issue #$IssueNumber)." }

# Optionally wait for checks
if ($WaitForChecks) {
  Write-Host "Waiting for checks on PR #$prNum…"
  for ($i = 0; $i -lt 60; $i++) {
    $summary = gh pr checks $prNum -R $Repo 2>$null
    if ($LASTEXITCODE -eq 0 -and $summary) {
      if ($summary -match "All checks were successful") {
        Write-Host "Checks are green."
        break
      }
      if ($summary -match "(?i)failing|failed") {
        Fail "Checks failing for PR #$prNum"
      }
    }
    Start-Sleep -Seconds 5
  }
}

# Merge & delete remote branch
Write-Host "Merging PR #$prNum…"
gh pr merge $prNum -R $Repo --squash --delete-branch | Out-Null
Write-Host "PR #$prNum merged. Remote branch deleted."

# Delete local branch (switch to main first)
try {
  & git checkout main | Out-Null
} catch {}
try {
  & git branch -D $branch | Out-Null
  Write-Host "Local branch '$branch' deleted."
} catch {
  Write-Warning "Could not delete local branch '$branch': $($_.Exception.Message)"
}
