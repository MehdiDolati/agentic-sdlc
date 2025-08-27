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

# Call the dispatcher (engine) – do not ask it to open a PR
$dispatchArgs = @{
  Repo        = $Repo
  IssueNumber = $IssueNumber
}
if ($DockerSmoke) { $dispatchArgs.DockerSmoke = $true }

$dispatch = & (Join-Path $PSScriptRoot 'issue-dispatch.ps1') @dispatchArgs
if (-not $dispatch) { Fail "issue-dispatch returned no context." }

$branch = $dispatch.Branch
$title  = $dispatch.Title
Write-Host "Branch from dispatcher: $branch"

# Stage & commit any changes the dispatcher just made
if (git status --porcelain) {
  git add -A | Out-Null
  $msg = ("Resolve #{0}: {1}" -f $IssueNumber, $title)
  Write-Host "Committing changes: $msg"
  git commit -m "$msg" | Out-Null
} else {
  Write-Host "No changes to commit."
}

# Ensure upstream & push safely
$branchName = (git rev-parse --abbrev-ref HEAD).Trim()
# Detect upstream safely (suppress errors)
$hasUpstream = $false
try {
  git rev-parse --symbolic-full-name --abbrev-ref "$branchName@{u}" *> $null
  if ($LASTEXITCODE -eq 0) { $hasUpstream = $true }
} catch { $hasUpstream = $false }

if (-not $hasUpstream) {
  Write-Host "Setting upstream and pushing $branchName…"
  git push -u origin "$branchName" | Out-Null
} else {
  Write-Host "Rebasing on remote and pushing $branchName…"
  git pull --rebase origin "$branchName" | Out-Null
  git push | Out-Null
}


# Create or update PR (always provide title/body)
$existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number' 2>$null
if (-not $existing) {
  $prArgs = @{
    R     = $Repo
    base  = "main"
    head  = $branch
    title = $title
    body  = "Automated PR for issue #$IssueNumber.`r`n`r`nCloses #$IssueNumber"
  }
  $null = gh pr create @prArgs
  $existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number'
}


# Idempotently ensure the body contains “Closes #N”
try {
  Import-Module "$PSScriptRoot/Agentic.Tools.psm1" -Force -ErrorAction Stop
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  Ensure-PrBodyHasClose -Repo $Repo -HeadBranch $branch -IssueNumber $IssueNumber -Title $dispatch.Title -Body $currBody
} catch {
  # Fallback if helper module isn't available
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  if ($currBody -notmatch "(?i)closes\s*#\s*$IssueNumber") {
    $newBody = ($currBody.Trim() + "`r`n`r`nCloses #$IssueNumber").Trim()
    gh pr edit $existing -R $Repo --body $newBody | Out-Null
    Write-Host "Injected 'Closes #$IssueNumber' into PR body (fallback)."
  }
}

# Apply labels if any (loop; gh expects one label per flag)
if ($Labels -and $Labels.Count -gt 0) {
  foreach ($label in $Labels) {
    gh pr edit $existing -R $Repo --add-label "$label" | Out-Null
  }
  Write-Host "Applied labels: $($Labels -join ', ')"
}

if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  # Poll up to ~5 minutes (60 * 5s). Adjust if you want longer.
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

# Auto-merge if requested
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  gh pr merge $existing -R $Repo --squash --delete-branch | Out-Null
}

Write-Host "Done. PR #$existing for issue #$IssueNumber ready."