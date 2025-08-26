# tools/auto-issue.ps1
# Windows PowerShell 5+ compatible
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber,
  [string[]]                           $Labels,
  [switch]                             $OpenPR,
  [switch]                             $DockerSmoke,
  [switch]                             $AutoMerge,        # auto-merge when checks are green
  [switch]                             $WaitForChecks     # wait for checks before returning
)

function Fail($msg){ Write-Error $msg; exit 1 }

$ErrorActionPreference = 'Stop'

# Preconditions
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Fail "GitHub CLI 'gh' not found. Install https://cli.github.com and run 'gh auth login'."
}
& gh auth status 1>$null 2>$null

# Ensure working tree is clean
$dirty = git status --porcelain
if ($dirty) { Fail "Working tree is dirty. Commit or stash before running auto-issue." }

# Call the dispatcher (engine)
$dispatchArgs = @{
  Repo        = $Repo
  IssueNumber = $IssueNumber
}
if ($OpenPR)      { $dispatchArgs.OpenPR = $true }
if ($DockerSmoke) { $dispatchArgs.DockerSmoke = $true }

$dispatch = & (Join-Path $PSScriptRoot 'issue-dispatch.ps1') @dispatchArgs

if (-not $dispatch) { Fail "issue-dispatch returned no context." }

$branch = $dispatch.Branch
$title  = $dispatch.Title

Write-Host "Branch from dispatcher: $branch"
# Create or update PR
$existing = gh pr list -R $Repo --head $branch --json number -q '.[0].number' 2>$null
if (-not $existing) {
  # Create with a safe title/body to avoid flags being interpreted
  $prNum = gh pr create -R $Repo --head $branch --base main `
    --title "$title" `
    --body "Automated PR for issue #$IssueNumber.`n`nCloses #$IssueNumber" `
    --fill 2>$null | ForEach-Object { $_ } # capture output or URL
  # Resolve PR number reliably
  $existing = gh pr list -R $Repo --head $branch --json number -q '.[0].number'
}

# Ensure body has Closes #N (idempotent)
$body = gh pr view $existing -R $Repo --json body -q .body
if ($body -notmatch "(?i)closes\s*#\s*$IssueNumber") {
  $newBody = ($body.Trim() + "`r`n`r`nCloses #$IssueNumber").Trim()
  gh pr edit $existing -R $Repo --body $newBody | Out-Null
  Write-Host "Injected 'Closes #$IssueNumber' into PR body."
}

# Apply labels if any
if ($Labels -and $Labels.Count -gt 0) {
  # Quote each label to handle spaces
  $quoted = $Labels | ForEach-Object { '"{0}"' -f $_ }
  gh pr edit $existing -R $Repo --add-label $quoted | Out-Null
  Write-Host "Applied labels: $($Labels -join ', ')"
}

# Wait for checks if requested
if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  # Poll a few times; stop on success/failure
  for ($i=0; $i -lt 60; $i++) {
    $sum = gh pr checks $existing -R $Repo --json status,state -q '[.status,.state] | @tsv' 2>$null
    if ($LASTEXITCODE -eq 0 -and $sum) {
      # status/state semantics vary; if gh supports a success state, we can break.
      $summary = gh pr checks $existing -R $Repo
      if ($summary -match "All checks were successful") { break }
      if ($summary -match "failing") { Fail "Checks failing for PR #$existing" }
    }
    Start-Sleep -Seconds 5
  }
}

# Auto-merge if requested
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  gh pr merge $existing -R $Repo --squash --delete-branch | Out-Null
}

Write-Host "Done. PR #$existing for issue #$IssueNumber ready."