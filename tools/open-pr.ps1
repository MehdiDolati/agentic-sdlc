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

# Ensure we’re on a branch
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch) -or $branch -eq 'HEAD') {
  Fail "Not on a branch. Checkout your issue branch first."
}

# Ensure remote main is known
& git fetch origin main --quiet

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


# Does branch have an upstream?
$hasUpstream = (& git rev-parse --symbolic-full-name --abbrev-ref "$branch@{u}" 2>$null)
if (-not $hasUpstream) {
  Write-Host "Setting upstream and pushing $branch…"
  & git push -u origin $branch | Out-Null
} else {
  Write-Host "Rebasing on remote and pushing $branch…"
  & git pull --rebase origin $branch | Out-Null
  & git push | Out-Null
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
    Fail ("gh pr create failed (exit {0}). stderr:`n{1}" -f $res.ExitCode, $res.StdErr)
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