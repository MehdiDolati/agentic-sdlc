# tools/auto-issue.ps1
# Windows PowerShell 5+ compatible (no Start-Job/Wait-Job; hard timeouts via Start-Process)

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true )][string] $Repo,
  [Parameter(Mandatory = $true )][int]    $IssueNumber,
  [Parameter(Mandatory = $false)][string[]] $Labels,
  [switch] $OpenPR,
  [switch] $DockerSmoke,
  [switch] $AutoMerge,
  [switch] $WaitForChecks
)

function Fail($msg) { Write-Error $msg; exit 1 }

# --- Non-interactive env hardening -------------------------------------------
$ErrorActionPreference          = 'Stop'
$ProgressPreference             = 'SilentlyContinue'
$env:GIT_ASKPASS                = "echo"                 # prevent auth prompts
$env:GIT_TERMINAL_PROMPT        = "0"
$env:GIT_EDITOR                 = "true"
$env:GH_PROMPT_DISABLED         = "1"
$env:GH_NO_UPDATE_NOTIFIER      = "1"

# --- Utilities ---------------------------------------------------------------
function Get-PwshExe {
  if ($PSHOME -and (Test-Path (Join-Path $PSHOME 'powershell.exe'))) {
    return (Join-Path $PSHOME 'powershell.exe') # Windows PowerShell host
  }
  return 'powershell.exe'
}

function Invoke-ExternalWithTimeout {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(Mandatory=$true)][string]$ArgumentList,
    [int]$TimeoutSeconds = 10,
    [string]$WorkingDirectory = (Get-Location).Path
  )
  $outFile = [System.IO.Path]::GetTempFileName()
  $errFile = [System.IO.Path]::GetTempFileName()
  try {
    $p = Start-Process -FilePath $FilePath `
                       -ArgumentList $ArgumentList `
                       -WorkingDirectory $WorkingDirectory `
                       -NoNewWindow -PassThru `
                       -RedirectStandardOutput $outFile `
                       -RedirectStandardError  $errFile

    $null = $p.WaitForExit($TimeoutSeconds * 1000)
    if (-not $p.HasExited) {
      try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
      throw "Timed out after ${TimeoutSeconds}s: $FilePath $ArgumentList"
    }

    $stdout = Get-Content -LiteralPath $outFile -Raw -ErrorAction SilentlyContinue
    $stderr = Get-Content -LiteralPath $errFile -Raw -ErrorAction SilentlyContinue
    [pscustomobject]@{
      ExitCode = $p.ExitCode
      StdOut   = $stdout
      StdErr   = $stderr
    }
  }
  finally {
    Remove-Item -LiteralPath $outFile,$errFile -ErrorAction SilentlyContinue
  }
}

function Ensure-Tool([string]$name, [string]$hintUrl) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) { Fail "$name not found. Install: $hintUrl" }
}

# --- Preconditions -----------------------------------------------------------
Ensure-Tool 'git' 'https://git-scm.com/downloads'
Ensure-Tool 'gh'  'https://cli.github.com'

# Accept GITHUB_TOKEN (CI) by shimming into GH_TOKEN for gh CLI
if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN) -and -not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
  $env:GH_TOKEN = $env:GITHUB_TOKEN
}

# Non-interactive authentication: prefer token, probe once with gh api
if (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
  $null = & gh api user --jq .login 2>$null
  if ($LASTEXITCODE -ne 0) {
    Fail "GH_TOKEN is set but invalid or missing scopes. Ensure it has 'repo' and 'workflow'."
  }
} else {
  try {
    & gh auth status 1>$null 2>$null
  } catch {
    Fail "GitHub CLI not authenticated. Run once: gh auth login --web --scopes 'repo,workflow' or set GH_TOKEN."
  }
}

# Ensure working tree is clean (clear, actionable failure rather than stall)
$dirty = git status --porcelain
if ($dirty) { Fail "Working tree is dirty. Commit or stash before running auto-issue." }

# --- Call dispatcher inline (no child process / no timeout) ------------------
try {
  $dispatchArgs = @{
    Repo        = $Repo
    IssueNumber = $IssueNumber
  }
  if ($OpenPR)      { $dispatchArgs.OpenPR      = $true }
  if ($DockerSmoke) { $dispatchArgs.DockerSmoke = $true }

  $dispatch = & (Join-Path $PSScriptRoot 'issue-dispatch.ps1') @dispatchArgs
  if (-not $dispatch) { Fail "issue-dispatch returned no context." }
}
catch {
  Fail ("issue-dispatch failed: {0}" -f $_.Exception.Message)
}

if (-not $dispatch) { Fail "issue-dispatch returned no context." }
$branch = [string]$dispatch.Branch
$title  = [string]$dispatch.Title

Write-Host "Branch from dispatcher: $branch"

# --- Stage & commit anything produced by dispatcher --------------------------
# (idempotent — commits only if something changed)
$diffIndex = & git status --porcelain
if (-not [string]::IsNullOrWhiteSpace($diffIndex)) {
  & git add -A | Out-Null
  $commitMsg = ("Resolve #{0}: {1}" -f $IssueNumber, $title)
  Write-Host "Committing changes: $commitMsg"
  & git commit -m "$commitMsg" | Out-Null
} else {
  Write-Host "No changes to commit."
}

# --- Ensure upstream, rebase/push safely -------------------------------------
# Determine branch from current HEAD if needed
if ([string]::IsNullOrWhiteSpace($branch)) {
  $branch = (& git rev-parse --abbrev-ref HEAD).Trim()
}

# Does branch have an upstream?
$hasUpstream = $null
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

$null = & git rev-parse --abbrev-ref --symbolic-full-name "$branch@{u}" 2>$null
$probeExit = $LASTEXITCODE
if ($probeExit -eq 0) {
  $hasUpstream = (& git rev-parse --abbrev-ref --symbolic-full-name "$branch@{u}" 2>$null).Trim()
}

$ErrorActionPreference = $prevEap

if ($probeExit -ne 0 -or [string]::IsNullOrWhiteSpace($hasUpstream)) {
  Write-Host "Setting upstream and pushing $branch…"
  & git push -u origin $branch | Out-Null
} else {
  Write-Host "Rebasing on remote and pushing $branch…"
  & git pull --rebase origin $branch | Out-Null
  & git push | Out-Null
}

# Ensure we only try to open a PR if this branch has commits ahead of main
$base = 'main'
& git fetch origin $base | Out-Null

# Count ahead/behind relative to origin/main
$counts = & git rev-list --left-right --count "origin/$base...$branch" 2>$null
# Expected format: "<behind> <ahead>"
$behind = 0; $ahead = 0
if ($counts -match '^\s*(\d+)\s+(\d+)\s*$') {
  $behind = [int]$Matches[1]
  $ahead  = [int]$Matches[2]
}

if ($ahead -le 0) {
  Write-Host "Branch '$branch' has no commits ahead of '$base'. Skipping PR creation."
  Write-Host "Done. Nothing to PR for issue #$IssueNumber right now."
  return
}


# --- Create or update PR (non-interactive, with timeout) ---------------------
# Check if a PR already exists for this branch
$existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number' 2>$null

if (-not $existing) {
  $prTitle = $title
  $prBody  = "Automated PR for issue #$IssueNumber.`r`n`r`nCloses #$IssueNumber"

  $ghCreate = @(
    'pr','create',
    '-R', $Repo,
    '--base','main',
    '--head', $branch,
    '--title', ('"{0}"' -f $prTitle),
    '--body',  ('"{0}"' -f $prBody)
  ) -join ' '

  $res = Invoke-ExternalWithTimeout -FilePath 'gh' -ArgumentList $ghCreate -TimeoutSeconds 180 -WorkingDirectory (Get-Location).Path
  if ($res.ExitCode -ne 0) {
  $exitDisplay = ($res.ExitCode -as [int]); if ($null -eq $exitDisplay) { $exitDisplay = -1 }
  $msg = @"
	gh pr create failed (exit $exitDisplay).
	STDERR:
	$($res.StdErr)
	STDOUT:
	$($res.StdOut)
"@
  Fail $msg
}

  # Resolve PR number post-create
  $existing = gh pr list -R $Repo --head $branch --json number --jq '.[0].number'
}

# --- Ensure PR body contains “Closes #N” (idempotent) ------------------------
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

# --- Apply labels (one-by-one; gh expects a single value per flag) -----------
if ($Labels -and $Labels.Count -gt 0) {
  foreach ($label in $Labels) {
    gh pr edit $existing -R $Repo --add-label "$label" | Out-Null
  }
  Write-Host "Applied labels: $($Labels -join ', ')"
}

# --- Optionally wait for checks to complete ----------------------------------
if ($WaitForChecks) {
  Write-Host "Waiting for checks to complete…"
  # Poll up to 5 minutes (60 * 5s). Adjust as needed.
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

# --- Auto-merge if requested --------------------------------------------------
if ($AutoMerge) {
  Write-Host "Merging PR #$existing…"
  $mergeArgs = @('pr','merge', $existing, '-R', $Repo, '--squash','--delete-branch') -join ' '
  $m = Invoke-ExternalWithTimeout -FilePath 'gh' -ArgumentList $mergeArgs -TimeoutSeconds 180 -WorkingDirectory (Get-Location).Path
  if ($m.ExitCode -ne 0) {
    Fail ("gh pr merge failed (exit {0}). stderr:`n{1}" -f $m.ExitCode, $m.StdErr)
  }
}

Write-Host ("Done. PR #{0} for issue #{1} ready." -f $existing, $IssueNumber)
