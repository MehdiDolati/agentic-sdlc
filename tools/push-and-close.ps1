<# 
 .SYNOPSIS
   Create a branch for an issue, run optional local CI, push changes, open a PR, and (optionally) merge it.
 .USAGE
   tools\push-and-close.ps1 -Repo "OWNER/REPO" -IssueNumber 1 [-RunLocalCI] [-DockerSmoke] [-BaseBranch main] [-AutoMerge] [-Paths @(".")]
 .NOTES
   - Requires: git, gh (GitHub CLI), PowerShell 5.1+
   - This script avoids PS7-only operators (no null-conditional, etc.).
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$Repo,

  [Parameter(Mandatory=$true)]
  [int]$IssueNumber,

  # If provided, run local tests before pushing (expects tools\local-ci.ps1)
  [switch]$RunLocalCI,

  # If provided along with -RunLocalCI, run docker smoke tests too
  [switch]$DockerSmoke,

  # Target base branch for the PR
  [string]$BaseBranch = "main",

  # Auto-merge after PR is created (squash + delete branch)
  [switch]$AutoMerge,

  # Files/paths to include in the commit (default: all changes)
  [string[]]$Paths = @(".")
)

function Assert-Exe($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "Required command '$name' not found on PATH." }
  return $cmd.Source
}

function Get-IssueTitle {
  param([string]$Repo,[int]$IssueNumber)
  $json = gh issue view $IssueNumber --repo $Repo --json title 2>$null
  if (-not $json) { throw "Could not query issue #$IssueNumber from $Repo via 'gh'." }
  try {
    $obj = $json | ConvertFrom-Json
    return $obj.title
  } catch {
    throw "Failed to parse JSON from 'gh issue view'. Raw: $json"
  }
}

function New-BranchNameFromTitle {
  param([int]$IssueNumber,[string]$Title,[string]$Prefix = "issue")
  $t = $Title.ToLower()
  $t = ($t -replace '[^a-z0-9]+','-').Trim('-')
  if ($t.Length -gt 50) { $t = $t.Substring(0,50).Trim('-') }
  return "$Prefix-$IssueNumber-$t"
}

function Invoke-LocalCI {
  param([switch]$DockerSmoke)
  $ciPath = Join-Path (Get-Location) "tools\local-ci.ps1"
  if (Test-Path $ciPath) {
    if ($DockerSmoke) {
      & $ciPath -DockerSmoke
    } else {
      & $ciPath
    }
    if ($LASTEXITCODE -ne 0) { throw "Local CI failed (tools\local-ci.ps1)." }
  } else {
    Write-Warning "tools\local-ci.ps1 not found, skipping local CI."
  }
}

# 1) Pre-flight checks
$null = Assert-Exe git
$null = Assert-Exe gh

# Ensure we are inside a git repo
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { throw "This directory is not a git repository." }

# 2) Gather issue metadata
$title = Get-IssueTitle -Repo $Repo -IssueNumber $IssueNumber
$branch = New-BranchNameFromTitle -IssueNumber $IssueNumber -Title $title

Write-Host "=== Issue #$IssueNumber ===" -ForegroundColor Cyan
Write-Host "Title: $title"
Write-Host "Branch: $branch"
Write-Host ""

# 3) Create/switch to branch (keep local changes)
git checkout -b "$branch"
if ($LASTEXITCODE -ne 0) {
  # If branch exists, just switch
  git checkout "$branch"
  if ($LASTEXITCODE -ne 0) { throw "Could not switch to branch $branch" }
}

# 4) Optional: run local CI before committing (to catch env failures early)
if ($RunLocalCI) {
  Write-Host "`nRunning local CI..." -ForegroundColor Yellow
  Invoke-LocalCI -DockerSmoke:$DockerSmoke
}

# 5) Stage & commit
if ($Paths.Count -eq 1 -and $Paths[0] -eq ".") {
  git add -A
} else {
  git add $Paths
}
# Only commit if there is something to commit
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  $subject = "feat: resolve #$IssueNumber — $title"
  git commit -m "$subject" -m "Closes #$IssueNumber"
} else {
  Write-Host "No staged changes to commit; continuing." -ForegroundColor Yellow
}

# 6) Push branch
git push -u origin "$branch"
if ($LASTEXITCODE -ne 0) { throw "git push failed." }

# 7) Create PR
$prTitle = "$title (#{0})" -f $IssueNumber
$prBody  = "This PR addresses **Issue #$IssueNumber**.`n`nCloses #$IssueNumber."
gh pr create --repo $Repo --head "$branch" --base "$BaseBranch" --title "$prTitle" --body "$prBody"
if ($LASTEXITCODE -ne 0) { throw "Failed to create PR via 'gh pr create'." }

# 8) Optionally auto-merge (squash) and delete branch
if ($AutoMerge) {
  Write-Host "Attempting to merge PR (squash) and delete branch..." -ForegroundColor Yellow
  gh pr merge --squash --delete-branch --repo $Repo
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Auto-merge failed (may require approvals or checks). You can merge via GitHub UI."
  } else {
    Write-Host "PR merged and branch deleted." -ForegroundColor Green
  }
}

Write-Host "`nAll done. Review/merge the PR if not auto-merged. Once merged into '$BaseBranch', GitHub will auto-close issue #$IssueNumber due to 'Closes #$IssueNumber' in the commit/PR body." -ForegroundColor Green
