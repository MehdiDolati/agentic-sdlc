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

# --- timeout helper (PS5-compatible) -----------------------------------------
function Invoke-WithTimeout {
  param(
    [Parameter(Mandatory=$true)][scriptblock]$ScriptBlock,
    [int]$Seconds = 180,
    [string]$Description = "operation",
    $ArgumentList
  )
  $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
  try {
    $done = Wait-Job -Job $job -Timeout $Seconds
    if (-not $done) {
      Stop-Job $job -ErrorAction SilentlyContinue
      Remove-Job $job -ErrorAction SilentlyContinue
      throw "Timed out after ${Seconds}s while waiting for $Description."
    }
    $out = Receive-Job -Job $job -ErrorAction Stop
    return $out
  } finally {
    Remove-Job $job -ErrorAction SilentlyContinue
  }
}

function Fail($msg){ Write-Error $msg; exit 1 }

$ErrorActionPreference = 'Stop'

# Prevent interactive prompts from git/gh/editors
$env:GIT_ASKPASS = "echo"
$env:GIT_TERMINAL_PROMPT = "0"
$env:GIT_EDITOR = "true"
$env:GH_PROMPT_DISABLED = "1"
$env:GH_NO_UPDATE_NOTIFIER = "1"
$ProgressPreference = 'SilentlyContinue'

# --- timeout helper (PS5-compatible) -----------------------------------------
function Invoke-WithTimeout {
  param(
    [Parameter(Mandatory=$true)][scriptblock]$ScriptBlock,
    [int]$Seconds = 180,
    [string]$Description = "operation",
    $ArgumentList
  )
  $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
  try {
    $done = Wait-Job -Job $job -Timeout $Seconds
    if (-not $done) {
      Stop-Job $job -ErrorAction SilentlyContinue
      Remove-Job $job -ErrorAction SilentlyContinue
      throw "Timed out after ${Seconds}s while waiting for $Description."
    }
    $out = Receive-Job -Job $job -ErrorAction Stop
    return $out
  } finally {
    Remove-Job $job -ErrorAction SilentlyContinue
  }
}

# Tiny tracer
function Trace($msg) { Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" }

# Run a scriptblock with a timeout (so we fail fast instead of 'freezing')
function Invoke-WithTimeout {
  param(
    [Parameter(Mandatory=$true)][scriptblock]$ScriptBlock,
    [int]$TimeoutSec = 60,
    [string]$Description = "operation"
  )
  $job = Start-Job -ScriptBlock $ScriptBlock
  if (-not (Wait-Job $job -Timeout $TimeoutSec)) {
    Stop-Job $job -Force | Out-Null
    Remove-Job $job -Force | Out-Null
    throw "Timed out after ${TimeoutSec}s while $Description"
  }
  $result = Receive-Job $job
  Remove-Job $job -Force | Out-Null
  return $result
}

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

$dispatch = Invoke-WithTimeout -Seconds 10 -Description "issue-dispatch" -ScriptBlock {
  param($root, $args)
  & (Join-Path $root 'issue-dispatch.ps1') @args
} -ArgumentList @($PSScriptRoot, $dispatchArgs)

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
  
  $null = Invoke-WithTimeout -Seconds 120 -Description "gh pr create" -ScriptBlock {
	  param($args)
	  gh pr create @args
  } -ArgumentList @($prArgs)

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