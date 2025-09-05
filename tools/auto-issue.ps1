# tools/auto-issue.ps1
# Purpose: Create/checkout an issue branch only. No PR here.

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Repo,
  [Parameter(Mandatory=$true)][int]    $IssueNumber
)

function Fail($msg){ Write-Error $msg; exit 1 }

# Non-interactive hardening
$ErrorActionPreference     = 'Stop'
$ProgressPreference        = 'SilentlyContinue'
$env:GIT_ASKPASS           = "echo"
$env:GIT_TERMINAL_PROMPT   = "0"
$env:GIT_EDITOR            = "true"
$env:GH_PROMPT_DISABLED    = "1"
$env:GH_NO_UPDATE_NOTIFIER = "1"

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

# --- NEW: Sync main before branching -----------------------------------------
try {
  Write-Host "[auto-issue] Fetching from origin..."
  & git fetch --prune origin | Out-Null

  # Make sure local 'main' exists and tracks origin/main
  $hasLocalMain = (& git show-ref --verify --quiet refs/heads/main); $hasLocalMain = ($LASTEXITCODE -eq 0)
  if (-not $hasLocalMain) {
    Write-Host "[auto-issue] Creating local 'main' to track 'origin/main'..."
    & git checkout -b main origin/main | Out-Null
  }

  Write-Host "[auto-issue] Switching to 'main'..."
  & git switch main | Out-Null

  Write-Host "[auto-issue] Fast-forwarding 'main' from origin/main..."
  & git pull --ff-only origin main | Out-Null

  # Optional: verify we are on main and up-to-date
  $cur = (& git rev-parse --abbrev-ref HEAD).Trim()
  if ($cur -ne 'main') { Fail "Failed to switch to 'main' (current: $cur)" }
} catch {
  Fail ("Failed to sync 'main': {0}" -f $_.Exception.Message)
}
# -----------------------------------------------------------------------------

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
Write-Host "Branch ready: $branchName"