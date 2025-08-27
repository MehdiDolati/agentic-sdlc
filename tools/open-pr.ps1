# tools/open-pr.ps1
# Purpose: Open a PR for the current issue branch ONLY if it is ahead of main.

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber,
  [string[]]                           $Labels,
  [switch]                             $WaitForChecks,
  [switch]                             $AutoMerge
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

# Ensure we’re on a branch
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch) -or $branch -eq 'HEAD') {
  Fail "Not on a branch. Checkout your issue branch first."
}

# Ensure remote main is known
& git fetch origin main --quiet

# Ensure upstream exists (push if needed)
$hasUpstream = (& git rev-parse --abbrev-ref --symbolic-full-name "$branch@{u}" 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($hasUpstream)) {
  Write-Host "Setting upstream and pushing $branch…"
  & git push -u origin $branch | Out-Null
}

# Only open PR if branch is ahead of main (has commits to review)
$ahead = [int](& git rev-list --count "origin/main..$branch")
if ($ahead -le 0) {
  Write-Host "Branch '$branch' has no commits ahead of main. Skipping PR creation."
  exit 0
}

# Build PR
$title = & gh api "repos/$Repo/issues/$IssueNumber" --jq .title 2>$null
if ([string]::IsNullOrWhiteSpace($title)) { $title = "Work for issue #$IssueNumber" }
$body  = "Automated PR for issue #$IssueNumber.`r`n`r`nCloses #$IssueNumber"

# If a PR already exists, don’t recreate
$existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number' 2>$null
if (-not $existing) {
  gh pr create `
    -R $Repo `
    --base main `
    --head $branch `
    --title $title `
    --body  $body | Out-Null

  $existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number'
  Write-Host "Opened PR #$existing for '$branch'."
} else {
  Write-Host "PR #$existing already exists for '$branch'."
}

# Ensure “Closes #N” in body
try {
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  if ($currBody -notmatch "(?i)closes\s*#\s*$IssueNumber") {
    $newBody = ($currBody.Trim() + "`r`n`r`nCloses #$IssueNumber").Trim()
    gh pr edit $existing -R $Repo --body $newBody | Out-Null
    Write-Host "Injected 'Closes #$IssueNumber' into PR body."
  }
} catch {
  Write-Warning "Could not verify/update PR body: $($_.Exception.Message)"
}

# Apply labels if provided
if ($Labels -and $Labels.Count -gt 0) {
  foreach ($label in $Labels) {
    gh pr edit $existing -R $Repo --add-label "$label" | Out-Null
  }
  Write-Host "Applied labels: $($Labels -join ', ')"
}

# Optionally wait for checks
if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  for ($i = 0; $i -lt 60; $i++) {
    $summary = gh pr checks $existing -R $Repo 2>$null
    if ($LASTEXITCODE -eq 0 -and $summary) {
      if ($summary -match "All checks were successful") {
        Write-Host "Checks are green."
        break
      }
      if ($summary -match "(?i)failing|failed") {
        Fail "Checks failing for PR #$existing"
      }
    }
    Start-Sleep -Seconds 5
  }
}

# Optionally auto-merge
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  gh pr merge $existing -R $Repo --squash --delete-branch | Out-Null
  Write-Host "Merged PR #$existing and deleted the remote branch."
}
