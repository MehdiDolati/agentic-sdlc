# tools/auto-issue.ps1
# Windows PowerShell 5+ compatible (no PS7-only operators)
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

function Fail($msg){ Write-Error $msg; exit 1 }

# -------------------- Non-interactive environment knobs -----------------------
$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'
$env:GIT_ASKPASS            = "echo"
$env:GIT_TERMINAL_PROMPT    = "0"
$env:GIT_EDITOR             = "true"
$env:GH_PROMPT_DISABLED     = "1"
$env:GH_NO_UPDATE_NOTIFIER  = "1"

# -------------------- Helpers --------------------------------------------------
function Ensure-Tool([string]$name, [string]$installUrl='') {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    if ($installUrl) {
      Fail "Required tool '$name' not found. Install: $installUrl"
    } else {
      Fail "Required tool '$name' not found."
    }
  }
}

function Ensure-GhAuth {
  Ensure-Tool 'gh' 'https://cli.github.com'
  try { gh auth status 1>$null 2>$null } catch { Fail "Run: gh auth login" }
}

function Ensure-GitClean {
  $status = git status --porcelain
  if (-not [string]::IsNullOrWhiteSpace($status)) {
    Fail "Working tree is dirty. Commit or stash before running auto-issue."
  }
}

# PS5-safe timeout wrapper using jobs
function Invoke-WithTimeout {
  param(
    [Parameter(Mandatory=$true)][scriptblock]$ScriptBlock,
    [int]$TimeoutSeconds = 240,
    [string]$Description = "operation",
    $ArgumentList
  )
  $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
  try {
    $ok = Wait-Job -Job $job -Timeout $TimeoutSeconds
    if (-not $ok) {
      Stop-Job $job -ErrorAction SilentlyContinue
      Remove-Job $job -ErrorAction SilentlyContinue
      throw "Timed out after $TimeoutSeconds s during $Description."
    }
    $out = Receive-Job -Job $job -ErrorAction Stop
    return $out
  } finally {
    Remove-Job $job -ErrorAction SilentlyContinue
  }
}

# -------------------- Preconditions -------------------------------------------
Ensure-Tool 'git' 'https://git-scm.com/downloads'
Ensure-GhAuth
Ensure-GitClean

# -------------------- Call the dispatcher (engine) ----------------------------
$dispatchArgs = @{
  Repo        = $Repo
  IssueNumber = $IssueNumber
}
if ($OpenPR)      { $dispatchArgs.OpenPR      = $true }
if ($DockerSmoke) { $dispatchArgs.DockerSmoke = $true }

$dispatch = Invoke-WithTimeout -TimeoutSeconds 240 -Description "issue-dispatch" -ScriptBlock {
  param($root, $args)
  & (Join-Path $root 'issue-dispatch.ps1') @args
} -ArgumentList @($PSScriptRoot, $dispatchArgs)

if (-not $dispatch) { Fail "issue-dispatch returned no context." }

$branch = $dispatch.Branch
$title  = [string]$dispatch.Title
if ([string]::IsNullOrWhiteSpace($branch)) { $branch = (git rev-parse --abbrev-ref HEAD).Trim() }

Write-Host "Branch from dispatcher: $branch"

# -------------------- Stage & commit any changes the dispatcher made ----------
git add -A | Out-Null
$hasStaged = git diff --cached --name-only
if (-not [string]::IsNullOrWhiteSpace($hasStaged)) {
  $msg = "Resolve #$($IssueNumber): $title"
  Write-Host "Committing changes: $msg"
  git commit -m "$msg" | Out-Null
} else {
  Write-Host "No changes to commit."
}

# -------------------- Ensure upstream & push safely ---------------------------
$currBranch  = (git rev-parse --abbrev-ref HEAD).Trim()
$hasUpstream = git rev-parse --symbolic-full-name --abbrev-ref "$currBranch@{u}" 2>$null

if (-not $hasUpstream) {
  Write-Host "Setting upstream and pushing $currBranch…"
  git push -u origin $currBranch | Out-Null
} else {
  Write-Host "Rebasing on remote and pushing $currBranch…"
  git pull --rebase origin $currBranch | Out-Null
  git push | Out-Null
}

# -------------------- Create or update PR (always provide title/body) ---------
$existing = gh pr list -R $Repo --head $currBranch --json number --jq '.[0].number' 2>$null

if (-not $existing) {
  $prTitle = $title
  $prBody  = "Automated PR for issue #$($IssueNumber).`r`n`r`nCloses #$($IssueNumber)."

  Write-Host "Creating PR for $currBranch → main…"
  # Use a timeout to avoid hangs
  $null = Invoke-WithTimeout -TimeoutSeconds 180 -Description "gh pr create" -ScriptBlock {
    param($repo,$base,$head,$pt,$pb)
    gh pr create -R $repo --base $base --head $head --title $pt --body $pb
  } -ArgumentList @($Repo,'main',$currBranch,$prTitle,$prBody)

  # Re-fetch number
  $existing = gh pr list -R $Repo --head $currBranch --json number --jq '.[0].number'
} else {
  Write-Host "PR #$existing already exists for $currBranch."
}

# -------------------- Ensure "Closes #N" present ------------------------------
try {
  $currBody = gh pr view $existing -R $Repo --json body --jq .body
  if ($currBody -notmatch "(?i)closes\s*#\s*$IssueNumber") {
    $newBody = ($currBody.Trim() + "`r`n`r`nCloses #$IssueNumber").Trim()
    gh pr edit $existing -R $Repo --body $newBody | Out-Null
    Write-Host "Injected 'Closes #$IssueNumber' into PR body."
  }
} catch {
  Write-Warning "Could not read/update PR body: $_"
}

# -------------------- Apply labels (one flag per label) -----------------------
if ($Labels -and $Labels.Count -gt 0) {
  foreach ($label in $Labels) {
    gh pr edit $existing -R $Repo --add-label "$label" | Out-Null
  }
  Write-Host "Applied labels: $($Labels -join ', ')"
}

# -------------------- Wait for checks (simple textual poll) -------------------
if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  for ($i=0; $i -lt 60; $i++) {  # ~5 minutes
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

# -------------------- Auto-merge if requested ---------------------------------
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  gh pr merge $existing -R $Repo --squash --delete-branch | Out-Null
}

Write-Host "Done. PR #$existing for issue #$IssueNumber ready."