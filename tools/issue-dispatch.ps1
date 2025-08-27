# tools/auto-issue.ps1
# Windows PowerShell 5+ compatible; portable & non-interactive.

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber,
  [string[]]                           $Labels,
  [switch]                             $OpenPR,
  [switch]                             $DockerSmoke,
  [switch]                             $AutoMerge,     # auto-merge when checks are green
  [switch]                             $WaitForChecks  # wait for checks before returning
)

# --- Portable helpers
. (Join-Path $PSScriptRoot 'lib/Agentic.Portable.ps1')

function Fail($msg){ Write-Error $msg; exit 1 }
$ErrorActionPreference = 'Stop'

# --- Preconditions
Ensure-Git
Ensure-GhAuth
Ensure-GitClean

# --- Call dispatcher (engine) to prep branch / make changes / run tests
$dispatchArgs = @{
  Repo        = $Repo
  IssueNumber = $IssueNumber
}
if ($OpenPR)      { $dispatchArgs.OpenPR      = $true }
if ($DockerSmoke) { $dispatchArgs.DockerSmoke = $true }

$dispatch = & (Join-Path $PSScriptRoot 'issue-dispatch.ps1') @dispatchArgs
if ($LASTEXITCODE -ne 0) { Fail "issue-dispatch failed with exit code $LASTEXITCODE" }
if (-not $dispatch)      { Fail "issue-dispatch returned no context." }

$branch = $dispatch.Branch
$title  = $dispatch.Title
Write-Host "Branch from dispatcher: $branch"

# --- Stage & commit anything left by the dispatcher/idempotent scripts
git add -A | Out-Null
$pending = git diff --cached --name-only
if (-not [string]::IsNullOrWhiteSpace($pending)) {
  $commitMsg = "Resolve #$($IssueNumber): ${title}"
  Write-Host "Committing changes: $commitMsg"
  git commit -m "$commitMsg" | Out-Null
} else {
  Write-Host "No changes to commit."
}

# --- Ensure upstream & push safely
Ensure-UpstreamAndPush $branch

# --- Create or update PR (always provide title/body to avoid prompts)
$existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number' 2>$null
if (-not $existing) {
  $prTitle = "Resolve #$($IssueNumber): ${title}"
  $prBody  = "Automated PR for **${title}**.`r`n`r`nCloses #$IssueNumber"
  gh pr create `
    -R $Repo `
    --base main `
    --head $branch `
    --title "$prTitle" `
    --body  "$prBody"  | Out-Null

  # Re-fetch PR number
  $existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number'
}

# --- Ensure body has 'Closes #N' (idempotent)
try {
  Import-Module (Join-Path $PSScriptRoot 'Agentic.Tools.psm1') -Force -ErrorAction Stop
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  Ensure-PrBodyHasClose -Repo $Repo -HeadBranch $branch -IssueNumber $IssueNumber -Title $title -Body $currBody
} catch {
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  if ($currBody -notmatch "(?i)closes\s*#\s*$IssueNumber") {
    $newBody = ($currBody.Trim() + "`r`n`r`nCloses #$IssueNumber").Trim()
    gh pr edit $existing -R $Repo --body $newBody | Out-Null
    Write-Host "Injected 'Closes #$IssueNumber' into PR body (fallback)."
  }
}

# --- Apply labels (one flag per label)
if ($Labels -and $Labels.Count -gt 0) {
  foreach ($label in $Labels) {
    gh pr edit $existing -R $Repo --add-label "$label" | Out-Null
  }
  Write-Host "Applied labels: $($Labels -join ', ')"
}

# --- Wait for checks (parse human text; gh’s JSON fields differ across versions)
if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  for ($i = 0; $i -lt 60; $i++) {  # ~5 minutes @ 5s
    $summary = gh pr checks $existing -R $Repo 2>$null
    if ($LASTEXITCODE -eq 0 -and $summary) {
      if ($summary -match "All checks were successful") { Write-Host "Checks are green."; break }
      if ($summary -match "(?i)failing|failed")         { Fail "Checks failing for PR #$existing" }
    }
    Start-Sleep -Seconds 5
  }
}

# --- Auto-merge
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  gh pr merge $existing -R $Repo --squash --delete-branch | Out-Null
}

Write-Host "Done. PR #$existing for issue #$IssueNumber ready."