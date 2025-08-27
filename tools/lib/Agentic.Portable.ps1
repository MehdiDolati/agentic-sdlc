# tools/lib/Agentic.Portable.ps1
# PowerShell 5+ compatible helpers for portable, non-interactive scripts.

$ErrorActionPreference = 'Stop'

function Fail([string]$msg) { Write-Error $msg; exit 1 }

function Resolve-RepoRoot {
  # Anchor scripts to the repo root (assumes this file lives under tools/lib/)
  if (-not $script:RepoRoot) {
    $here = Split-Path -Parent $PSCommandPath       # tools/lib
    $tools = Split-Path -Parent $here                # tools
    $root  = Split-Path -Parent $tools               # repo root
    if (-not (Test-Path (Join-Path $root ".git"))) {
      # Fallback: current directory
      $root = (Get-Location).Path
    }
    $script:RepoRoot = $root
  }
  $script:RepoRoot
}

function Ensure-Tool([string]$name, [string]$installUrl='') {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    if ($installUrl) {
      Fail "Required tool '$name' not found. Install: $installUrl"
    } else {
      Fail "Required tool '$name' not found in PATH."
    }
  }
}

function Ensure-GhAuth {
  Ensure-Tool 'gh' 'https://cli.github.com'
  try {
    # Non-interactive, short+sweet check: get the current user login
    $login = & gh api user --jq .login 2>$null
    if ([string]::IsNullOrWhiteSpace($login)) {
      throw "not authenticated"
    }
  }
  catch {
    Fail "GitHub CLI is not authenticated for non-interactive use. Run once: `gh auth login --web --scopes 'repo,workflow'` or set a token via `$env:GH_TOKEN`."
  }
}

function Ensure-Git {
  Ensure-Tool 'git' 'https://git-scm.com/downloads'
  try { git rev-parse --is-inside-work-tree 1>$null 2>$null } catch { Fail "Run from inside a git repo." }
}

function Test-GitClean {
  $status = git status --porcelain
  return [string]::IsNullOrWhiteSpace($status)
}

function Ensure-GitClean {
  if (-not (Test-GitClean)) { Fail "Working tree is dirty. Commit or stash before continuing." }
}

function Get-PythonPath {
  # Prefer venv python
  $root = Resolve-RepoRoot
  $venvWin = Join-Path $root ".venv\Scripts\python.exe"
  $venvPos = Join-Path $root ".venv/bin/python"
  if (Test-Path $venvWin) { return $venvWin }
  if (Test-Path $venvPos) { return $venvPos }

  # Then launcher on Windows
  $isWindows = $IsWindows -or ($env:OS -like "*Windows*")
  if ($isWindows) {
    $py311 = Get-Command 'py' -ErrorAction SilentlyContinue
    if ($py311) {
      try {
        $v = & py -3.11 -V 2>$null
        if ($LASTEXITCODE -eq 0) { return 'py -3.11' }
      } catch {}
    }
  }

  # Then python3, then python
  foreach ($cand in @('python3','python')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) { return $cand }
  }

  Fail "No Python found. Install Python 3.11+."
}

function Ensure-Venv {
  $root = Resolve-RepoRoot
  $venvDir = Join-Path $root '.venv'
  if (Test-Path $venvDir) { return }

  Write-Host "[venv] creating"
  $py = Get-PythonPath
  # Use launcher if available to target 3.11; otherwise fall back to current
  $isLauncher = ($py -like 'py -3.11')
  if ($isLauncher) {
    & py -3.11 -m venv $venvDir
  } else {
    & $py -m venv $venvDir
  }
  if ($LASTEXITCODE -ne 0) { Fail "Failed to create venv." }
}

function Invoke-Python([string[]]$args) {
  $py = Get-PythonPath
  # If the python path contains a space (like 'py -3.11'), invoke via cmd /c
  if ($py -like '* *') {
    & cmd /c "$py $($args -join ' ')"
  } else {
    & $py @args
  }
  if ($LASTEXITCODE -ne 0) { Fail "Python command failed: $($args -join ' ')" }
}

function Ensure-Requirements([string]$requirementsRelPath) {
  $root = Resolve-RepoRoot
  $req = Join-Path $root $requirementsRelPath
  if (Test-Path $req) {
    Write-Host "[deps] installing from $requirementsRelPath"
    Invoke-Python @('-m','pip','install','--upgrade','pip')
    Invoke-Python @('-m','pip','install','-r',"$req")
  }
}

function Ensure-Branch([int]$IssueNumber, [string]$Slug) {
  Ensure-Git
  $branch = "issue-$IssueNumber-$Slug"
  $exists = git rev-parse --verify --quiet "refs/heads/$branch"
  if ($LASTEXITCODE -eq 0) {
    git checkout $branch | Out-Null
  } else {
    git checkout -b $branch | Out-Null
  }
  $branch
}

function Ensure-UpstreamAndPush([string]$branch) {
  $hasUpstream = git rev-parse --symbolic-full-name --abbrev-ref "$branch@{u}" 2>$null
  if (-not $hasUpstream) {
    Write-Host "Setting upstream and pushing $branch…"
    git push -u origin $branch | Out-Null
  } else {
    Write-Host "Rebasing on remote and pushing $branch…"
    git pull --rebase origin $branch | Out-Null
    git push | Out-Null
  }
}

function New-Slug([string]$s) {
  $s = $s.ToLower()
  $s = ($s -replace '[^a-z0-9]+','-').Trim('-')
  if ($s.Length -gt 64) { $s = $s.Substring(0,64).Trim('-') }
  return $s
}
